import json
from typing import Optional, Tuple
from models.schemas import CandidateCreate, UserResponse
from service.activity_service import ActivityHelpers


async def create_candidate_from_parsed_data(
    candidate_data: CandidateCreate,
    current_user: UserResponse,
    db,
    resume_id: str,
    resume_name: str
) -> Tuple[bool, str, Optional[dict]]:
    try:
        existing_candidate = await db.candidate.find_unique(where={"email": candidate_data.email})
        if existing_candidate:
            return False, f"Candidate with email {candidate_data.email} already exists", None
        
        candidate_dict = candidate_data.model_dump()
        json_fields = [
            "education",
            "experience",
            "certifications",
            "projects",
            "previousJobs",
            "personalInfo",
            "languages"
        ]
        for key in json_fields:
            if key in candidate_dict and candidate_dict[key] is not None:
                candidate_dict[key] = json.dumps(candidate_dict[key])

        # ✅ Create new candidate
        candidate = await db.candidate.create(
            data={
                **candidate_dict,
                "userId": current_user.id,
                "resumeId": resume_id,
                "resumeName": resume_name
            }
        )

        # Log activity
        await ActivityHelpers.log_candidate_added(
            user_id=current_user.id,
            candidate_id=candidate.id,
            candidate_name=candidate.name
        )

        # ✅ Return the candidate info for frontend Redux
        return True, f"Candidate '{candidate.name}' created successfully", {
            "user_id": current_user.id,
            "candidate_id": candidate.id,
            "candidate_name": candidate.name,
            "email": candidate.email,
            "resume_id": resume_id,
            "resume_name": resume_name
        }

    except Exception as e:
        return False, f"Failed to create candidate: {str(e)}", None
