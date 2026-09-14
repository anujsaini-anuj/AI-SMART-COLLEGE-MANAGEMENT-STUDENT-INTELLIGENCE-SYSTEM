from pydantic import BaseModel, Field


class FacultyCreate(BaseModel):

    faculty_id: str = Field(
        ...,
        min_length=2,
        max_length=50
    )

    name: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    phone: str | None = Field(
        default=None,
        max_length=20
    )

    designation: str | None = Field(
        default=None,
        max_length=100
    )

    department_id: int