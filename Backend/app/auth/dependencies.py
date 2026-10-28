from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.database import get_db
from app.errors import AuthError
from .security import decode
from .repository import by_id
from .service import active

bearer = HTTPBearer(auto_error=False)
def current_account(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db=Depends(get_db)):
    if not credentials:
        raise AuthError(401, 'AUTH_ACCESS_TOKEN_INVALID', '로그인이 필요합니다.')
    # JWT의 role만 신뢰하지 않고 DB에서 현재 활성 상태와 역할을 확인한다.
    claims = decode(credentials.credentials, 'access')
    user = by_id(db, int(claims['sub']))
    # 삭제된 계정을 가리키는 JWT는 재로그인이 필요한 인증 오류다.
    if user is None:
        raise AuthError(401, 'AUTH_ACCESS_TOKEN_INVALID', '인증이 만료되었습니다. 다시 로그인해주세요.')
    active(user)
    return user

def require_roles(*roles):
    def check(user=Depends(current_account)):
        if user.role not in roles:
            raise AuthError(403, 'AUTH_FORBIDDEN', '접근 권한이 없습니다.')
        return user
    return check
