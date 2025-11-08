import calendar
from fastapi import APIRouter, Depends
from typing import List
from database import get_db
from models.schemas import (
    DashboardMetrics, MetricWithChange, RecruitmentTrend, PipelineStage, 
    ActivityItem, UserResponse
)
from auth.dependencies import get_current_user
from datetime import datetime, timedelta, timezone

router = APIRouter()

# Helper
def calculate_change(current, previous):
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(current_user: UserResponse = Depends(get_current_user)):
    db = get_db()
    user_id = current_user.id

    now = datetime.utcnow()
    start_current_month = now.replace(day=1)
    start_last_month = (start_current_month - timedelta(days=1)).replace(day=1)
    end_last_month = start_current_month

    # ✅ Total Jobs — user only
    total_jobs_current = await db.job.count(
        where={"userId": user_id, "createdAt": {"gte": start_current_month}}
    )
    total_jobs_last = await db.job.count(
        where={"userId": user_id, "createdAt": {"gte": start_last_month, "lt": end_last_month}}
    )
    job_change = calculate_change(total_jobs_current, total_jobs_last)

    # ✅ Active Candidates — user only
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)

    active_current = await db.application.count(
        where={"userId": user_id, "appliedAt": {"gte": thirty_days_ago}}
    )
    active_last = await db.application.count(
        where={"userId": user_id, "appliedAt": {"gte": sixty_days_ago, "lt": thirty_days_ago}}
    )
    active_change = calculate_change(active_current, active_last)

    # ✅ Hiring Success Rate — user only
    total_applications = await db.application.count(where={"userId": user_id})
    hired_applications = await db.application.count(where={"userId": user_id, "status": "HIRED"})
    hiring_success_rate = (hired_applications / total_applications * 100) if total_applications else 0

    total_apps_last = await db.application.count(
        where={"userId": user_id, "appliedAt": {"gte": start_last_month, "lt": end_last_month}}
    )
    hired_apps_last = await db.application.count(
        where={
            "userId": user_id,
            "appliedAt": {"gte": start_last_month, "lt": end_last_month},
            "status": "HIRED"
        }
    )
    success_rate_last = (hired_apps_last / total_apps_last * 100) if total_apps_last else 0
    success_change = calculate_change(hiring_success_rate, success_rate_last)

    # ✅ AI Interviews Completed — ***scheduledById***
    ai_interviews_current = await db.interview.count(
        where={"scheduledById": user_id, "status": "COMPLETED", "createdAt": {"gte": start_current_month}}
    )
    ai_interviews_last = await db.interview.count(
        where={"scheduledById": user_id, "status": "COMPLETED", "createdAt": {"gte": start_last_month, "lt": end_last_month}}
    )
    ai_change = calculate_change(ai_interviews_current, ai_interviews_last)

    # ✅ Avg Time to Hire — placeholder
    avg_time_to_hire = 1
    avg_time_last = 2
    avg_time_change = calculate_change(avg_time_to_hire, avg_time_last)

    return DashboardMetrics(
        totalJobs=MetricWithChange(value=total_jobs_current, change=job_change),
        activeCandidates=MetricWithChange(value=active_current, change=active_change),
        hiringSuccessRate=MetricWithChange(value=round(hiring_success_rate, 1), change=round(success_change, 1)),
        avgTimeToHire=MetricWithChange(value=avg_time_to_hire, change=avg_time_change),
        aiInterviewsCompleted=MetricWithChange(value=ai_interviews_current, change=ai_change),
    )


@router.get("/recruitment-trends", response_model=List[RecruitmentTrend])
async def get_recruitment_trends(current_user: UserResponse = Depends(get_current_user)):
    db = get_db()
    user_id = current_user.id

    current_date = datetime.utcnow()
    trends = []

    for i in range(5, -1, -1):
        target_date = current_date - timedelta(days=30 * i)
        year, month = target_date.year, target_date.month
        start_of_month = datetime(year, month, 1)
        end_of_month = datetime(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)

        applications_count = await db.application.count(
            where={
                "userId": user_id,
                "appliedAt": {"gte": start_of_month, "lte": end_of_month}
            }
        )

        trends.append(RecruitmentTrend(month=calendar.month_abbr[month], applications=applications_count))

    return trends


@router.get("/pipeline", response_model=List[PipelineStage])
async def get_pipeline_stages(current_user: UserResponse = Depends(get_current_user)):
    db = get_db()
    user_id = current_user.id

    applied = await db.application.count(where={"userId": user_id, "status": "APPLIED"})
    screening = await db.application.count(where={"userId": user_id, "status": "SCREENING"})
    interview = await db.application.count(where={"userId": user_id, "status": "INTERVIEW"})
    offer = await db.application.count(where={"userId": user_id, "status": "OFFER"})
    hired = await db.application.count(where={"userId": user_id, "status": "HIRED"})

    total = applied + screening + interview + offer + hired

    if total == 0:
        return [
            PipelineStage(stage=s, count=0, percentage=0)
            for s in ["Applied", "Screening", "Interview", "Offer", "Hired"]
        ]

    return [
        PipelineStage(stage="Applied", count=applied, percentage=round(applied/total*100)),
        PipelineStage(stage="Screening", count=screening, percentage=round(screening/total*100)),
        PipelineStage(stage="Interview", count=interview, percentage=round(interview/total*100)),
        PipelineStage(stage="Offer", count=offer, percentage=round(offer/total*100)),
        PipelineStage(stage="Hired", count=hired, percentage=round(hired/total*100)),
    ]


@router.get("/activities", response_model=List[ActivityItem])
async def get_recent_activities(current_user: UserResponse = Depends(get_current_user)):
    db = get_db()
    user_id = current_user.id

    activities = await db.activity.find_many(
        where={"userId": user_id},
        
    )

    if not activities:
        return []

    return [
        ActivityItem(
            id=a.id,
            type=a.type,
            title=a.title,
            description=a.description,
            time=format_time_ago(a.createdAt)
        )
        for a in activities
    ]


@router.get("/department-stats", response_model=List[dict])
async def get_department_stats(current_user: UserResponse = Depends(get_current_user)):
    db = get_db()
    user_id = current_user.id

    departments = await db.query_raw(
        """
        SELECT department, COUNT(*) AS job_count
        FROM "jobs"
        WHERE "userId" = $1
        GROUP BY department
        ORDER BY job_count DESC
        """,
        user_id,
    )

    return [{"department": d["department"], "jobCount": d["job_count"]} for d in departments]




def format_time_ago(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = diff.total_seconds()
    minutes = int(seconds // 60)
    hours = int(minutes // 60)
    days = int(hours // 24)

    if seconds < 60:
        return "just now"
    elif minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        return f"{days} day{'s' if days != 1 else ''} ago"
