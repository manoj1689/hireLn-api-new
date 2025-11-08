import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Union
from database import get_db
from models.schemas import InterviewJoinResponse, InterviewResponse, InterviewStatus, ScheduleInterviewResponse, UserResponse
from auth.dependencies import get_user_or_interview_auth
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter()



# ------------------------------------------------------
# ✅ JOIN INTERVIEW (with auth)
# ------------------------------------------------------
@router.get("/join", response_model=InterviewJoinResponse)
async def join_interview(
    interview_id: str,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth),
):
    """Join an interview using authentication header (Bearer or X-Interview-Token)."""
    
    db = get_db()
    try:
        # ✅ Access control
        where_clause = {"id": interview_id}
        if isinstance(auth_data, UserResponse):
            where_clause["scheduledById"] = auth_data.id
        elif isinstance(auth_data, dict):
            allowed_id = auth_data.get("interviewId")
            if allowed_id and allowed_id != interview_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access this interview",
                )

        # Fetch interview + related data
        interview = await db.interview.find_unique(
            where=where_clause,
            include={"candidate": True, "application": True, "job": True},
        )

        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found",
            )

        # Prevent joining if interview is cancelled/completed
        if interview.status in [InterviewStatus.CANCELLED, InterviewStatus.COMPLETED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Interview is {interview.status.lower()}",
            )

        # Auto-update to JOINED if scheduled
        if interview.status == InterviewStatus.SCHEDULED:
            await db.interview.update(
                where={"id": interview_id},
                data={"status": InterviewStatus.JOINED},
            )

        # Candidate, Application, Job fallback-safe handling
        candidate = getattr(interview, "candidate", None)
        application = getattr(interview, "application", None)
        job = getattr(interview, "job", None)

        # Parse interviewers
        interviewers = []
        try:
            if interview.interviewers:
                if isinstance(interview.interviewers, str):
                    interviewers = json.loads(interview.interviewers)
                elif isinstance(interview.interviewers, list):
                    interviewers = interview.interviewers
        except Exception:
            interviewers = []

        # Build interview response
        interview_response = ScheduleInterviewResponse(
            id=interview.id,
            candidateId=candidate.id if candidate else "unknown",
            candidateName=candidate.name if candidate else "Unknown Candidate",
            candidateEmail=candidate.email if candidate else "N/A",
            applicationId=application.id if application else None,
            jobId=application.jobId if application else None,
            jobTitle=job.title if job else "N/A",
            interviewType=interview.type,
            status=InterviewStatus.JOINED,
            scheduledAt=interview.scheduledAt,
            duration=interview.duration,
            timezone=interview.timezone,
            interviewers=interviewers,
            meetingLink=interview.meetingLink,
            location=interview.location,
            notes=interview.notes,
            feedback=interview.feedback,
            invitationSent=interview.invitationSent,
            joinToken=interview.joinToken,
            tokenExpiry=interview.tokenExpiry,
            createdAt=interview.createdAt,
            updatedAt=interview.updatedAt,
            startedAt=interview.startedAt,
            completedAt=interview.completedAt,

            # Candidate Fields
            candidateEducation=getattr(candidate, "education", None),
            candidateExperience=getattr(candidate, "experience", None),
            candidateSkills=getattr(candidate, "technicalSkills", None),
            candidateLinkedIn=getattr(candidate, "linkedin", None),
            candidateGitHub=getattr(candidate, "github", None),
            candidateLocation=getattr(candidate, "location", None),

            # Application
            coverLetter=getattr(application, "coverLetter", None),

            # Job Fields
            jobDepartment=getattr(job, "department", None),
            jobDescription=getattr(job, "description", None),
            jobResponsibility=getattr(job, "responsibilities", None),
            jobSkills=getattr(job, "skills", None),
            jobEducation=getattr(job, "education", None),
            jobCertificates=getattr(job, "certifications", None),
            jobPublished=getattr(job, "publishedAt", None),
        )

        redirect_url = f"/ai-interview-round?interview_id={interview_id}"

        return InterviewJoinResponse(
            success=True,
            message="Successfully joined the interview session.",
            interview=interview_response,
            redirectUrl=redirect_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining interview {interview_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


# ------------------------------------------------------
# ✅ CONFIRM INTERVIEW
# ------------------------------------------------------
@router.post("/confirm/{interview_id}")
async def confirm_interview(
    interview_id: str,
    confirmed: bool = True,
    response_message: Optional[str] = None,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth),
):
    """Confirm or cancel interview attendance."""
   
    db = get_db()
    try:
        # Access restriction
        where_clause = {"id": interview_id}
        if isinstance(auth_data, UserResponse):
            where_clause["scheduledById"] = auth_data.id
        elif isinstance(auth_data, dict):
            allowed_id = auth_data.get("interviewId")
            if allowed_id and allowed_id != interview_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized for this interview",
                )

        interview = await db.interview.find_unique(where=where_clause)
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found",
            )

        new_status = (
            InterviewStatus.CONFIRMED if confirmed else InterviewStatus.CANCELLED
        )
        update_data = {"status": new_status}

        if response_message:
            update_data["notes"] = f"{interview.notes or ''}\n\nCandidate response: {response_message}"

        await db.interview.update(where={"id": interview_id}, data=update_data)

        return {
            "success": True,
            "message": f"Interview {'confirmed' if confirmed else 'cancelled'} successfully",
            "status": new_status,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming interview {interview_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


# ------------------------------------------------------
# ✅ START INTERVIEW
# ------------------------------------------------------
@router.put("/{interview_id}/start")
async def start_interview(
    interview_id: str,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth),
):
    """Mark interview as IN_PROGRESS."""
  
    db = get_db()
    try:
        # Access control
        where_clause = {"id": interview_id}
        if isinstance(auth_data, UserResponse):
            where_clause["scheduledById"] = auth_data.id
        elif isinstance(auth_data, dict):
            allowed_id = auth_data.get("interviewId")
            if allowed_id and allowed_id != interview_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to start this interview",
                )

        interview = await db.interview.find_unique(where=where_clause)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")
        # ✅ Set current UTC timestamp when starting
        now_utc = datetime.now(timezone.utc)
        await db.interview.update(
            where={"id": interview_id},
            data={
                "status": InterviewStatus.IN_PROGRESS,
                "startedAt": datetime.now(timezone.utc),
            },
        )

        return {
            "success": True,
            "message": "Interview started successfully",
            "status": InterviewStatus.IN_PROGRESS
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting interview {interview_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ------------------------------------------------------
# ✅ COMPLETE INTERVIEW
# ------------------------------------------------------
@router.put("/{interview_id}/complete")
async def complete_interview(
    interview_id: str,
    auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth),
):
    """Mark interview as COMPLETED."""
   
    db = get_db()
    try:
        where_clause = {"id": interview_id}
        if isinstance(auth_data, UserResponse):
            where_clause["scheduledById"] = auth_data.id
        elif isinstance(auth_data, dict):
            allowed_id = auth_data.get("interviewId")
            if allowed_id and allowed_id != interview_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to complete this interview",
                )

        interview = await db.interview.find_unique(where=where_clause)
        if not interview:
            raise HTTPException(status_code=404, detail="Interview not found")

        await db.interview.update(
            where={"id": interview_id},
            data={
                "status": InterviewStatus.COMPLETED,
                "completedAt": datetime.now(timezone.utc),
            },
        )

        return {
            "success": True,
            "message": "Interview completed successfully",
            "status": InterviewStatus.COMPLETED,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing interview {interview_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
