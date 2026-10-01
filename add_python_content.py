"""
Add modules and lessons to a course.
Usage: python add_python_content.py
"""
import requests

BASE_URL = "http://localhost:8000/api"
COURSE_ID = 2   # Python course ID — change if needed

# ═══════════════════════════════════════════════════════════
# STEP 1: Login as Instructor
# ═══════════════════════════════════════════════════════════
print("🔐 Logging in as instructor...")
login = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "instructor@demo.com", "password": "inst123"},
)

if login.status_code != 200:
    print(f"❌ Login failed: {login.status_code} — {login.text}")
    exit(1)

token = login.json()["access_token"]
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}
print(f"✅ Logged in successfully\n")


# ═══════════════════════════════════════════════════════════
# STEP 2: Create Modules
# ═══════════════════════════════════════════════════════════
modules_to_create = [
    {
        "title": "Getting Started with Python",
        "description": "Introduction, installation, and your first program",
        "order_index": 1,
    },
    {
        "title": "Python Basics",
        "description": "Variables, data types, and operators",
        "order_index": 2,
    },
    {
        "title": "Control Flow",
        "description": "If/else statements, loops, and comprehensions",
        "order_index": 3,
    },
    {
        "title": "Functions & Modules",
        "description": "Defining functions and importing modules",
        "order_index": 4,
    },
]

print(f"📚 Creating modules for course ID {COURSE_ID}...")
module_ids = []

for m in modules_to_create:
    r = requests.post(
        f"{BASE_URL}/instructor/courses/{COURSE_ID}/modules",
        json=m,
        headers=headers,
    )
    if r.status_code == 201:
        data = r.json()
        module_ids.append(data["id"])
        print(f"  ✅ Module '{data['title']}' (id={data['id']})")
    else:
        print(f"  ❌ Failed '{m['title']}' — {r.status_code} — {r.text[:100]}")

if not module_ids:
    print("\n❌ No modules created. Aborting.")
    exit(1)

print(f"\n✅ Created {len(module_ids)} modules\n")


# ═══════════════════════════════════════════════════════════
# STEP 3: Create Lessons per Module
# ═══════════════════════════════════════════════════════════
lessons_by_module_index = {
    0: [  # Getting Started
        {
            "title": "Welcome to Python",
            "type": "video",
            "content": "Course overview and what you'll build",
            "resource_url": "https://www.youtube.com/watch?v=kqtD5dpn9C8",
            "duration_minutes": 5,
            "order_index": 1,
            "is_preview": True,
        },
        {
            "title": "Installing Python & VS Code",
            "type": "video",
            "content": "Set up your development environment",
            "resource_url": "https://www.youtube.com/watch?v=YYXdXT2l-Gg",
            "duration_minutes": 12,
            "order_index": 2,
            "is_preview": False,
        },
        {
            "title": "Course Resources PDF",
            "type": "pdf",
            "content": "Downloadable resources for this course",
            "resource_url": "https://example.com/python-resources.pdf",
            "duration_minutes": 0,
            "order_index": 3,
            "is_preview": False,
        },
    ],
    1: [  # Python Basics
        {
            "title": "Variables & Data Types",
            "type": "video",
            "content": "Integers, strings, floats, booleans",
            "resource_url": "https://www.youtube.com/watch?v=Z1Yd7upQsXY",
            "duration_minutes": 20,
            "order_index": 1,
            "is_preview": False,
        },
        {
            "title": "Operators in Python",
            "type": "video",
            "content": "Arithmetic, comparison, and logical operators",
            "resource_url": "https://www.youtube.com/watch?v=v5MR5JnKcZI",
            "duration_minutes": 15,
            "order_index": 2,
            "is_preview": False,
        },
        {
            "title": "Working with Strings",
            "type": "video",
            "content": "String methods, formatting, and f-strings",
            "resource_url": "https://www.youtube.com/watch?v=Ctqi5Y4X-jA",
            "duration_minutes": 22,
            "order_index": 3,
            "is_preview": False,
        },
    ],
    2: [  # Control Flow
        {
            "title": "If / Elif / Else Statements",
            "type": "video",
            "content": "Conditional logic in Python",
            "resource_url": "https://www.youtube.com/watch?v=Zp5MuPOtsSY",
            "duration_minutes": 18,
            "order_index": 1,
            "is_preview": False,
        },
        {
            "title": "For Loops",
            "type": "video",
            "content": "Iterating through sequences",
            "resource_url": "https://www.youtube.com/watch?v=94UHCEmprCY",
            "duration_minutes": 15,
            "order_index": 2,
            "is_preview": False,
        },
        {
            "title": "While Loops",
            "type": "video",
            "content": "Conditional iteration",
            "resource_url": "https://www.youtube.com/watch?v=6iF8Xb7Z3wQ",
            "duration_minutes": 12,
            "order_index": 3,
            "is_preview": False,
        },
        {
            "title": "Quiz: Control Flow",
            "type": "quiz",
            "content": "Test your understanding of control flow",
            "duration_minutes": 10,
            "order_index": 4,
            "is_preview": False,
        },
    ],
    3: [  # Functions & Modules
        {
            "title": "Defining Functions",
            "type": "video",
            "content": "def keyword, parameters, and return values",
            "resource_url": "https://www.youtube.com/watch?v=9Os0o3wzS_I",
            "duration_minutes": 20,
            "order_index": 1,
            "is_preview": False,
        },
        {
            "title": "Args & Kwargs",
            "type": "video",
            "content": "Advanced function arguments",
            "resource_url": "https://www.youtube.com/watch?v=4jBJhCaNrWU",
            "duration_minutes": 18,
            "order_index": 2,
            "is_preview": False,
        },
        {
            "title": "Importing Modules",
            "type": "video",
            "content": "import, from...import, and pip",
            "resource_url": "https://www.youtube.com/watch?v=CqvZ3vGoGs0",
            "duration_minutes": 15,
            "order_index": 3,
            "is_preview": False,
        },
    ],
}

print("📝 Adding lessons to modules...")
total_lessons = 0

for idx, module_id in enumerate(module_ids):
    lessons = lessons_by_module_index.get(idx, [])
    print(f"\n  📖 Module ID {module_id} ({len(lessons)} lessons):")

    for lesson in lessons:
        r = requests.post(
            f"{BASE_URL}/instructor/courses/modules/{module_id}/lessons",
            json=lesson,
            headers=headers,
        )
        if r.status_code == 201:
            print(f"    ✅ {lesson['title']}")
            total_lessons += 1
        else:
            print(f"    ❌ {lesson['title']} — {r.status_code} — {r.text[:100]}")


# ═══════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"🎉 COMPLETE!")
print(f"   Modules created: {len(module_ids)}")
print(f"   Lessons created: {total_lessons}")
print(f"\n👉 Refresh browser:")
print(f"   http://localhost:5173/student/courses/{COURSE_ID}/learn")
print(f"{'='*50}")