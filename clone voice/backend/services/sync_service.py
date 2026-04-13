"""
Sync.so Service — AI lip sync video generation.
Takes a face image + audio and produces a talking-head video.
"""

import os
import uuid
import time
import httpx
from config import SYNC_API_KEY, UPLOAD_DIR


SYNC_API_BASE = "https://api.sync.so/v2"

HEADERS = {
    "x-api-key": SYNC_API_KEY,
    "Content-Type": "application/json",
}


async def generate_lipsync(image_path: str, audio_path: str, model: str = "lipsync-2") -> dict:
    """
    Submit a lip sync generation job.
    Returns job info with ID for status polling.
    """
    # Upload files and get URLs — Sync.so needs publicly accessible URLs
    # For local dev, we'll upload the files directly via multipart
    async with httpx.AsyncClient(timeout=120) as client:
        # First, upload the image and audio to get asset IDs
        # Using the direct upload approach
        with open(image_path, "rb") as img_file, open(audio_path, "rb") as aud_file:
            response = await client.post(
                f"{SYNC_API_BASE}/generate",
                headers={"x-api-key": SYNC_API_KEY},
                data={
                    "model": model,
                    "input": '[{"type": "video", "path": "image"}, {"type": "audio", "path": "audio"}]',
                },
                files={
                    "image": (os.path.basename(image_path), img_file, "image/jpeg"),
                    "audio": (os.path.basename(audio_path), aud_file, "audio/mpeg"),
                },
            )

    if response.status_code not in (200, 201, 202):
        raise Exception(f"Sync.so API error: {response.status_code} - {response.text}")

    result = response.json()
    print(f"👄 Lip sync job submitted: {result.get('id', 'unknown')}")
    return result


async def generate_lipsync_with_urls(image_url: str, audio_url: str, model: str = "lipsync-2") -> dict:
    """
    Submit a lip sync job using publicly accessible URLs.
    This is the preferred method if files are hosted somewhere.
    """
    payload = {
        "model": model,
        "input": [
            {"type": "video", "url": image_url},
            {"type": "audio", "url": audio_url},
        ],
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{SYNC_API_BASE}/generate",
            headers=HEADERS,
            json=payload,
        )

    if response.status_code not in (200, 201, 202):
        raise Exception(f"Sync.so API error: {response.status_code} - {response.text}")

    return response.json()


async def check_status(job_id: str) -> dict:
    """Check the status of a lip sync generation job."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{SYNC_API_BASE}/generate/{job_id}",
            headers=HEADERS,
        )

    if response.status_code != 200:
        raise Exception(f"Status check failed: {response.status_code} - {response.text}")

    return response.json()


async def wait_for_completion(job_id: str, max_wait: int = 180, poll_interval: int = 5) -> dict:
    """
    Poll for job completion.
    Returns the completed job data with video URL.
    """
    elapsed = 0
    while elapsed < max_wait:
        status = await check_status(job_id)
        state = status.get("status", "").lower()

        if state == "completed":
            print(f"✅ Lip sync completed! Video URL: {status.get('outputUrl', 'N/A')}")
            return status
        elif state in ("failed", "error"):
            raise Exception(f"Lip sync job failed: {status.get('error', 'Unknown error')}")

        print(f"⏳ Lip sync status: {state} ({elapsed}s elapsed)")
        time.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(f"Lip sync job timed out after {max_wait}s")


async def download_video(video_url: str) -> str:
    """Download the generated video to local storage."""
    output_path = os.path.join(UPLOAD_DIR, f"lipsync_{uuid.uuid4().hex[:12]}.mp4")

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(video_url)

    with open(output_path, "wb") as f:
        f.write(response.content)

    print(f"🎬 Video downloaded: {output_path}")
    return output_path
