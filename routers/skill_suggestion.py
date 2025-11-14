from fastapi import APIRouter, HTTPException, status, Depends
from models.schemas import UserResponse
from pydantic import BaseModel
from typing import List, Optional
from database import get_db
from auth.dependencies import get_current_user  # ✅ Import your auth dependency
  # ✅ User schema (adjust import path as per your project)

router = APIRouter()

# ✅ Pydantic Schemas
class SkillSuggestionBase(BaseModel):
    department: str
    suggestions: List[str]

class SkillSuggestionCreate(SkillSuggestionBase):
    pass

class SkillSuggestionUpdate(BaseModel):
    department: Optional[str] = None
    suggestions: Optional[List[str]] = None

class SkillSuggestionResponse(SkillSuggestionBase):
    id: str

    class Config:
        orm_mode = True


# ✅ Get all suggestions (Public)
@router.get("/", response_model=List[SkillSuggestionResponse])
async def get_all_skill_suggestions():
    db = get_db()
    skill_suggestions = await db.skillsuggestion.find_many()
    return skill_suggestions


# ✅ Get a single suggestion by ID (Public)
@router.get("/{suggestion_id}", response_model=SkillSuggestionResponse)
async def get_skill_suggestion(suggestion_id: str):
    db = get_db()
    suggestion = await db.skillsuggestion.find_unique(where={"id": suggestion_id})
    if not suggestion:
        raise HTTPException(status_code=404, detail="Skill suggestion not found")
    return suggestion


# ✅ Create new suggestion (Authenticated)
@router.post(
    "/create",
    response_model=SkillSuggestionResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_skill_suggestion(
    data: SkillSuggestionCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_db()
    new_suggestion = await db.skillsuggestion.create(data=data.dict())
    return new_suggestion


# ✅ Update existing suggestion (Authenticated)
@router.put("/{suggestion_id}", response_model=SkillSuggestionResponse)
async def update_skill_suggestion(
    suggestion_id: str,
    update_data: SkillSuggestionUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_db()
    existing = await db.skillsuggestion.find_unique(where={"id": suggestion_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Skill suggestion not found")

    updated = await db.skillsuggestion.update(
        where={"id": suggestion_id},
        data=update_data.dict(exclude_unset=True)
    )
    return updated


# ✅ Delete suggestion (Authenticated)
@router.delete("/{suggestion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill_suggestion(
    suggestion_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    db = get_db()
    existing = await db.skillsuggestion.find_unique(where={"id": suggestion_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Skill suggestion not found")

    await db.skillsuggestion.delete(where={"id": suggestion_id})
    return {"message": "Skill suggestion deleted successfully"}


@router.delete("/{suggestion_id}/skill/{skill_name}", status_code=status.HTTP_200_OK)
async def delete_skill_from_suggestion(
    suggestion_id: str,
    skill_name: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Delete a single skill from a skill suggestion list.
    Keeps the record, only removes that skill from the suggestions array.
    """
    db= get_db()

    # ✅ Check if record exists
    existing = await db.skillsuggestion.find_unique(where={"id": suggestion_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Skill suggestion not found")

    # ✅ Current skills list
    current_skills = existing.suggestions or []

    # ✅ Check if skill exists in list
    if skill_name not in current_skills:
        raise HTTPException(status_code=404, detail="Skill not found in suggestions")

    # ✅ Remove the skill
    updated_skills = [s for s in current_skills if s != skill_name]

    # ✅ Update record
    await db.skillsuggestion.update(
        where={"id": suggestion_id},
        data={"suggestions": updated_skills},
    )

    return {
        "message": f"Skill '{skill_name}' removed successfully",
        "updated_suggestions": updated_skills,
    }