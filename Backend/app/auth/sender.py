import logging
from app.config import get_settings
from app.errors import AuthError

class ConsoleCodeSender:
    """실제 SMS 연결 전 로컬에서만 인증번호 흐름을 검증하는 Sender다."""
    # TODO: SMS Provider가 확정되면 Console Sender를 실제 구현으로 교체한다.
    def send(self, phone: str, code: str):
        if get_settings().app_env != 'local':
            raise AuthError(503, 'SMS_PROVIDER_UNAVAILABLE', '인증번호 발송이 준비되지 않았습니다.')
        logging.getLogger('uvicorn.error').warning('[LOCAL ONLY] Password reset %s: %s', phone, code)

sender = ConsoleCodeSender()
