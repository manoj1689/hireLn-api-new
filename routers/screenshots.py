from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status,Request
from typing import Union
from prisma import Prisma

from database import get_db
from auth.dependencies import get_current_user, get_user_or_interview_auth
from service.screenshot_service import save_screenshot_file

from models.schemas import (
    ScreenshotSaveResponse,
    ScreenshotUploadRequest,
    ScreenshotDeleteResponse,
    ScreenshotListResponse,
    ScreenshotResponse,
    UserResponse,
)

router = APIRouter()

def build_url(request: Request, relative_path: str) -> str:
    return f"{request.base_url}{relative_path.lstrip('/')}"


# ============================================================
# 1️⃣ UPLOAD SCREENSHOT
# ============================================================
@router.post(
    "/upload",
    summary="Save automated exam screenshot",
    response_model=ScreenshotSaveResponse,
)
async def upload_screenshot(
    interview_id: str,
    faceVerified: bool | None = None,
    multiFace: bool | None = None,
    note: str | None = None,
    file: UploadFile = File(...),
    db: Prisma = Depends(get_db),
     auth_data: Union[UserResponse, dict] = Depends(get_user_or_interview_auth),
):
    """
    Upload screenshot + face verification flags.
    """
    
    # ---------------------------
    # 🔒 Access Restriction
    # ---------------------------
    where_clause = {"id": interview_id}

    if isinstance(auth_data, UserResponse):
        where_clause["scheduledById"] = auth_data.id

    elif isinstance(auth_data, dict):
        allowed = auth_data.get("interviewId")
        if allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to upload screenshots for this interview",
            )

    # ---------------------------
    # 📸 Save file
    # ---------------------------
    image_url = await save_screenshot_file(file, interview_id)
    print("image url",image_url)
    # ---------------------------
    # 🗄️ Save DB record
    # ---------------------------
    record = await db.interviewscreenshot.create(
        data={
            "interviewId": interview_id,
            "imageUrl": image_url["url"],
            "faceVerified": faceVerified,
            "multiFace": multiFace,
            "note": note,
        }
    )

    return ScreenshotSaveResponse(
        success=True,
        screenshot=ScreenshotResponse.from_orm(record)
    )


# ============================================================
# 2️⃣ LIST SCREENSHOTS
# ============================================================
@router.get(
    "/{interview_id}/list",
    summary="List screenshots for an interview",
    response_model=ScreenshotListResponse,
)
async def list_screenshots(
    interview_id: str,
    request: Request,
    db: Prisma = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):

    interview = await db.interview.find_unique(where={"id": interview_id})
    if not interview:
        raise HTTPException(404, "Interview not found")

    if interview.scheduledById != current_user.id:
        raise HTTPException(403, "Not allowed to view screenshots")

    # Fetch raw DB models
    screenshots = await db.interviewscreenshot.find_many(
        where={"interviewId": interview_id},
        order={"capturedAt": "desc"},
    )

    # Convert each DB record → ScreenshotResponse
    response_items = []
    for s in screenshots:
        response_items.append(
            ScreenshotResponse(
                id=s.id,
                interviewId=s.interviewId,
                imageUrl=build_url(request, s.imageUrl),   # ⭐ FULL URL HERE
                faceVerified=s.faceVerified,
                multiFace=s.multiFace,
                note=s.note,
                capturedAt=s.capturedAt,
            )
        )

    return ScreenshotListResponse(
        count=len(response_items),
        screenshots=response_items,
    )


# ============================================================
# 3️⃣ GET SINGLE SCREENSHOT
# ============================================================
@router.get(
    "/view/{id}",
    summary="Get single screenshot details",
    response_model=ScreenshotResponse,
)
async def get_screenshot(
    id: str,
    request: Request,
    db: Prisma = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):

    record = await db.interviewscreenshot.find_unique(where={"id": id})
    if not record:
        raise HTTPException(404, "Screenshot not found")

    interview = await db.interview.find_unique(where={"id": record.interviewId})
    if not interview:
        raise HTTPException(404, "Interview not found")

    if interview.scheduledById != current_user.id:
        raise HTTPException(403, "Not allowed")

    return ScreenshotResponse(
        id=record.id,
        interviewId=record.interviewId,
        imageUrl=build_url(request, record.imageUrl),    # ⭐ FULL PUBLIC URL
        faceVerified=record.faceVerified,
        multiFace=record.multiFace,
        note=record.note,
        capturedAt=record.capturedAt,
    )


# ============================================================
# 4️⃣ DELETE SCREENSHOT
# ============================================================
@router.delete(
    "/delete/{id}",
    summary="Delete a screenshot",
    response_model=ScreenshotDeleteResponse,
)
async def delete_screenshot(
    id: str,
    db: Prisma = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Recruiter-only screenshot deletion.
    """

    record = await db.interviewscreenshot.find_unique(where={"id": id})
    if not record:
        raise HTTPException(404, "Screenshot not found")

    interview = await db.interview.find_unique(where={"id": record.interviewId})
    if not interview:
        raise HTTPException(404, "Interview not found")

    if interview.scheduledById != current_user.id:
        raise HTTPException(403, "Not allowed")

    # Delete
    await db.interviewscreenshot.delete(where={"id": id})

    return ScreenshotDeleteResponse(success=True, deletedId=id)
