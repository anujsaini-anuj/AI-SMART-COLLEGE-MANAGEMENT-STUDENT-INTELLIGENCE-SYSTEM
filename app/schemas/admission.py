from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr, ConfigDict


# ==================================================
# CREATE ADMISSION APPLICATION
# ==================================================

class AdmissionApplicationCreate(BaseModel):

    applicant_name: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    email: EmailStr

    phone: str = Field(
        ...,
        min_length=10,
        max_length=15
    )

    date_of_birth: Optional[date] = None

    previous_qualification: str = Field(
        ...,
        min_length=2,
        max_length=100
    )

    previous_percentage: float = Field(
        ...,
        ge=0,
        le=100
    )

    course_id: int = Field(
        ...,
        gt=0
    )

    academic_year: str = Field(
        ...,
        min_length=4,
        max_length=20
    )


class AdmissionApplicationResponse(BaseModel):

    id: int
    application_number: str
    applicant_name: str
    email: str
    phone: str
    date_of_birth: date | None
    previous_qualification: str
    previous_percentage: float | None
    course_id: int
    academic_year: str
    status: str
    reviewed_by: int | None
    review_remarks: str | None
    enrolled_student_id: str | None
    submitted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

