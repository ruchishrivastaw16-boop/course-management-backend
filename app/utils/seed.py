from app.database import SessionLocal
from app.models import *
from app.core.security import hash_password

def seed():
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("⚠️  Data already exists. Skipping seed.")
            return

        admin = User(
            full_name="Admin User", email="admin@demo.com",
            password_hash=hash_password("admin123"), role=UserRole.admin,
        )
        instructor = User(
            full_name="John Instructor", email="instructor@demo.com",
            password_hash=hash_password("inst123"), role=UserRole.instructor,
        )
        student = User(
            full_name="Jane Student", email="student@demo.com",
            password_hash=hash_password("stud123"), role=UserRole.student,
        )
        db.add_all([admin, instructor, student])
        db.commit()

        courses = [
            Course(
                instructor_id=instructor.id, title="React Masterclass 2025",
                slug="react-masterclass",
                description="Master React from basics to advanced hooks.",
                category="Web Development", level=CourseLevel.intermediate,
                status=CourseStatus.published, price=49.99, is_free=False,
                duration_hours=24, lessons_count=68, rating=4.8, students_count=1240,
                thumbnail="https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=800",
            ),
            Course(
                instructor_id=instructor.id, title="Python for Beginners",
                slug="python-for-beginners",
                description="Learn Python from scratch.",
                category="Programming", level=CourseLevel.beginner,
                status=CourseStatus.published, price=0, is_free=True,
                duration_hours=18, lessons_count=52, rating=4.9, students_count=3420,
                thumbnail="https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=800",
            ),
            Course(
                instructor_id=instructor.id, title="Node.js & REST API",
                slug="nodejs-api",
                description="Build scalable backend APIs with Node.js.",
                category="Web Development", level=CourseLevel.intermediate,
                status=CourseStatus.pending, price=59.99, is_free=False,
                duration_hours=22, lessons_count=58, rating=4.6, students_count=720,
                thumbnail="https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=800",
            ),
        ]
        db.add_all(courses)
        db.commit()

        # Add modules/lessons for first course
        c1 = courses[0]
        m1 = Module(course_id=c1.id, title="Getting Started", order_index=1)
        m2 = Module(course_id=c1.id, title="React Fundamentals", order_index=2)
        db.add_all([m1, m2])
        db.commit()

        db.add_all([
            Lesson(module_id=m1.id, title="Welcome", type=LessonType.video,
                   duration_minutes=5, order_index=1, is_preview=True),
            Lesson(module_id=m1.id, title="Setup", type=LessonType.video,
                   duration_minutes=12, order_index=2),
            Lesson(module_id=m2.id, title="JSX & Components", type=LessonType.video,
                   duration_minutes=18, order_index=1),
            Lesson(module_id=m2.id, title="Props & State", type=LessonType.video,
                   duration_minutes=22, order_index=2),
        ])
        db.commit()

        print("✅ Seed complete!")
        print("   Admin:      admin@demo.com / admin123")
        print("   Instructor: instructor@demo.com / inst123")
        print("   Student:    student@demo.com / stud123")
    finally:
        db.close()

if __name__ == "__main__":
    seed()