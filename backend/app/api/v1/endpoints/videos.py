from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List
import uuid

from app.schemas.video import VideoRequest, VideoResponse, VideoStatus
from app.services.video_service import VideoService
from pipeline.orchestrator import VideoGenerationOrchestrator

router = APIRouter()


async def get_video_service() -> VideoService:
    return VideoService()


async def get_orchestrator() -> VideoGenerationOrchestrator:
    return VideoGenerationOrchestrator()


@router.post("/generate", response_model=dict)
async def generate_video(
        request: VideoRequest,
        background_tasks: BackgroundTasks,
        video_service: VideoService = Depends(get_video_service),
        orchestrator: VideoGenerationOrchestrator = Depends(get_orchestrator)
):
    """
    Generate educational video from concept query
    """
    try:
        # Create task ID
        task_id = str(uuid.uuid4())

        # Queue video generation task
        background_tasks.add_task(
            orchestrator.generate_video_async,
            task_id,
            request.concept_name,
            request.domain,
            request.difficulty_level
        )

        # Create task record
        await video_service.create_task_record(task_id, request)

        return {
            "task_id": task_id,
            "status": "queued",
            "message": "Video generation started"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
        video_id: str,
        video_service: VideoService = Depends(get_video_service)
):
    """
    Get video details by ID
    """
    video = await video_service.get_video_by_id(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.get("/", response_model=List[VideoResponse])
async def list_videos(
        domain: str = None,
        limit: int = 20,
        offset: int = 0,
        video_service: VideoService = Depends(get_video_service)
):
    """
    List videos with optional filtering
    """
    videos = await video_service.list_videos(
        domain=domain,
        limit=limit,
        offset=offset
    )
    return videos


@router.delete("/{video_id}")
async def delete_video(
        video_id: str,
        video_service: VideoService = Depends(get_video_service)
):
    """
    Delete a video
    """
    success = await video_service.delete_video(video_id)
    if not success:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"message": "Video deleted successfully"}