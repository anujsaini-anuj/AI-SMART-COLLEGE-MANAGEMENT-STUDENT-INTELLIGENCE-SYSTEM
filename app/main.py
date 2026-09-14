from fastapi import FastAPI, Depends

from app.database.database import Base, engine
from app.database.models import User

from app.routers.auth import router as auth_router
from app.routers.department import router as department_router
from app.routers.faculty import router as faculty_router
from app.routers.student import router as student_router


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
