from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.auth.router import router
from app.config import get_settings
from app.errors import install_handlers, unexpected_error

app = FastAPI(title='Frame Science Auth')
install_handlers(app)
app.include_router(router)

@app.middleware('http')
async def auth_headers(request: Request, call_next):
    # Cookie-backed mutations must come from an explicitly trusted browser origin.
    origin = request.headers.get('origin')
    if request.method == 'POST' and request.url.path.startswith('/api/auth/'):
        if (origin and origin not in get_settings().allowed_origins.split(',')) or request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse(status_code=403, content={'code': 'AUTH_ORIGIN_INVALID', 'message': '허용되지 않은 요청입니다.'})
    try:
        response = await call_next(request)
    except Exception as exc:
        # ServerErrorMiddleware의 재전파로 원문 예외가 서버 로그에 유출되지 않게 한다.
        response = await unexpected_error(request, exc)
    if request.url.path.startswith('/api/auth/'):
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.get('/')
def root():
    return {'message': 'Frame Science Backend'}
