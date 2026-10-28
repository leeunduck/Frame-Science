import json
import secrets
import time
from app.config import get_settings
from app.errors import AuthError
from app.redis_store import redis, key, revoke_all
from . import repository as repo
from .security import DUMMY_HASH, decode, digest, hash_password, issue, password_policy, verify_password
from .sender import sender


def active(user):
    if not user or not user.is_active:
        raise AuthError(403, 'ACCOUNT_INACTIVE', '비활성 계정입니다. 관리자에게 문의해주세요.')


def tokens(user):
    access, _ = issue(user, 'access')
    refresh, claims = issue(user, 'refresh')
    ttl = max(1, claims['exp'] - int(time.time()))
    token_key, index = key('refresh:' + claims['jti']), key(f'sessions:{user.id}')
    # 계정별 Set을 함께 유지해야 비밀번호 변경 시 모든 기기의 Refresh를 폐기할 수 있다.
    with redis.pipeline() as pipe:
        pipe.set(token_key, str(user.id), ex=ttl)
        pipe.sadd(index, token_key)
        pipe.expire(index, ttl)
        pipe.execute()
    return {'accessToken': access, 'role': user.role}, refresh


def login(db, data):
    user = repo.by_phone(db, data.phone, lock=True)
    # 없는 번호도 해시 검증을 수행하고 동일한 오류를 반환해 계정 존재 여부 노출을 줄인다.
    if not verify_password(data.password, user.password_hash if user else DUMMY_HASH) or not user:
        raise AuthError(401, 'AUTH_INVALID_CREDENTIALS', '등록되지 않은 휴대폰 번호이거나 비밀번호가 올바르지 않습니다.')
    active(user)
    result = tokens(user)
    db.commit()
    return result


def refresh(db, token):
    """기존 Refresh를 원자적으로 소비해 같은 토큰의 동시 재사용을 막는다."""
    claims = decode(token, 'refresh')
    user = repo.by_id(db, int(claims['sub']), lock=True)
    token_key = key('refresh:' + claims['jti'])
    if redis.getdel(token_key) != claims['sub']:
        raise AuthError(401, 'AUTH_REFRESH_TOKEN_INVALID', '로그인이 만료되었습니다.')
    redis.srem(key('sessions:' + claims['sub']), token_key)
    # 계정 삭제는 비활성 상태가 아니라 인증 대상 자체가 사라진 경우다.
    if user is None:
        raise AuthError(401, 'AUTH_REFRESH_TOKEN_INVALID', '인증이 만료되었습니다. 다시 로그인해주세요.')
    active(user)
    result = tokens(user)
    db.commit()
    return result


def logout(token):
    """없는 토큰도 성공으로 처리하되, 유효한 경우 현재 Refresh Session만 폐기한다."""
    try:
        claims = decode(token, 'refresh')
    except AuthError:
        return
    with redis.pipeline() as pipe:
        pipe.delete(key('refresh:' + claims['jti']))
        pipe.srem(key('sessions:' + claims['sub']), key('refresh:' + claims['jti']))
        pipe.execute()


def request_reset(db, phone):
    s = get_settings()
    if s.app_env != 'local':
        raise AuthError(503, 'SMS_PROVIDER_UNAVAILABLE', '인증번호 발송이 준비되지 않았습니다.')
    # 등록 여부와 무관하게 같은 재요청 제한을 적용해 외부 응답 차이를 줄인다.
    if not redis.set(key('cooldown:' + digest(phone)), '1', nx=True, ex=s.reset_request_cooldown_seconds):
        return
    user = repo.by_phone(db, phone)
    if not user or not user.is_active:
        return
    code = f'{secrets.randbelow(1000000):06d}'
    state = json.dumps({'id': user.id, 'hash': digest(user.password_hash), 'code': digest(code), 'attempts': 0})
    code_key = key('code:' + digest(phone))
    redis.set(code_key, state, ex=s.reset_code_ttl_seconds)
    try:
        sender.send(phone, code)
    except Exception:
        redis.delete(code_key)
        raise


def verify_reset(phone, code):
    # 비교·시도 횟수 증가·소비를 하나의 Lua 실행으로 묶어 동시 검증 성공을 막는다.
    state = redis.eval("""
    local raw = redis.call('GET', KEYS[1])
    if not raw then return 'expired' end
    local data = cjson.decode(raw)
    if data.code ~= ARGV[1] then
        data.attempts = data.attempts + 1
        if data.attempts >= tonumber(ARGV[2]) then
            redis.call('DEL', KEYS[1])
            return 'attempts_exceeded'
        else redis.call('SET', KEYS[1], cjson.encode(data), 'KEEPTTL') end
        return 'invalid'
    end
    redis.call('DEL', KEYS[1])
    return raw
    """, 1, key('code:' + digest(phone)), digest(code), get_settings().reset_code_max_attempts)
    messages = {
        'invalid': '인증번호가 올바르지 않습니다.',
        'expired': '인증번호가 만료되었습니다. 새 인증번호를 요청해주세요.',
        'attempts_exceeded': '인증번호 입력 횟수를 초과했습니다. 새 인증번호를 요청해주세요.',
    }
    if state in messages:
        raise AuthError(400, 'PASSWORD_RESET_CODE_' + state.upper(), messages[state])
    data = json.loads(state)
    token = secrets.token_urlsafe(32)
    redis.set(key('reset:' + digest(token)), json.dumps({'id': data['id'], 'hash': data['hash']}), ex=get_settings().reset_token_ttl_seconds)
    return {'resetToken': token}


def confirm_reset(db, data):
    """일회용 Reset Token을 소비하고 기존 Refresh를 폐기한 뒤 비밀번호를 저장한다."""
    password_policy(data.newPassword, data.newPasswordConfirm)
    token_key = key('reset:' + digest(data.resetToken))
    raw = redis.get(token_key)
    if not raw:
        raise AuthError(400, 'PASSWORD_RESET_TOKEN_EXPIRED', '비밀번호 변경 요청이 만료되었습니다. 다시 인증해주세요.')
    state = json.loads(raw)
    user = repo.by_id(db, state['id'], lock=True)
    # 이전 비밀번호에서 발급한 다른 Reset Token도 비밀번호가 바뀌면 사용할 수 없다.
    if not user or not user.is_active or state['hash'] != digest(user.password_hash):
        raise AuthError(400, 'PASSWORD_RESET_TOKEN_INVALID', '유효하지 않은 비밀번호 변경 요청입니다. 다시 인증해주세요.')
    hashed = hash_password(data.newPassword)
    if redis.getdel(token_key) != raw:
        raise AuthError(400, 'PASSWORD_RESET_TOKEN_INVALID', '유효하지 않은 비밀번호 변경 요청입니다. 다시 인증해주세요.')
    # 계정 행 잠금으로 Login/Refresh/Reset을 직렬화한다.
    # Redis 폐기에 실패하면 비밀번호 변경도 커밋하지 않는다.
    revoke_all(user.id)
    user.password_hash = hashed
    db.commit()
