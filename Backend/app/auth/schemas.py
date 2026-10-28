from typing import Annotated, Literal
from pydantic import BaseModel, StringConstraints

Phone = Annotated[str, StringConstraints(pattern=r'^010[0-9]{8}$')]
Password = Annotated[str, StringConstraints(min_length=1, max_length=128)]
class PhoneRequest(BaseModel):
    phone: Phone
class LoginRequest(PhoneRequest):
    password: Password
class VerifyRequest(PhoneRequest):
    code: Annotated[str, StringConstraints(pattern=r'^[0-9]{6}$')]
class ConfirmRequest(BaseModel):
    resetToken: Annotated[str, StringConstraints(min_length=1, max_length=256)]
    newPassword: Password
    newPasswordConfirm: Password
class TokenResponse(BaseModel):
    accessToken: str
    role: Literal['STUDENT', 'PARENT', 'STAFF']
class ResetResponse(BaseModel):
    resetToken: str
