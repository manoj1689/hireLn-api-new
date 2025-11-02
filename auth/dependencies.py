from fastapi import Depends, HTTPException, status, Query, Header
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from typing import Optional, Union
from datetime import datetime, timezone
import logging
import json
import re
from pydantic import ValidationError

from auth.jwt_handler import verify_token
from database import get_db
from models.schemas import UserResponse
from prisma import Prisma

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth2 for user login - make it optional for mixed auth scenarios
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = verify_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = get_db()

   
    # Regular user
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise credentials_exception
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,        # Only name
        avatar=user.avatar,
        role=user.role,
        planType=user.accountType,
        subscriptionActive=user.subscriptionActive,
        trialEndsAt=user.trialEndsAt,
        isTrialActive=user.subscriptionActive and (user.trialEndsAt is None or user.trialEndsAt > datetime.utcnow()),
        registered=user.registered,
        fcm_token=user.fcm_token,
        createdAt=user.createdAt,
        updatedAt=user.updatedAt
    )

# ✅ Optional: Require admin users
async def get_admin_user(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user




# ✅ Verify interview or application token
async def verify_interview_token(token: str) -> dict:
    """Verify interview or application token and return associated data"""
    db = get_db()
    
    # Step 1️⃣ — Try to find interview by joinToken
    interview = await db.interview.find_first(
        where={"joinToken": token},
        include={
            "candidate": True,
            "application": {
                "include": {
                    "job": True,
                    "user": True
                }
            }
        }
    )

    # Step 2️⃣ — If not found in interview, check in application
    if not interview:
        application = await db.application.find_first(
            where={"joinToken": token},
            include={
                "candidate": True,
                "job": True,
                "user": True
            }
        )

        if not application:
            raise HTTPException(status_code=401, detail="Invalid interview token")

        # Step 3️⃣ — Check token expiry for application
        if application.tokenExpiry:
            current_time = datetime.now(timezone.utc)
            token_expiry = application.tokenExpiry
            if token_expiry.tzinfo is None:
                token_expiry = token_expiry.replace(tzinfo=timezone.utc)
            if current_time > token_expiry:
                raise HTTPException(status_code=401, detail="Application token has expired")

        # ✅ Return Application token details
        return {
            "source": "application",
            "candidate": application.candidate,
            "job": application.job,
            "recruiter": application.user,
        }

    # Step 4️⃣ — Check token expiry for interview
    if interview.tokenExpiry:
        current_time = datetime.now(timezone.utc)
        token_expiry = interview.tokenExpiry
        if token_expiry.tzinfo is None:
            token_expiry = token_expiry.replace(tzinfo=timezone.utc)
        if current_time > token_expiry:
            raise HTTPException(status_code=401, detail="Interview token has expired")

    # ✅ Return Interview token details
    return {
        "source": "interview",
        "interview": interview,
        "candidate": interview.candidate,
        "job": interview.application.job,
        "recruiter": interview.application.user
    }

# ✅ Combined user OR interview token auth - token only
async def get_user_or_interview_auth(
    user_token: Optional[str] = Depends(oauth2_scheme),
    interview_token: Optional[str] = Header(None, alias="X-Interview-Token"),
) -> Union[UserResponse, dict]:
    """
    Authenticate using either:
    1. Authorization: Bearer <jwt_token> header
    2. X-Interview-Token: <interview_token> header
    """
    print("interview_Token",interview_token)
    # Priority 1: Interview token auth
    if interview_token:
        try:
            logger.info("🔐 Attempting interview token auth")
            result = await verify_interview_token(interview_token)
            logger.info("✅ Interview token verified")
            return result
        except HTTPException as e:
            logger.warning(f"❌ Interview token failed: {e.detail}")
            # Don't raise here, try user token next

    # Priority 2: User token auth
    if user_token:
        try:
            logger.info("🔐 Attempting user token auth")
            result = await get_current_user(user_token)
            logger.info("✅ User token verified")
            return result
        except HTTPException as e:
            logger.warning(f"❌ User token failed: {e.detail}")

    logger.error("❌ No valid token provided")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either Authorization Bearer token or X-Interview-Token header.",
        headers={"WWW-Authenticate": "Bearer"},
    )

# ✅ Interview token only auth
async def get_interview_auth_only(
    interview_token: str = Header(..., alias="X-Interview-Token")
) -> dict:
    """Validate interview token only - for public interview access"""
    try:
        logger.info("🔐 Validating interview token")
        result = await verify_interview_token(interview_token)
        logger.info("✅ Interview token verified")
        return result
    except HTTPException as e:
        logger.error(f"❌ Interview token validation failed: {e.detail}")
        raise e


async def get_current_user_optional() -> Optional[UserResponse]:
    try:
        return await get_current_user()
    except:
        return None