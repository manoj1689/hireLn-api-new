import json
from fastapi import APIRouter, HTTPException, status as http_status, Depends, Query
from typing import List, Optional, Union
from service.activity_service import ActivityHelpers
from database import get_db
from models.schemas import (
    CandidateCreate, CandidateResponse,UserResponse, 
)
from auth.dependencies import get_current_user, get_current_user_optional

router = APIRouter()

@router.post("/add", response_model=CandidateResponse)
async def create_candidate(
    candidate_data: CandidateCreate,
    current_user: Optional[UserResponse] = Depends(get_current_user_optional)
):
    """Create a new candidate. Guests can create without authentication."""
    db = get_db()

    # ✅ If isGuest is False, require authentication
    if not candidate_data and not current_user:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for non-guest candidates"
        )

    # ✅ Check if candidate already exists
    existing_candidate = await db.candidate.find_unique(where={"email": candidate_data.email})
    if existing_candidate:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Candidate with this email already exists"
        )

    # ✅ Convert Pydantic model to dict
    candidate_dict = candidate_data.dict()

    # ✅ Assign userId only if not guest
    if not candidate_data and current_user:
        candidate_dict["userId"] = current_user.id
    else:
        candidate_dict["userId"] = None  # Guests don't have an associated user

    # ✅ Fields to serialize as JSON strings before storing
    json_fields = [
        "education",
        "experience",
        "certifications",
        "projects",
        "languages",
        "previousJobs",
        "personalInfo"
    ]

    for field in json_fields:
        if candidate_dict.get(field) is not None:
            candidate_dict[field] = json.dumps(candidate_dict[field])

    # ✅ Create candidate in DB
    candidate = await db.candidate.create(data=candidate_dict)
    #    print("Candidate JSON (after serialization):", json.dumps(candidate_dict, indent=2))

    # ✅ Prepare response
    response_data = candidate.dict()
    response_data["applicationStatus"] = None
    response_data["interviewStatus"] = None

    # ✅ Log activity only for authenticated users
    if current_user:
        await ActivityHelpers.log_candidate_added(
            user_id=current_user.id,
            candidate_id=candidate.id,
            candidate_name=candidate.name
        )

    return CandidateResponse(**response_data)

@router.get("/", response_model=List[CandidateResponse])
async def get_candidates(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
    technicalSkills: Optional[List[str]] = Query(None),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get all candidates with optional filtering by search and technical skills only"""
    db = get_db()
    
    where_clause = {"userId": current_user.id}

    # Search by name/email/skills
    if search:
        where_clause["OR"] = [
            {"name": {"contains": search, "mode": "insensitive"}},
            {"email": {"contains": search, "mode": "insensitive"}},
            {"technicalSkills": {"has": search}}
        ]

    # Filter by technicalSkills
    if technicalSkills:
        where_clause["AND"] = where_clause.get("AND", []) + [
            {"technicalSkills": {"hasSome": technicalSkills}}
        ] # type: ignore

    candidates = await db.candidate.find_many(
        where=where_clause,
        skip=skip,
        take=limit,
        include={
            "applications": {
                "where": {"userId": current_user.id},
                "include": {
                    "interviews": {
                        "order_by": {"scheduledAt": "desc"}
                    }
                },
                "order_by": {"appliedAt": "desc"}
            }
        }
    )
    
    result = []
    for candidate in candidates:
        latest_application_status = None
        latest_interview_status = None
        
        if candidate.applications:
            latest_app = candidate.applications[0]
            latest_application_status = latest_app.status

            all_interviews = []
            for app in candidate.applications:
                if app.interviews:
                    all_interviews.extend(app.interviews)
            
            if all_interviews:
                sorted_interviews = sorted(all_interviews, key=lambda x: x.scheduledAt, reverse=True)
                latest_interview_status = sorted_interviews[0].status
        
        candidate_data = candidate.dict()
        candidate_data["applicationStatus"] = latest_application_status
        candidate_data["interviewStatus"] = latest_interview_status
        
        result.append(CandidateResponse(**candidate_data))
    
    return result

@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get a specific candidate by ID with application and interview status"""
    db = get_db()
    
    candidate = await db.candidate.find_unique(
        where={"id": candidate_id},
        include={
            "applications": {
                "where": {"userId": current_user.id},  # Only get applications created by current user
                "include": {
                    "interviews": {
                        "order_by": {"scheduledAt": "desc"}
                    }
                },
                "order_by": {"appliedAt": "desc"}
            }
        }
    )
    
    if not candidate:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Get the most recent application status
    latest_application_status = None
    latest_interview_status = None
    
    if candidate.applications:
        # Get the most recent application
        latest_app = candidate.applications[0]  # Already ordered by appliedAt desc
        latest_application_status = latest_app.status
        
        # Get the most recent interview status from all applications
        all_interviews = []
        for app in candidate.applications:
            if app.interviews:
                all_interviews.extend(app.interviews)
        
        if all_interviews:
            # Sort all interviews by scheduledAt desc and get the latest
            sorted_interviews = sorted(all_interviews, key=lambda x: x.scheduledAt, reverse=True)
            latest_interview_status = sorted_interviews[0].status
    
    # Build candidate response with original structure plus status fields
    candidate_data = candidate.dict()
    candidate_data["applicationStatus"] = latest_application_status
    candidate_data["interviewStatus"] = latest_interview_status
    
    return CandidateResponse(**candidate_data)

# 🔁 UPDATE candidate
@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    update_data: CandidateCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_db()

    existing_candidate = await db.candidate.find_unique(where={"id": candidate_id})
    if not existing_candidate:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    candidate = await db.candidate.update(
        where={"id": candidate_id},
        data=update_data.dict(exclude_unset=True)
    )

    candidate_data = candidate.dict()
    candidate_data["applicationStatus"] = None
    candidate_data["interviewStatus"] = None

    # Log activity
    await ActivityHelpers.log_candidate_updated(
       user_id=current_user.id,
       candidate_id=candidate.id,
       candidate_name=candidate.name
   )

    return CandidateResponse(**candidate_data)


# ❌ DELETE candidate
@router.delete("/{candidate_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_db()

    existing_candidate = await db.candidate.find_unique(where={"id": candidate_id})
    if not existing_candidate:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    await db.candidate.delete(where={"id": candidate_id})
    
    await ActivityHelpers.log_candidate_deleted(
       user_id=current_user.id,
       candidate_id=candidate_id,
       candidate_name=existing_candidate.name
   )


@router.get("/{candidate_id}/status-summary")
async def get_candidate_status_summary(
    candidate_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get a summary of candidate's application and interview status"""
    db = get_db()
    
    candidate = await db.candidate.find_unique(
        where={"id": candidate_id},
        include={
            "applications": {
                "where": {"userId": current_user.id},  # Only get applications created by current user
                "include": {
                    "job": True,
                    "interviews": True
                }
            }
        }
    )
    
    if not candidate:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    # Calculate statistics
    stats = {
        "candidateId": candidate_id,
        "candidateName": candidate.name,
        "candidateEmail": candidate.email,
        "totalApplications": len(candidate.applications),
        "applicationsByStatus": {
            "APPLIED": 0,
            "SCREENING": 0,
            "INTERVIEW": 0,
            "OFFER": 0,
            "HIRED": 0,
            "REJECTED": 0
        },
        "interviewsByStatus": {
            "SCHEDULED": 0,
            "CONFIRMED": 0,
            "IN_PROGRESS": 0,
            "COMPLETED": 0,
            "CANCELLED": 0,
            "NO_SHOW": 0,
            "RESCHEDULED": 0
        },
        "interviewsByType": {
            "PHONE": 0,
            "VIDEO": 0,
            "IN_PERSON": 0,
            "TECHNICAL": 0,
            "BEHAVIORAL": 0,
            "PANEL": 0
        },
        "averageMatchScore": 0,
        "recentActivity": []
    }
    
    total_match_score = 0
    match_score_count = 0
    
    for app in candidate.applications:
        # Count applications by status
        stats["applicationsByStatus"][app.status] += 1
        
        # Calculate average match score
        if app.matchScore:
            total_match_score += app.matchScore
            match_score_count += 1
        
        # Add to recent activity
        stats["recentActivity"].append({
            "type": "APPLICATION",
            "action": f"Applied for {app.job.title if app.job else 'Unknown Position'}",
            "date": app.appliedAt,
            "status": app.status
        })
        
        # Count interviews
        for interview in app.interviews:
            stats["interviewsByStatus"][interview.status] += 1
            stats["interviewsByType"][interview.type] += 1
            
            # Add to recent activity
            stats["recentActivity"].append({
                "type": "INTERVIEW",
                "action": f"{interview.type} interview for {app.job.title if app.job else 'Unknown Position'}",
                "date": interview.scheduledAt,
                "status": interview.status
            })
    
    # Calculate average match score
    if match_score_count > 0:
        stats["averageMatchScore"] = round(total_match_score / match_score_count, 1)
    
    # Sort recent activity by date (most recent first)
    stats["recentActivity"].sort(key=lambda x: x["date"], reverse=True)
    stats["recentActivity"] = stats["recentActivity"][:10]  # Limit to 10 most recent
    
    return stats

@router.get("/statistics/overview")
async def get_candidates_overview(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get overview statistics for all candidates"""
    db = get_db()
    
    # Get all candidates with their applications and interviews
    candidates = await db.candidate.find_many(
        include={
            "applications": {
                "where": {"userId": current_user.id},  # Only get applications created by current user
                "include": {
                    "interviews": True
                }
            }
        }
    )
    
    stats = {
        "totalCandidates": len(candidates),
        "candidatesWithApplications": 0,
        "candidatesWithInterviews": 0,
        "applicationsByStatus": {
            "APPLIED": 0,
            "SCREENING": 0,
            "INTERVIEW": 0,
            "OFFER": 0,
            "HIRED": 0,
            "REJECTED": 0
        },
        "interviewsByStatus": {
            "SCHEDULED": 0,
            "CONFIRMED": 0,
            "IN_PROGRESS": 0,
            "COMPLETED": 0,
            "CANCELLED": 0,
            "NO_SHOW": 0,
            "RESCHEDULED": 0
        },
        "topSkills": {},
        "averageApplicationsPerCandidate": 0
    }
    
    total_applications = 0
    
    for candidate in candidates:
        # Count candidates with applications
        if candidate.applications:
            stats["candidatesWithApplications"] += 1
            total_applications += len(candidate.applications)
        
        # Check if candidate has interviews
        has_interviews = any(app.interviews for app in candidate.applications)
        if has_interviews:
            stats["candidatesWithInterviews"] += 1
        
        # Count skills
        for skill in candidate.skills:
            stats["topSkills"][skill] = stats["topSkills"].get(skill, 0) + 1
        
        # Count applications and interviews by status
        for app in candidate.applications:
            stats["applicationsByStatus"][app.status] += 1
            
            for interview in app.interviews:
                stats["interviewsByStatus"][interview.status] += 1
    
    # Calculate average applications per candidate
    if stats["candidatesWithApplications"] > 0:
        stats["averageApplicationsPerCandidate"] = round(
            total_applications / stats["candidatesWithApplications"], 1
        )
    
    # Get top 10 skills
    stats["topSkills"] = dict(
        sorted(stats["topSkills"].items(), key=lambda x: x[1], reverse=True)[:10]
    )
    
    return stats
