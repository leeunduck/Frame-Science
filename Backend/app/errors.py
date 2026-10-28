from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
import logging
import traceback

logger = logging.getLogger(__name__)


def log_failure(message: str, exc: Exception, level: int = logging.ERROR):
    # 예외 원문·SQL 매개변수·locals·소스 줄에는 인증정보가 포함될 수 있다.
    # traceback의 파일/행/함수와 예외 유형만 기록해 호출 경로를 보존한다.
    frames = ''.join(
        f'  File "{frame.f_code.co_filename}", line {line}, in {frame.f_code.co_name}\n'
        for frame, line in traceback.walk_tb(exc.__traceback__)
    )
    logger.log(level, '%s\nTraceback (most recent call last):\n%s%s', message, frames, type(exc).__name__)


async def unexpected_error(request: Request, exc: Exception):
    log_failure('Unexpected Auth error', exc)
    return JSONResponse(status_code=500, content={'code': 'INTERNAL_SERVER_ERROR', 'message': '잠시 후 다시 시도해주세요.'})


class AuthError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message

def install_handlers(app):
    @app.exception_handler(AuthError)
    async def auth_error(request: Request, exc: AuthError):
        return JSONResponse(status_code=exc.status, content={'code': exc.code, 'message': exc.message})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc):
        return JSONResponse(status_code=422, content={'code': 'VALIDATION_ERROR', 'message': '입력 내용을 확인해주세요.'})

    async def unavailable(request: Request, exc):
        log_failure('Auth dependency unavailable', exc)
        return JSONResponse(status_code=503, content={'code': 'SERVICE_UNAVAILABLE', 'message': '잠시 후 다시 시도해주세요.'})
    app.add_exception_handler(RedisError, unavailable)
    app.add_exception_handler(SQLAlchemyError, unavailable)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc):
        return JSONResponse(status_code=exc.status_code, content={'code': 'HTTP_ERROR', 'message': '요청을 처리할 수 없습니다.'})

    app.add_exception_handler(Exception, unexpected_error)
