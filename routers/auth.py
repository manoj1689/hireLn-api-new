from uuid import uuid4
from fastapi import APIRouter, HTTPException, status, Depends, Body
from datetime import timedelta, datetime, timezone
from fastapi.responses import JSONResponse
from firebase_admin import auth as firebase_auth
from auth.dependencies import get_current_user
from auth.jwt_handler import create_access_token
from database import get_db
from models.schemas import (
   GuestRequest, TokenResponse, UserRequest, UserResponse
)
from service.activity_service import ActivityHelpers
from service.notification_service import FCMService


router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login_user(user_req: UserRequest):
    db = get_db()  # Prisma DB connection

    try:
        # ---------------- Verify Firebase token ----------------
        decoded_token = firebase_auth.verify_id_token(user_req.token)
        googleId = decoded_token.get("uid")
        email = decoded_token.get("email") or user_req.email
        name = decoded_token.get("name") or user_req.name or "User"
        picture = decoded_token.get("picture") or user_req.avatar

        if not email:
            raise HTTPException(status_code=400, detail="Token is invalid or missing email")

        # ---------------- Role from request ----------------
        if not user_req.role:
            raise HTTPException(status_code=400, detail="Role is required in request")
        role = user_req.role.upper()  # Must be RECRUITER or GUEST

        # ---------------- Check if user exists ----------------
        user = await db.user.find_unique(where={"email": email})

        # ---------------- Email-role collision check ----------------
        if user:
            stored_role = str(user.role).upper()  # normalize
            if stored_role != role:
                print(f"🚫 Role mismatch: stored={stored_role}, requested={role}")
                raise HTTPException(
                    status_code=400,
                    detail=f"User with email {user.email} already exists as {stored_role}. Cannot login as {user.role}."
                )

        # ---------------- First-time login → create user ----------------
        if not user:
            user_data = {
                "email": email,
                "name": name.strip(),
                "avatar": picture,
                "role": role,
                "googleId": googleId or f"{role.lower()}_{uuid4()}",
                "accountType": user_req.accountType,
                "subscriptionActive": user_req.subscriptionActive or False,
                "trialEndsAt": user_req.trialEndsAt,
                "fcm_token": user_req.fcm_token or "",
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
            }
            user = await db.user.create(data=user_data)

        # ---------------- Update FCM token ----------------
        if user_req.fcm_token:
            await db.user.update(where={"id": user.id}, data={"fcm_token": user_req.fcm_token})
            user.fcm_token = user_req.fcm_token

        # ---------------- Send FCM notification ----------------
        if user.fcm_token:
            title = "Welcome Guest 👋" if role == "GUEST" else "Login Successful 🔑"
            body = f"Hello {user.name}!" if role == "GUEST" else f"Welcome back, {user.name}!"
            await FCMService.send_notification(
                fcm_token=user.fcm_token,
                title=title,
                body=body,
                data={"type": "login", "screen": "dashboard"},
            )

        # ---------------- Generate JWT ----------------
        token_expiry = timedelta(hours=12) if role == "GUEST" else None
        access_token = create_access_token(data={"sub": user.id}, expires_delta=token_expiry)

             
        # ---------------- Prepare response ----------------
        user_resp = UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar=user.avatar,
            role=user.role,
            planType=user.accountType,
            subscriptionActive=user.subscriptionActive,
            trialEndsAt=user.trialEndsAt,
            isTrialActive=user.subscriptionActive and (user.trialEndsAt is None or user.trialEndsAt > datetime.utcnow()),
            registered=user.registered,  # ✅ Based on company data
            fcm_token=user.fcm_token,
            createdAt=user.createdAt,
            updatedAt=user.updatedAt
        )

        return TokenResponse(access_token=access_token, token_type="bearer", user=user_resp)

    
    except HTTPException as he:
        # ✅ Return clean JSON manually
        return JSONResponse(
            status_code=he.status_code,
            content={"success": False, "detail": he.detail},
        )

    except Exception as e:
        import traceback
        print("🔥 Unexpected login error:", traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "detail": f"Unexpected login error: {str(e)}",
            },
        )
@router.post("/guest-login", response_model=TokenResponse)
async def guest_login(user_req: GuestRequest):
    db = get_db()

    try:
        # ---------------- Validate role ----------------
        if not user_req.role:
            raise HTTPException(status_code=400, detail="Role is required in request")
        role = user_req.role.upper()
        if role != "GUEST":
            raise HTTPException(status_code=400, detail="Only GUEST role is allowed here")

        # ---------------- Generate guest identity ----------------
        guest_email = f"guest_{uuid4().hex[:10]}@example.com"
        guest_name =  "Guest User"
        google_id = f"guest_{uuid4()}"

        # ---------------- Create guest user ----------------
        user_data = {
            "email": guest_email,
            "name": guest_name,
            "avatar": "https://cdn-icons-png.flaticon.com/512/149/149071.png",
            "role": "GUEST",
            "googleId": google_id,
            "accountType": user_req.accountType,
            "subscriptionActive": user_req.subscriptionActive or False,
            "trialEndsAt": user_req.trialEndsAt,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }

        user = await db.user.create(data=user_data)

        # ---------------- Generate JWT ----------------
        token_expiry = timedelta(hours=12)
        access_token = create_access_token(data={"sub": user.id}, expires_delta=token_expiry)

        # ---------------- Prepare response ----------------
        user_resp = UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar=user.avatar,
            role=user.role,
            planType=user.accountType,
            subscriptionActive=user.subscriptionActive,
            trialEndsAt=user.trialEndsAt,
            isTrialActive=user.subscriptionActive and (user.trialEndsAt is None or user.trialEndsAt > datetime.utcnow()),
            registered=False,
            fcm_token=None,
            createdAt=user.createdAt,
            updatedAt=user.updatedAt,
        )

        return TokenResponse(access_token=access_token, token_type="bearer", user=user_resp)

    except HTTPException as he:
        return JSONResponse(
            status_code=he.status_code,
            content={"success": False, "detail": he.detail},
        )
    except Exception as e:
        import traceback
        print("🔥 Unexpected guest login error:", traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "detail": f"Unexpected guest login error: {str(e)}",
            },
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """Return current user (Recruiter or Guest)"""
    return current_user


@router.get("/trial-status")
async def get_trial_status(current_user: UserResponse = Depends(get_current_user)):
    """
    Return current user's trial/subscription status.
    Guests will always return inactive trial & subscription.
    """
    db = get_db()

    # If guest
    if current_user.role == "guest":
        return {
            "isTrialActive": False,
            "trialEndsAt": None,
            "daysRemaining": 0,
            "subscriptionActive": False,
            "planType": "none"
        }

    # Recruiter
    user = await db.user.find_unique(where={"id": current_user.id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    days_remaining = 0
    if user.trialEndsAt and user.isTrialActive:
        days_remaining = max(0, (user.trialEndsAt - datetime.utcnow()).days)

    return {
        "isTrialActive": user.isTrialActive,
        "trialEndsAt": user.trialEndsAt,
        "daysRemaining": days_remaining,
        "subscriptionActive": user.subscriptionActive,
        "planType": user.planType,
    }

