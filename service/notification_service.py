# service/notification_service.py
from firebase_admin import messaging
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class FCMService:
    @staticmethod
    async def send_notification(
        fcm_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None
    ) -> bool:
        """
        Sends a push notification to a single FCM token.
        Returns True if success, False otherwise.
        """

        if not fcm_token:
            logger.warning("❌ Missing FCM token; skipping notification.")
            return False

        try:
            # Build the message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                    image=image_url
                ),
                token=fcm_token,
                data={str(k): str(v) for k, v in (data or {}).items()},
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        click_action="FLUTTER_NOTIFICATION_CLICK"
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default")
                    )
                ),
            )

            # Send notification
            response = messaging.send(message)
            logger.info(f"✅ Notification sent successfully: {response}")
            return True

        except messaging.UnregisteredError:
            logger.error(f"⚠️ Invalid or expired FCM token: {fcm_token}")
            return False
        except Exception as e:
            logger.error(f"🔥 FCM send error: {str(e)}")
            return False


async def notify_user_login(user_email: str, fcm_token: str):
    await FCMService.send_notification(
        fcm_token=fcm_token,
        title="Welcome back 👋",
        body=f"{user_email}, you’ve logged in successfully!",
        data={"screen": "dashboard", "type": "login_success"}
    )

async def notify_all_users(db):
    users = await db.user.find_many(where={"fcm_token": {"not": None}})
    for user in users:
        await FCMService.send_notification(
            fcm_token=user.fcm_token,
            title="New Feature 🎉",
            body="Explore our new AI interview evaluator now!",
            data={"action": "open_features"}
        )