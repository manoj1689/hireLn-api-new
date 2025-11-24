import os
import asyncio
from datetime import datetime, timedelta
from prisma import Prisma

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
SCREENSHOT_DIR = os.path.join(ROOT_DIR, "screenshots")

# Ensure screenshot directory exists
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def delete_old_screenshots():
    db = Prisma()
    await db.connect()

    cutoff = datetime.utcnow() - timedelta(hours=24)

    old_records = await db.interviewscreenshot.find_many(
        where={"capturedAt": {"lte": cutoff}}
    )

    for rec in old_records:
        # Extract ONLY the filename
        # turns "/screenshots/abc.jpg" --> "abc.jpg"
        filename = rec.imageUrl.split("/")[-1]

        # Absolute local file path
        file_path = os.path.join(SCREENSHOT_DIR, filename)

        # 🗑️ Delete physical file
        if os.path.isfile(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ Deleted file: {file_path}")
            except Exception as e:
                print(f"⚠️ Failed to delete file {file_path}: {e}")
        else:
            print(f"⚠️ File not found: {file_path}")

        # 🗑️ Delete DB row
        try:
            await db.interviewscreenshot.delete(where={"id": rec.id})
            print(f"🗑️ Deleted DB record: {rec.id}")
        except Exception as e:
            print(f"⚠️ Failed to delete DB record {rec.id}: {e}")

    await db.disconnect()
