from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class SessionResponse(BaseModel):
    player_id: str
    session_id: str
    access_token: str
    refresh_token: str


class SessionBindingRequest(BaseModel):
    session_id: str
    refresh_token: str


class RefreshRequest(SessionBindingRequest):
    pass


class LogoutRequest(SessionBindingRequest):
    pass


class SessionRevocationResponse(BaseModel):
    session_id: str
    revoked: bool