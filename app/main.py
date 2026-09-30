from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import Base, engine
from app.models import *  # noqa

from app.routers import auth
from app.routers import users as users_module
from app.routers import courses as courses_module
from app.routers import enrollments as enrollments_module
from app.routers import assignments as assignments_module
from app.routers import submissions as submissions_module
from app.routers import payments as payments_module
from app.routers import notifications as notifications_module

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CourseHub API",
    description="Course Management System Backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════
# 🌐 PUBLIC
# ═══════════════════════════════════════════════════════════
app.include_router(auth.router)
app.include_router(courses_module.public_router)
app.include_router(assignments_module.public_router)

# ═══════════════════════════════════════════════════════════
# 👨‍🏫 INSTRUCTOR
# ═══════════════════════════════════════════════════════════
app.include_router(courses_module.instructor_router)
app.include_router(enrollments_module.instructor_router)
app.include_router(assignments_module.instructor_router)
app.include_router(submissions_module.instructor_router)

# ═══════════════════════════════════════════════════════════
# 🎓 STUDENT
# ═══════════════════════════════════════════════════════════
app.include_router(users_module.profile_router)
app.include_router(enrollments_module.student_router)
app.include_router(submissions_module.student_router)
app.include_router(payments_module.student_router)
app.include_router(notifications_module.user_router)

# ═══════════════════════════════════════════════════════════
# 🛡️ ADMIN
# ═══════════════════════════════════════════════════════════
app.include_router(users_module.admin_router)
app.include_router(courses_module.admin_router)
app.include_router(enrollments_module.admin_router)
app.include_router(assignments_module.admin_router)
app.include_router(submissions_module.admin_router)
app.include_router(payments_module.admin_router)
app.include_router(notifications_module.admin_router)


@app.get("/")
def root():
    return {"message": "CourseHub API 🚀", "docs": "/docs"}