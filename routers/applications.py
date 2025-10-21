import json
from fastapi import APIRouter, HTTPException, status as http_status, Depends, Query
from typing import List, Optional, Union
from service.activity_service import ActivityHelpers
from database import get_db
from models.schemas import ( 
    ApplicationCreate, ApplicationUpdate, ApplicationResponse, UserResponse, ApplicationStatus
)
from auth.dependencies import get_current_user
from models.schemas import InterviewStatus

from utils.token_utils import generate_interview_token

router = APIRouter()


@router.post("/applications", response_model=ApplicationResponse)
async def create_application(
    application_data: ApplicationCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create a new job application with initial status = INVITED"""
    db = get_db()
    
    # Check if already exists
    existing_application = await db.application.find_unique(
        where={
            "jobId_candidateId": {
                "jobId": application_data.jobId,
                "candidateId": application_data.candidateId
            }
        }
    )
    if existing_application:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Application already exists for this job and candidate"
        )
    
    # Create with INVITED status
    app_data = application_data.dict()
    app_data["userId"] = current_user.id
    application = await db.application.create(data=app_data)

    # Fetch job & candidate
    details = await db.job.find_unique(where={"id": application.jobId})
    candidate = await db.candidate.find_unique(where={"id": application.candidateId})
    join_token = generate_interview_token()
    
    if candidate and details:
        # Send invitation email
        from service.email_service import EmailService
        import asyncio
        email_service = EmailService()

        loop = asyncio.get_event_loop()
        email_sent = await loop.run_in_executor(
            None,
            email_service.send_interview_accept,
            candidate.email,
            candidate.name,
            application.id,
            details.id,
            details.title,
            join_token
        )

        if email_sent:
            print(f"Invitation sent to {candidate.email} for {details.title}", flush=True)
        else:
            print(f"Failed to send invitation to {candidate.email}", flush=True)

        # Log activity
        await ActivityHelpers.log_application_received(
            user_id=current_user.id,
            application_id=application.id,
            candidate_name=candidate.name,
            job_title=details.title
        )

    return ApplicationResponse(**application.dict())

@router.post("/applications/{application_id}/accept", response_model=ApplicationResponse)

async def accept_application(application_id: str):
    """Update application status to APPLIED without authentication"""
    db = get_db()

    # 🔎 Find application
    application = await db.application.find_unique(where={"id": application_id})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # ✅ Update status → APPLIED
    application = await db.application.update(
        where={"id": application_id},
        data={"status": "APPLIED"}
    )

    return ApplicationResponse(**application.dict())



@router.get("/applications/{application_id}", response_model=ApplicationResponse)
async def get_application(application_id: str):
    """Return application data by ID"""
    db = get_db()

    # 🔎 Find application
    application = await db.application.find_unique(where={"id": application_id})
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # 📝 Return the application data
    return ApplicationResponse(**application.dict())




@router.get("/applications/list/", response_model=List[ApplicationResponse])
async def get_applications(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    candidate_id: Optional[str] = Query(None, description="Filter by candidate ID"),
    status: Optional[ApplicationStatus] = Query(None, description="Filter by application status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get applications for the authenticated user with optional filters"""
    db = get_db()

    # Build filters, always include current user's applications
    where_clause = {"userId": current_user.id}

    if job_id:
        where_clause["jobId"] = job_id
    if candidate_id:
        where_clause["candidateId"] = candidate_id
    if status:
        where_clause["status"] = status

    try:
        applications = await db.application.find_many(
            where=where_clause,
            skip=skip,
            take=limit,
            include={
                "job": True,
                "candidate": True
            }
        )

        return [
            ApplicationResponse(
                id=app.id,
                jobId=app.jobId,
                candidateId=app.candidateId,
                coverLetter=app.coverLetter,
                status=app.status,
                matchScore=app.matchScore,
                userId=app.userId,
                notes=app.notes,
                appliedAt=app.appliedAt,
                updatedAt=app.updatedAt
            )
            for app in applications
        ]

    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching applications: {str(e)}"
        )

@router.put("/applications/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: str,
    application_data: ApplicationUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update an application status"""
    db = get_db()
    
    # Check if application exists
    existing_application = await db.application.find_unique(where={"id": application_id})
    if not existing_application:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    update_data = application_data.dict(exclude_unset=True)
    application = await db.application.update(
        where={"id": application_id},
        data=update_data
    )
   

    # Log activity if status changed
    if application_data.status and application_data.status != existing_application.status:
        if existing_application.job and existing_application.candidate:
            await ActivityHelpers.log_application_status_changed(
                user_id=current_user.id,
                application_id=application.id,
                candidate_name=existing_application.candidate.name,
                job_title=existing_application.job.title,
                new_status=application_data.status.value
            )
   
    return ApplicationResponse(**application.dict())

# Add a debug endpoint to check what data exists
@router.get("/debug/applications")
async def debug_applications(
    current_user: UserResponse = Depends(get_current_user)
):
    """Debug endpoint to see all applications data"""
    db = get_db()
    
    try:
        # Get all applications
        applications = await db.application.find_many(
            include={
                "job": True,
                "candidate": True
            }
        )
        
        # Get all jobs
        jobs = await db.job.find_many()
        
        # Get all candidates
        candidates = await db.candidate.find_many()
        
        return {
            "total_applications": len(applications),
            "total_jobs": len(jobs),
            "total_candidates": len(candidates),
            "applications": [
                {
                    "id": app.id,
                    "jobId": app.jobId,
                    "candidateId": app.candidateId,
                    "status": app.status,
                    "job_title": app.job.title if app.job else "No job",
                    "candidate_name": app.candidate.name if app.candidate else "No candidate"
                }
                for app in applications
            ],
            "jobs": [{"id": job.id, "title": job.title} for job in jobs],
            "candidates": [{"id": candidate.id, "name": candidate.name} for candidate in candidates]
        }
    except Exception as e:
        return {"error": str(e)}

