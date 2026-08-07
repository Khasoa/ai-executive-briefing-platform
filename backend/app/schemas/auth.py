from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserSchema


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    fullName: str = Field(min_length=1, max_length=255)
    name: str | None = Field(default=None, max_length=100)
    role: str = Field(default="Executive", max_length=255)
    company: str = Field(default="", max_length=255)
    timezone: str = Field(default="UTC", max_length=100)


class RefreshRequest(BaseModel):
    refreshToken: str = Field(min_length=20, max_length=512)


class LogoutRequest(BaseModel):
    refreshToken: str = Field(min_length=20, max_length=512)


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"
    expiresIn: int
    user: UserSchema
