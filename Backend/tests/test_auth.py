"""Real PostgreSQL + Redis, rollback accounts and isolated Redis keys."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
os.environ['REDIS_PREFIX'] = 'frame:test:' + uuid.uuid4().hex + ':'
from app.main import app
from app.database import engine, get_db
from app.auth.models import UserAccount
from app.auth.security import hash_password, decode, digest
from app.auth import service
from app.redis_store import redis, key
from app.config import get_settings

@pytest.fixture
def client(monkeypatch):
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode='create_savepoint')
    user = UserAccount(phone='01099990001', password_hash=hash_password('0001'), role='STUDENT', is_active=True)
    db.add(user)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    sent = []
    monkeypatch.setattr(service.sender, 'send', lambda phone, code: sent.append(code))
    with TestClient(app) as c:
        yield c, db, user, sent
    app.dependency_overrides.clear()
    db.close()
    transaction.rollback()
    connection.close()
    keys = list(redis.scan_iter(key('*')))
    if keys:
        redis.delete(*keys)

def login(c, password='0001'):
    return c.post('/api/auth/login', json={'phone': '01099990001', 'password': password})

def reset_token(c, sent):
    assert c.post('/api/auth/password-reset/request', json={'phone': '01099990001'}).status_code == 204
    result = c.post('/api/auth/password-reset/verify', json={'phone': '01099990001', 'code': sent[-1]})
    assert result.status_code == 200
    return result.json()['resetToken']

def confirm(c, token, password='Frame123!', confirmation='Frame123!'):
    return c.post('/api/auth/password-reset/confirm', json={'resetToken': token, 'newPassword': password, 'newPasswordConfirm': confirmation})

def test_login_rotation_logout(client):
    c, db, user, sent = client
    result = login(c)
    assert result.status_code == 200
    assert decode(result.json()['accessToken'], 'access')['sub'] == str(user.id)
    assert 'HttpOnly' in result.headers['set-cookie'] and 'SameSite=lax' in result.headers['set-cookie']
    assert result.headers['cache-control'] == 'no-store'
    old = c.cookies.get('refresh_token')
    assert c.post('/api/auth/refresh').status_code == 200
    new = c.cookies.get('refresh_token')
    assert old != new
    c.cookies.clear(); c.cookies.set('refresh_token', old, domain='testserver.local', path='/api/auth')
    assert c.post('/api/auth/refresh').status_code == 401
    c.cookies.clear(); c.cookies.set('refresh_token', new, domain='testserver.local', path='/api/auth')
    assert c.post('/api/auth/logout').status_code == 204
    assert not c.cookies.get('refresh_token')
    c.cookies.set('refresh_token', new, domain='testserver.local', path='/api/auth')
    assert c.post('/api/auth/refresh').status_code == 401
    assert c.post('/api/auth/logout').status_code == 204

def test_credentials_validation_inactive(client):
    c, db, user, _ = client
    bad = login(c, 'wrong')
    unknown = c.post('/api/auth/login', json={'phone': '01099990002', 'password': 'wrong'})
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json() == {
        'code': 'AUTH_INVALID_CREDENTIALS',
        'message': '등록되지 않은 휴대폰 번호이거나 비밀번호가 올바르지 않습니다.',
    }
    invalid = c.post('/api/auth/login', json={'phone': 'invalid'})
    assert invalid.status_code == 422 and invalid.json()['code'] == 'VALIDATION_ERROR'
    login(c)
    user.is_active = False; db.commit()
    assert login(c).status_code == 403
    assert c.post('/api/auth/refresh').status_code == 403

def test_reset_policy_single_use_revokes_all(client):
    c, db, user, sent = client
    login(c); first = c.cookies.get('refresh_token')
    login(c); second = c.cookies.get('refresh_token')
    token = reset_token(c, sent)
    assert confirm(c, token, 'short', 'short').json()['code'] == 'PASSWORD_POLICY_VIOLATION'
    assert confirm(c, token, confirmation='different').json()['code'] == 'PASSWORD_CONFIRM_MISMATCH'
    assert confirm(c, token).status_code == 204
    assert confirm(c, token).status_code == 400
    assert login(c).status_code == 401
    assert login(c, 'Frame123!').status_code == 200
    for old in [first, second]:
        c.cookies.clear(); c.cookies.set('refresh_token', old, domain='testserver.local', path='/api/auth')
        assert c.post('/api/auth/refresh').status_code == 401
    assert user.password_hash.startswith('$argon2id$')

def test_unknown_request_code_expiry_attempt_limit(client):
    c, db, user, sent = client
    assert c.post('/api/auth/password-reset/request', json={'phone': '01099990002'}).status_code == 204
    assert sent == []
    c.post('/api/auth/password-reset/request', json={'phone': user.phone})
    c.post('/api/auth/password-reset/request', json={'phone': user.phone})
    assert len(sent) == 1
    wrong = '999999' if sent[0] != '999999' else '000000'
    for attempt in range(get_settings().reset_code_max_attempts):
        result = c.post('/api/auth/password-reset/verify', json={'phone': user.phone, 'code': wrong})
        assert result.status_code == 400
        if attempt + 1 == get_settings().reset_code_max_attempts:
            assert result.json() == {'code': 'PASSWORD_RESET_CODE_ATTEMPTS_EXCEEDED', 'message': '인증번호 입력 횟수를 초과했습니다. 새 인증번호를 요청해주세요.'}
        else:
            assert result.json() == {'code': 'PASSWORD_RESET_CODE_INVALID', 'message': '인증번호가 올바르지 않습니다.'}
    result = c.post('/api/auth/password-reset/verify', json={'phone': user.phone, 'code': sent[0]})
    assert result.status_code == 400
    assert result.json() == {'code': 'PASSWORD_RESET_CODE_EXPIRED', 'message': '인증번호가 만료되었습니다. 새 인증번호를 요청해주세요.'}
    assert confirm(c, 'missing').json()['code'] == 'PASSWORD_RESET_TOKEN_EXPIRED'

def test_code_consumed_once_concurrently(client):
    c, db, user, sent = client
    c.post('/api/auth/password-reset/request', json={'phone': user.phone})
    def verify(_):
        return c.post('/api/auth/password-reset/verify', json={'phone': user.phone, 'code': sent[0]}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(verify, range(2))) == [200, 400]

def test_token_types_origin_and_missing_cookie(client):
    c, *_ = client
    access = login(c).json()['accessToken']
    c.cookies.clear(); c.cookies.set('refresh_token', access)
    assert c.post('/api/auth/refresh').status_code == 401
    c.cookies.clear()
    assert c.post('/api/auth/refresh').status_code == 401
    assert c.post('/api/auth/logout').status_code == 204
    assert c.post('/api/auth/logout', headers={'Origin': 'https://evil.example'}).status_code == 403

def test_old_reset_token_invalid_after_password_change(client):
    c, db, user, sent = client
    first = reset_token(c, sent)
    redis.delete(key('cooldown:' + digest(user.phone)))
    second = reset_token(c, sent)
    assert confirm(c, second).status_code == 204
    assert confirm(c, first).json()['code'] == 'PASSWORD_RESET_TOKEN_INVALID'

@pytest.mark.parametrize('role', ['STUDENT', 'PARENT', 'STAFF'])
def test_roles(client, role):
    c, db, user, _ = client
    user.role = role; db.commit()
    assert login(c).json()['role'] == role


def test_expired_jwt_and_reset_ttl(client):
    import time
    import jwt
    c, db, user, sent = client
    claims = {'sub': str(user.id), 'type': 'refresh', 'jti': 'expired', 'iat': int(time.time()) - 60, 'exp': int(time.time()) - 1}
    token = jwt.encode(claims, get_settings().refresh_token_secret, algorithm='HS256')
    c.cookies.set('refresh_token', token)
    assert c.post('/api/auth/refresh').json()['code'] == 'AUTH_REFRESH_TOKEN_INVALID'
    token = reset_token(c, sent)
    token_key = key('reset:' + digest(token))
    assert 0 < redis.ttl(token_key) <= get_settings().reset_token_ttl_seconds
    redis.pexpire(token_key, 1)
    time.sleep(.01)
    assert confirm(c, token).json()['code'] == 'PASSWORD_RESET_TOKEN_EXPIRED'


def test_access_dependency_and_roles(client):
    from fastapi.security import HTTPAuthorizationCredentials
    from app.auth.dependencies import current_account, require_roles
    from app.errors import AuthError
    c, db, user, _ = client
    token = login(c).json()['accessToken']
    found = current_account(HTTPAuthorizationCredentials(scheme='Bearer', credentials=token), db)
    assert found.id == user.id
    assert require_roles('STUDENT', 'PARENT')(found).id == user.id
    with pytest.raises(AuthError) as exc:
        require_roles('STAFF')(found)
    assert exc.value.status == 403


def test_production_settings_secure_and_sender_disabled(client):
    from app.config import Settings
    from app.errors import AuthError
    c, db, user, _ = client
    values = get_settings().model_dump()
    values['app_env'] = 'production'
    assert Settings(**values).cookie_secure is True
    s = get_settings()
    old = s.app_env
    try:
        s.app_env = 'production'
        for phone in [user.phone, '01099990002']:
            result = c.post('/api/auth/password-reset/request', json={'phone': phone})
            assert result.status_code == 503
            assert result.json()['code'] == 'SMS_PROVIDER_UNAVAILABLE'
    finally:
        s.app_env = old


def test_deleted_account_access_and_refresh(client):
    from fastapi.security import HTTPAuthorizationCredentials
    from app.auth.dependencies import current_account
    from app.errors import AuthError
    c, db, user, _ = client
    access = login(c).json()['accessToken']
    refresh = decode(c.cookies.get('refresh_token'), 'refresh')
    db.delete(user)
    db.commit()
    with pytest.raises(AuthError) as error:
        current_account(HTTPAuthorizationCredentials(scheme='Bearer', credentials=access), db)
    assert (error.value.status, error.value.code) == (401, 'AUTH_ACCESS_TOKEN_INVALID')
    result = c.post('/api/auth/refresh')
    assert result.status_code == 401
    assert result.json()['code'] == 'AUTH_REFRESH_TOKEN_INVALID'
    assert not redis.exists(key('refresh:' + refresh['jti']))
    assert not redis.sismember(key('sessions:' + refresh['sub']), key('refresh:' + refresh['jti']))


def test_inactive_access_is_distinct_from_missing_account(client):
    from fastapi.security import HTTPAuthorizationCredentials
    from app.auth.dependencies import current_account
    from app.errors import AuthError
    c, db, user, _ = client
    access = login(c).json()['accessToken']
    user.is_active = False
    db.commit()
    with pytest.raises(AuthError) as error:
        current_account(HTTPAuthorizationCredentials(scheme='Bearer', credentials=access), db)
    assert (error.value.status, error.value.code) == (403, 'ACCOUNT_INACTIVE')
    assert error.value.message == '비활성 계정입니다. 관리자에게 문의해주세요.'


@pytest.mark.parametrize('kind', ['db', 'redis', 'unexpected'])
def test_infrastructure_errors_hide_details_and_log_frames(client, monkeypatch, caplog, kind):
    from redis.exceptions import RedisError
    from sqlalchemy.exc import StatementError
    import logging
    c, *_ = client
    marker = 'PRIVATE_PASSWORD_TOKEN_COOKIE_PHONE_CODE'
    exceptions = {
        'db': StatementError('private SQL', 'SELECT secret', {'password': marker}, ValueError(marker)),
        'redis': RedisError(marker),
        'unexpected': RuntimeError(marker),
    }
    def fail_login(*args):
        raise exceptions[kind]
    monkeypatch.setattr(service, 'login', fail_login)
    with caplog.at_level(logging.ERROR, logger='app.errors'):
        result = login(c)
    assert result.status_code == (500 if kind == 'unexpected' else 503)
    assert result.json() == {
        'code': 'INTERNAL_SERVER_ERROR' if kind == 'unexpected' else 'SERVICE_UNAVAILABLE',
        'message': '잠시 후 다시 시도해주세요.',
    }
    assert 'Traceback (most recent call last)' in caplog.text
    assert 'fail_login' in caplog.text
    assert type(exceptions[kind]).__name__ in caplog.text
    assert marker not in caplog.text + result.text
    assert 'SELECT secret' not in caplog.text + result.text
    assert all(record.exc_info is None for record in caplog.records)


def test_logout_redis_failure_logs_warning_and_clears_cookie(client, monkeypatch, caplog):
    from redis.exceptions import RedisError
    import logging
    c, *_ = client
    login(c)
    def fail_logout(*args):
        raise RedisError('PRIVATE_REFRESH_TOKEN')
    monkeypatch.setattr(service, 'logout', fail_logout)
    with caplog.at_level(logging.WARNING, logger='app.errors'):
        result = c.post('/api/auth/logout')
    assert result.status_code == 204 and result.content == b''
    assert 'Max-Age=0' in result.headers['set-cookie']
    assert not c.cookies.get('refresh_token')
    assert 'Logout Redis session revocation failed' in caplog.text
    assert 'fail_logout' in caplog.text
    assert 'PRIVATE_REFRESH_TOKEN' not in caplog.text


def test_expected_errors_do_not_emit_error_tracebacks(client, caplog):
    import logging
    c, *_ = client
    with caplog.at_level(logging.ERROR, logger='app.errors'):
        assert login(c, 'wrong').status_code == 401
        invalid = c.post('/api/auth/login', json={'phone': 'invalid', 'password': 'PRIVATE'})
        assert invalid.json() == {'code': 'VALIDATION_ERROR', 'message': '입력 내용을 확인해주세요.'}
        assert c.get('/not-found').json() == {'code': 'HTTP_ERROR', 'message': '요청을 처리할 수 없습니다.'}
    assert not [r for r in caplog.records if r.name == 'app.errors']
