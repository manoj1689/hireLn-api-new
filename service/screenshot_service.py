import os
from datetime import datetime
from fastapi import UploadFile
from fastapi.staticfiles import StaticFiles


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(BASE_DIR, "..")
SCREENSHOT_DIR = os.path.join(ROOT_DIR, "screenshots")

# Ensure screenshot directory exists
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def mount_screenshot_folder(app):
    """
    Mount /screenshots ONLY ONE TIME when the app starts.
    """
    app.mount(
        "/screenshots",
        StaticFiles(directory=SCREENSHOT_DIR),
        name="screenshots",
    )


async def save_screenshot_file(file: UploadFile, interview_id: str):
    """
    Save screenshot to disk and return paths.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{interview_id}_{timestamp}.jpg"

    file_path = os.path.join(SCREENSHOT_DIR, filename)

    # Save file
    with open(file_path, "wb") as f:
        f.write(await file.read())

    public_url = f"/screenshots/{filename}"

    return {
        "file_path": file_path,
        "url": public_url,
    }
