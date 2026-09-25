from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Date,
    UniqueConstraint
)

from sqlalchemy.orm import relationship

from app.database.database import Base


# ==================================================
# USER
# ==================================================

class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    email = Column(
        String(150),
        unique=True,
        index=True,
        nullable=False
    )

    password_hash = Column(
        String(255),
        nullable=False
    )

    role = Column(
        String(20),
        nullable=False,
        default="student"
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


# ==================================================
# DEPARTMENT
# ==================================================

class Department(Base):

    __tablename__ = "departments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(100),
        unique=True,
        nullable=False
    )

    code = Column(
        String(20),
        unique=True,
        nullable=False
    )

    description = Column(
        String(255),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Department → Faculty
    faculties = relationship(
        "Faculty",
        back_populates="department"
    )

    # Department → Student
    students = relationship(
        "Student",
        back_populates="department"
    )

    # Department → Course
    courses = relationship(
        "Course",
        back_populates="department"
    )


# ==================================================
# FACULTY
# ==================================================

class Faculty(Base):

    __tablename__ = "faculties"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    faculty_id = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )

    name = Column(
        String(100),
        nullable=False
    )

    phone = Column(
        String(20),
        nullable=True
    )

    designation = Column(
        String(100),
        nullable=True
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Faculty → User
    user = relationship(
        "User"
    )

    # Faculty → Department
    department = relationship(
        "Department",
        back_populates="faculties"
    )


    faculty_subjects = relationship(
        "FacultySubject",
        back_populates="faculty",
        cascade="all, delete-orphan"
    )


# ==================================================
# COURSE
# ==================================================

class Course(Base):

    __tablename__ = "courses"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    code = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )

    duration = Column(
        Integer,
        nullable=False
    )

    description = Column(
        String(255),
        nullable=True
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Course → Department
    department = relationship(
        "Department",
        back_populates="courses"
    )

    # Course → Subjects
    subjects = relationship(
        "Subject",
        back_populates="course"
    )

    # Course → Students
    students = relationship(
        "Student",
        back_populates="course"
    )

   

# ==================================================
# STUDENT
# ==================================================

class Student(Base):

    __tablename__ = "students"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    student_id = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )

    name = Column(
        String(100),
        nullable=False
    )

    phone = Column(
        String(20),
        nullable=True
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=False
    )

    course_id = Column(
        Integer,
        ForeignKey("courses.id"),
        nullable=False
    )

    semester = Column(
        Integer,
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Student → User
    user = relationship(
        "User"
    )

    # Student → Department
    department = relationship(
        "Department",
        back_populates="students"
    )

    # Student → Course
    course = relationship(
        "Course",
        back_populates="students"
    )


# ==================================================
# SUBJECT
# ==================================================

class Subject(Base):

    __tablename__ = "subjects"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    code = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )

    credits = Column(
        Integer,
        nullable=False
    )

    semester = Column(
        Integer,
        nullable=False
    )

    description = Column(
        String(255),
        nullable=True
    )

    course_id = Column(
        Integer,
        ForeignKey("courses.id"),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Subject → Course
    course = relationship(
        "Course",
        back_populates="subjects"
    )


    faculty_subjects = relationship(
        "FacultySubject",
        back_populates="subject",
        cascade="all, delete-orphan"
    )




class FacultySubject(Base):
    __tablename__ = "faculty_subjects"

    id = Column(Integer, primary_key=True, index=True)

    faculty_id = Column(
        Integer,
        ForeignKey("faculties.id"),
        nullable=False
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    faculty = relationship(
        "Faculty",
        back_populates="faculty_subjects"
    )

    subject = relationship(
        "Subject",
        back_populates="faculty_subjects"
    )

    __table_args__ = (
        UniqueConstraint(
            "faculty_id",
            "subject_id",
            name="unique_faculty_subject"
        ),
    )



# ==================================================
# ATTENDANCE
# ==================================================

class Attendance(Base):

    __tablename__ = "attendance"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            "date",
            name="unique_student_subject_attendance"
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    student_id = Column(
        String(50),
        ForeignKey("students.student_id"),
        nullable=False
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False
    )

    date = Column(
        Date,
        nullable=False
    )

    status = Column(
        String(20),
        nullable=False,
        default="Present"
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Attendance → Student
    student = relationship(
        "Student"
    )

    # Attendance → Subject
    subject = relationship(
        "Subject"
    )




# ==================================================
# MARKS
# ==================================================

class Marks(Base):

    __tablename__ = "marks"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            "exam_type",
            name="unique_student_subject_exam"
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    student_id = Column(
        String(50),
        ForeignKey("students.student_id"),
        nullable=False
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False
    )

    exam_type = Column(
        String(50),
        nullable=False
    )

    marks_obtained = Column(
        Integer,
        nullable=False
    )

    max_marks = Column(
        Integer,
        nullable=False
    )

    exam_date = Column(
        Date,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Marks → Student
    student = relationship(
        "Student"
    )

    # Marks → Subject
    subject = relationship(
        "Subject"
    )




# ==================================================
# ASSIGNMENT
# ==================================================

class Assignment(Base):

    __tablename__ = "assignments"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            "assignment_name",
            name="unique_student_subject_assignment"
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    student_id = Column(
        String(50),
        ForeignKey("students.student_id"),
        nullable=False
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False
    )

    assignment_name = Column(
        String(100),
        nullable=False
    )

    marks_obtained = Column(
        Integer,
        nullable=True
    )

    max_marks = Column(
        Integer,
        nullable=False
    )

    submission_date = Column(
        Date,
        nullable=True
    )

    status = Column(
        String(20),
        nullable=False,
        default="Pending"
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Assignment → Student
    student = relationship(
        "Student"
    )

    # Assignment → Subject
    subject = relationship(
        "Subject"
    )



# ==================================================
# PERFORMANCE
# ==================================================

class Performance(Base):

    __tablename__ = "performance"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            name="unique_student_subject_performance"
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    student_id = Column(
        String(50),
        ForeignKey("students.student_id"),
        nullable=False
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False
    )

    attendance_percentage = Column(
        Integer,
        nullable=False
    )

    marks_percentage = Column(
        Integer,
        nullable=False
    )

    assignment_percentage = Column(
        Integer,
        nullable=False
    )

    overall_percentage = Column(
        Integer,
        nullable=False
    )

    performance_level = Column(
        String(30),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Performance → Student
    student = relationship(
        "Student"
    )

    # Performance → Subject
    subject = relationship(
        "Subject"
    )




class StudentRisk(Base):

    __tablename__ = "student_risk"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            name="unique_student_subject_risk"
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    student_id = Column(
        String(50),
        ForeignKey("students.student_id"),
        nullable=False
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False
    )

    risk_score = Column(
        Integer,
        nullable=False
    )

    risk_level = Column(
        String(30),
        nullable=False
    )

    risk_reason = Column(
        String(500),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    student = relationship("Student")

    subject = relationship("Subject")




class Prediction(Base):

    __tablename__ = "predictions"

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            "prediction_type",
            name="unique_student_subject_prediction_type"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        String(50),
        ForeignKey("students.student_id"),
        nullable=False
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False
    )

    predicted_performance = Column(
        Integer,
        nullable=False
    )

    predicted_level = Column(
        String(30),
        nullable=False
    )

    model_name = Column(
        String(100),
        nullable=False
    )

    prediction_type = Column(
    String(100),
    nullable=False,
    default="Current Performance"
)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    student = relationship("Student")
    subject = relationship("Subject")







# ==================================================
# RECOMMENDATION
# ==================================================

class Recommendation(Base):

    __tablename__ = "recommendations"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    student_id = Column(
        String(50),
        ForeignKey("students.student_id"),
        nullable=False
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False
    )

    recommendation_text = Column(
        String(500),
        nullable=False
    )

    recommendation_type = Column(
        String(50),
        nullable=False
    )

    priority = Column(
        String(20),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    student = relationship(
        "Student"
    )

    subject = relationship(
        "Subject"
    )


class StudentMLRecord(Base):
    __tablename__ = "student_ml_records"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        String(50),
        ForeignKey("students.student_id"),
        nullable=False
    )

    subject_id = Column(
        Integer,
        ForeignKey("subjects.id"),
        nullable=False
    )

    attendance_percentage = Column(
        Integer,
        nullable=False
    )

    internal_marks_percentage = Column(
        Integer,
        nullable=False
    )

    assignment_percentage = Column(
        Integer,
        nullable=False
    )

    previous_exam_percentage = Column(
        Integer,
        nullable=False
    )


    final_exam_percentage = Column(
        Integer,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "subject_id",
            "previous_exam_percentage",
            name="uq_student_ml_record"
        ),
    )

    student = relationship("Student")
    subject = relationship("Subject")