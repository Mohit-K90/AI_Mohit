from fastapi import APIRouter, Depends, HTTPException
from app.services.task_service import TaskService
from app.schemas.task import TaskStatus

router = APIRouter()

async def get_task_service() -> TaskService:
    return TaskService()

@router.get("/{task_id}/status", response_model=TaskStatus)
async def get_task_status(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Get task status and progress
    """
    status = await task_service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status

@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Cancel a running task
    """
    success = await task_service.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
    return {"message": "Task cancelled successfully"}
