from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class SessionResponse(BaseModel):
    player_id: str
    access_token: str
    refresh_token: str