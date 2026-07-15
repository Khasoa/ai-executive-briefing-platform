from typing import Literal

from pydantic import BaseModel


class ProjectSchema(BaseModel):
    id: str
    name: str
    status: Literal["On Track", "At Risk"]
    progress: int
    owner: str
    dueDate: str


class ProjectsResponse(BaseModel):
    projects: list[ProjectSchema]
