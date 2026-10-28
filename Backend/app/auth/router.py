import logging
from app.errors import log_failure
from fastapi import APIRouter, Depends, Request, Response
from redis.exceptions import RedisError
from app.config import get_settings
from app.database import get_db
from . import service
from .schemas import LoginRequest, PhoneRequest, VerifyRequest, ConfirmRequest, TokenResponse, ResetResponse

router = APIRouter(prefix='/api/auth', tags=['Auth'])
COOKIE = 'refresh_token'
COOKIE_PATH = '/api/auth'

def set_cookie(response, token):
    s = get_settings()
    response.set_cookie(COOKIE, token, max_age=s.refresh_token_expire_days * 86400, httponly=True,
                        secure=s.cookie_secure, samesite=s.cookie_samesite, path=COOKIE_PATH)

def clear_cookie(response):
    s = get_settings()
    response.delete_cookie(COOKIE, path=COOKIE_PATH, httponly=True, secure=s.cookie_secure, samesite=s.cookie_samesite)

@router.post('/login', response_model=TokenResponse)
def login(data: LoginRequest, response: Response, db=Depends(get_db)):
    body, token = service.login(db, data)
    set_cookie(response, token)
    return body

@router.post('/refresh', response_model=TokenResponse)
def refresh(request: Request, response: Response, db=Depends(get_db)):
    body, token = service.refresh(db, request.cookies.get(COOKIE, ''))
    set_cookie(response, token)
    return body

@router.post('/logout', status_code=204)
def logout(request: Request):
    response = Response(status_code=204)
    try:
        service.logout(request.cookies.get(COOKIE, ''))
    except RedisError as exc:
        # Redis 장애에도 브라우저 Cookie는 삭제한다. 서버 상태 폐기는 보장되지 않는다.
        log_failure('Logout Redis session revocation failed; clearing browser cookie', exc, logging.WARNING)
    clear_cookie(response)
    return response

@router.post('/password-reset/request', status_code=204)
def request_reset(data: PhoneRequest, db=Depends(get_db)):
    service.request_reset(db, data.phone)

@router.post('/password-reset/verify', response_model=ResetResponse)
def verify_reset(data: VerifyRequest):
    return service.verify_reset(data.phone, data.code)

@router.post('/password-reset/confirm', status_code=204)
def confirm_reset(data: ConfirmRequest, db=Depends(get_db)):
    service.confirm_reset(db, data)
