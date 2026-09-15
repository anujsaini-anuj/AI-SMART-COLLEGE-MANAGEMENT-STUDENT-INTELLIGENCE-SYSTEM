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