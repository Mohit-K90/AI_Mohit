from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
from contextlib import asynccontextmanager

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from pipeline.orchestrator import VideoGenerationOrchestrator

# Lifespan manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting AI Education Platform...")
    app.state.orchestrator = VideoGenerationOrchestrator()
    await app.state.orchestrator.initialize()
    yield
    # Shutdown
    print("🛑 Shutting down AI Education Platform...")
    await app.state.orchestrator.cleanup()

# FastAPI app initialization
app = FastAPI(
    title="AI-Powered Educational Video Generator",
    description="Generate educational videos from knowledge graphs using AI and Manim",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Setup exception handlers
setup_exception_handlers(app)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]

    async def send_update(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            try:
                await self.active_connections[task_id].send_json(message)
            except:
                self.disconnect(task_id)

manager = ConnectionManager()

# WebSocket endpoint for real-time updates
@app.websocket("/ws/tasks/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(websocket, task_id)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(task_id)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)