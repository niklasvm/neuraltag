from pydantic import BaseModel


class LoginRequest(BaseModel):
    state: str
    code: str = None
    scope: str = None
    error: str = None
