import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

# Import database connection
from database import connect_db, disconnect_db

# Import routers
from routers import (
    application, auth, jobs, candidates, interviews, dashboard,
    interview_join, ai_tools, screenshots, settings, company,
    ai_interview, skill_suggestion, try_interview
)

from config.firebase_config import init_firebase
from service.screenshot_service import mount_screenshot_folder
from service.cron_cleanup import delete_old_screenshots


# ------------------------------------------
# 🚀 LIFESPAN (Replaces @app.on_event)
# ------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):

    print("🚀 Starting API… connecting to DB")
    await connect_db()

    print("🔥 Initializing Firebase…")
    init_firebase()

    # Start cleanup scheduler
    print("🧹 Starting screenshot cleanup scheduler…")
    cleanup_task = asyncio.create_task(schedule_cleanup_task())

    yield  # Application is running

    print("🛑 Shutting down… stopping tasks")
    cleanup_task.cancel()

    # Ensure DB disconnect
    await disconnect_db()
    print("👋 Shutdown complete")


# ------------------------------------------
# 🌐 FastAPI instance
# ------------------------------------------
app = FastAPI(
    title="HireLN API",
    description="API for HireLN - AI-Powered Hiring Platform",
    version="2.0.0",
    lifespan=lifespan,
    redirect_slashes=True
)

mount_screenshot_folder(app)


# ------------------------------------------
# 🧹 Background cleanup loop
# ------------------------------------------
async def schedule_cleanup_task():
    await asyncio.sleep(5)  # Wait until DB + app are ready

    while True:
        print("🧹 Running screenshot cleanup…")
        try:
            await delete_old_screenshots()
            print("✔️ Cleanup complete")
        except Exception as e:
            print("❌ Cleanup failed:", e)

        await asyncio.sleep(3600)  # 1 minute for testing
        # Change to 3600 for 1 hour in production


# ------------------------------------------
# 🔐 CORS
# ------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hireln.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------
# 📌 Include Routers
# ------------------------------------------
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(skill_suggestion.router, prefix="/api/skillsuggestions", tags=["Skill Suggestions"])
app.include_router(candidates.router, prefix="/api/candidates", tags=["Candidates"])
app.include_router(application.router, prefix="/api/application", tags=["application"])

app.include_router(interviews.router, prefix="/api/interviews", tags=["Interviews"])
app.include_router(try_interview.router, prefix="/api/try-interview", tags=["Try Interview"])
app.include_router(interview_join.router, prefix="/api/interview-join", tags=["Interview Join"])
app.include_router(ai_interview.router, prefix="/api/ai-interview", tags=["AI Interview"])
app.include_router(screenshots.router, prefix="/api/screenshots", tags=["Interview Screenshots"])

app.include_router(ai_tools.router, prefix="/api/ai-tools", tags=["AI Tools"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(company.router, prefix="/api/company", tags=["Company"])


# ------------------------------------------
# Health + Root
# ------------------------------------------
@app.get("/")
async def root():
    return {"message": "HireLN API v2.0.0 - AI-Powered Hiring Platform"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "2.0.0"}


# ------------------------------------------
# 🔥 Local Dev Runner
# ------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
