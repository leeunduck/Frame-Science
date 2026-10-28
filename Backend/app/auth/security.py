import hashlib
import hmac
import re
import string
import time
import uuid
import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from app.config import get_settings
from app.errors import AuthError

_hasher = PasswordHash.recommended()
def hash_password(password):
    """초기 4자리 비밀번호도 저장할 수 있도록 정책 검사와 Argon2 해시를 분리한다."""
    return _hasher.hash(password)
def verify_password(password, hashed):
    try:
        return _hasher.verify(password, hashed)
    except (ValueError, UnknownHashError):
        return False
DUMMY_HASH = hash_password('dummy-password-never-used')

def password_policy(password, confirmation):
    if len(password) < 8 or not re.search('[A-Za-z]', password) or not re.search('[0-9]', password) or not any(char in string.punctuation for char in password):
        raise AuthError(422, 'PASSWORD_POLICY_VIOLATION', '비밀번호는 8자 이상, 영문·숫자·특수문자를 포함해야 합니다.')
    if password != confirmation:
        raise AuthError(422, 'PASSWORD_CONFIRM_MISMATCH', '비밀번호 확인이 일치하지 않습니다.')

def issue(user, kind):
    """Access와 Refresh의 Secret·Claim을 분리해 서로 대체해 사용할 수 없게 한다."""
    s = get_settings()
    now = int(time.time())
    ttl = s.access_token_expire_minutes * 60 if kind == 'access' else s.refresh_token_expire_days * 86400
    claims = {'sub': str(user.id), 'type': kind, 'iat': now, 'exp': now + ttl}
    claims.update({'role': user.role} if kind == 'access' else {'jti': uuid.uuid4().hex})
    secret = s.access_token_secret if kind == 'access' else s.refresh_token_secret
    return jwt.encode(claims, secret, algorithm='HS256'), claims

def decode(token, kind):
    """서명뿐 아니라 필수 Claim과 용도를 검증해 다른 종류의 JWT 사용을 거부한다."""
    s = get_settings()
    try:
        claims = jwt.decode(token, s.access_token_secret if kind == 'access' else s.refresh_token_secret,
                            algorithms=['HS256'], options={'require': ['sub', 'type', 'iat', 'exp', 'role' if kind == 'access' else 'jti']})
        if claims['type'] != kind or not claims['sub'].isdigit() or int(claims['sub']) <= 0:
            raise ValueError()
        return claims
    except (jwt.InvalidTokenError, ValueError, TypeError, AttributeError):
        raise AuthError(401, 'AUTH_REFRESH_TOKEN_INVALID' if kind == 'refresh' else 'AUTH_ACCESS_TOKEN_INVALID', '인증이 만료되었습니다. 다시 로그인해주세요.') from None

def digest(value):
    return hmac.new(get_settings().refresh_token_secret.encode(), value.encode(), hashlib.sha256).hexdigest()
