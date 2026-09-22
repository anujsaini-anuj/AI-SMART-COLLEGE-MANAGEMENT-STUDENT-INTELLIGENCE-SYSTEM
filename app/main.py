from fastapi import FastAPI

from app.database.database import Base, engine


from app.routers.auth import router as auth_router
from app.routers.department import router as department_router
from app.routers.faculty import router as faculty_router
from app.routers.student import router as student_router
from app.routers.course import router as course_router
from app.routers.subject import router as subject_router
from app.routers.attendance import router as attendance_router
from app.routers.marks import router as marks_router
from app.routers.assignment import router as assignment_router
from app.routers.performance import router as performance_router
from app.routers.risk import router as risk_router
from app.routers.prediction import router as prediction_router
from app.routers.segmentation import router as segmentation_router
from app.routers.recommendation import router as recommendation_router
from app.routers.ai_assistant import router as ai_assistant_router
from app.routers.faculty_subject import router as faculty_subject_router
from app.routers.dashboard import router as dashboard_router
from app.routers import intelligence

Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="AI Smart College Management & Student Intelligence System",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "message": "AI Smart College Management System is running"
    }



app.include_router(auth_router)
app.include_router(department_router)
app.include_router(faculty_router)
app.include_router(student_router)
app.include_router(course_router)
app.include_router(subject_router)
app.include_router(attendance_router)
app.include_router(marks_router)
app.include_router(assignment_router)
app.include_router(performance_router)
app.include_router(risk_router)
app.include_router(prediction_router)
app.include_router(segmentation_router)
app.include_router(recommendation_router)
app.include_router(ai_assistant_router)
app.include_router(faculty_subject_router)
app.include_router(dashboard_router)
app.include_router(
    intelligence.router
)