from datetime import datetime
import json
from fastapi import APIRouter, HTTPException, status as http_status, Depends, Query
from typing import List, Optional, Union

from grpc import Status
from service.activity_service import ActivityHelpers
from database import get_db
from models.schemas import ( 
    ApplicationCreate,  ApplicationResponse, InterviewResponse, InterviewScheduleRequest, UserResponse, ApplicationStatus
)
from auth.dependencies import get_current_user, get_user_or_interview_auth
from models.schemas import InterviewStatus
from firebase_admin import messaging
from utils.token_utils import generate_interview_token, generate_token_expiry

router = APIRouter()
#create Application.
@router.post("/applications", response_model=ApplicationResponse)
async def create_application(
    application_data: ApplicationCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create a new job application.
       ✅ If user = GUEST → auto ACCEPT, no token, no email.
       ✅ If normal user → invite process (not included here).
    """

    db = get_db()

    # ✅ Check if application already exists
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

    # Convert request payload
    app_data = application_data.dict()
    app_data["userId"] = current_user.id

    # ✅ If user is GUEST → auto-ACCEPT, no link
    if current_user.role == "GUEST":
        app_data["status"] = "APPLIED"
        app_data["joinToken"] = None
        app_data["tokenExpiry"] = None

        # ✅ Create job application
        application = await db.application.create(data=app_data)

        # ✅ Log activity (guest mode)
        job_details = await db.job.find_unique(where={"id": application.jobId})
        candidate = await db.candidate.find_unique(where={"id": application.candidateId})

        if candidate and job_details:
            await ActivityHelpers.log_application_received(
                user_id=current_user.id,
                application_id=application.id,
                candidate_name=candidate.name,
                job_title=job_details.title
            )

        # ✅ Return without sending email or token
        return ApplicationResponse(**application.dict())

#schedule Interview

@router.post("/schedule", response_model=InterviewResponse)
async def schedule_interview(
    interview_data: InterviewScheduleRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """Schedule a new interview - ONLY for guest users"""
    
    # ✅ Allow only GUEST
    if current_user.role != "GUEST":
        raise HTTPException(
            status_code=Status.HTTP_403_FORBIDDEN,
            detail="Only guest users are allowed to schedule interviews"
        )

    db = get_db()
    
    # Check candidate
    candidate = await db.candidate.find_unique(where={"id": interview_data.candidateId})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    # Check application and job
    application = await db.application.find_unique(
        where={"id": interview_data.applicationId},
        include={"job": True}
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = application.job
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Parse scheduled date & time
    try:
        scheduled_datetime = datetime.strptime(
            f"{interview_data.scheduledDate} {interview_data.scheduledTime}",
            "%Y-%m-%d %H:%M"
        )
    except Exception:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail="Invalid date or time format"
        )
    
    join_token = generate_interview_token()
    token_expiry = generate_token_expiry(hours=48)
    
    # Prepare interview data
    interview_data_dict = {
        "candidateId": candidate.id,
        "applicationId": application.id,
        "scheduledById": current_user.id,
        "jobId": job.id,
        "type": interview_data.type,
        "scheduledAt": scheduled_datetime,
        "duration": interview_data.duration,
        "timezone": interview_data.timezone,
        "meetingLink": interview_data.meetingLink,
        "location": interview_data.location,
        "notes": interview_data.notes,
        "joinToken": join_token,
        "tokenExpiry": token_expiry,
        "status": "SCHEDULED",
        "interviewers": json.dumps([i.dict() for i in interview_data.interviewers]) if interview_data.interviewers else None
    }
    
    interview = await db.interview.create(data=interview_data_dict)

    if application.status == "APPLIED":
        await db.application.update(
            where={"id": application.id},
            data={"status": "INTERVIEW"}
        )
    
    await ActivityHelpers.log_interview_scheduled(
        user_id=current_user.id,
        interview_id=interview.id,
        candidate_name=candidate.name,
        job_title=job.title,
        scheduled_date=scheduled_datetime
    )
    
    response = {
        "id": interview.id,
        "candidateId": candidate.id,
        "candidateName": candidate.name,
        "candidateEmail": candidate.email,
        "applicationId": application.id,
        "jobId": job.id,
        "jobTitle": job.title,
        "interviewType": interview.type,
        "status": interview.status,
        "scheduledAt": interview.scheduledAt,
        "duration": interview.duration,
        "timezone": interview.timezone,
        "interviewers": interview_data.interviewers,
        "meetingLink": interview.meetingLink,
        "location": interview.location,
        "notes": interview.notes,
        "feedback": None,
        "invitationSent": interview.invitationSent,
        "joinToken": interview.joinToken,
        "tokenExpiry": interview.tokenExpiry,
        "createdAt": interview.createdAt,
        "updatedAt": interview.updatedAt
    }

    return InterviewResponse(**response)

