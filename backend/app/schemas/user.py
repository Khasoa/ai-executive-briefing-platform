from pydantic import BaseModel, ConfigDict


class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    fullName: str
    role: str
    company: str
    email: str
    avatar: str
    timezone: str
