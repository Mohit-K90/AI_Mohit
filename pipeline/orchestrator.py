import asyncio
import logging
from typing import Dict, Any
from dataclasses import dataclass

from pipeline.knowledge_graph.graph_service import GraphService
from pipeline.ai_services.content_generator import ContentGenerator
from pipeline.animation.manim_engine import ManimEngine
from pipeline.storage.s3_client import S3Client
from pipeline.storage.postgres_client import PostgresClient
from pipeline.storage.cache_service import CacheService


@dataclass
class GenerationRequest:
    task_id: str
    concept_name: str
    domain: str
    difficulty_level: str


class VideoGenerationOrchestrator:
    def __init__(self):
        self.graph_service = GraphService()
        self.content_generator = ContentGenerator()
        self.manim_engine = ManimEngine()
        self.s3_client = S3Client()
        self.postgres_client = PostgresClient()
        self.cache_service = CacheService()
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize all services"""
        await asyncio.gather(
            self.graph_service.initialize(),
            self.content_generator.initialize(),
            self.manim_engine.initialize(),
            self.s3_client.initialize(),
            self.postgres_client.initialize(),
            self.cache_service.initialize()
        )
        self.logger.info("Pipeline orchestrator initialized")

    async def generate_video_async(self, task_id: str, concept_name: str, domain: str, difficulty_level: str):
        """
        Main async video generation pipeline
        """
        request = GenerationRequest(task_id, concept_name, domain, difficulty_level)

        try:
            # Update status: Starting
            await self._update_task_status(task_id, "processing", 0, "Starting video generation")

            # Step 1: Knowledge Retrieval (20% progress)
            concept_data = await self._retrieve_concept_knowledge(request)
            await self._update_task_status(task_id, "processing", 20, "Retrieved concept knowledge")

            # Step 2: Content Generation (40% progress)
            slides, script = await self._generate_educational_content(concept_data, request)
            await self._update_task_status(task_id, "processing", 40, "Generated slides and script")

            # Step 3: Animation Creation (80% progress)
            video_path = await self._create_video_animation(slides, script, request)
            await self._update_task_status(task_id, "processing", 80, "Created video animation")

            # Step 4: Storage and Finalization (100% progress)
            video_url = await self._store_and_finalize(video_path, request)
            await self._update_task_status(task_id, "completed", 100, "Video generation completed", video_url)

            self.logger.info(f"Video generation completed for task {task_id}")

        except Exception as e:
            await self._update_task_status(task_id, "failed", -1, f"Error: {str(e)}")
            self.logger.error(f"Video generation failed for task {task_id}: {str(e)}")
            raise

    async def _retrieve_concept_knowledge(self, request: GenerationRequest) -> Dict[str, Any]:
        """Retrieve concept and related knowledge from graph database"""
        cache_key = f"concept_knowledge:{request.concept_name}:{request.domain}"

        # Check cache first
        cached_data = await self.cache_service.get(cache_key)
        if cached_data:
            return cached_data

        # Query knowledge graph
        concept_data = await self.graph_service.get_concept_with_context(
            concept_name=request.concept_name,
            domain=request.domain,
            depth=2
        )

        # Cache the result
        await self.cache_service.set(cache_key, concept_data, ttl=3600)

        return concept_data

    async def _generate_educational_content(self, concept_data: Dict[str, Any], request: GenerationRequest):
        """Generate slides and script using AI"""
        content = await self.content_generator.generate_educational_content(
            concept_data=concept_data,
            difficulty_level=request.difficulty_level,
            domain=request.domain
        )
        return content['slides'], content['script']

    async def _create_video_animation(self, slides, script, request: GenerationRequest) -> str:
        """Create animated video using Manim"""
        video_path = await self.manim_engine.generate_video(
            slides=slides,
            script=script,
            task_id=request.task_id
        )
        return video_path

    async def _store_and_finalize(self, video_path: str, request: GenerationRequest) -> str:
        """Store video and create database records"""
        # Upload to S3
        s3_url = await self.s3_client.upload_video(
            file_path=video_path,
            key=f"videos/{request.task_id}/output.mp4"
        )

        # Create database record
        video_record = {
            "id": request.task_id,
            "concept_name": request.concept_name,
            "domain": request.domain,
            "difficulty_level": request.difficulty_level,
            "s3_url": s3_url,
            "status": "completed"
        }

        await self.postgres_client.insert("videos", video_record)

        return s3_url

    async def _update_task_status(self, task_id: str, status: str, progress: int, message: str, video_url: str = None):
        """Update task status in database and notify via WebSocket"""
        task_update = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "message": message,
            "video_url": video_url,
            "updated_at": "now()"
        }

        # Update database
        await self.postgres_client.update("generation_tasks", task_update, f"id = '{task_id}'")

        # Notify via WebSocket (would need WebSocket manager reference)
        # await websocket_manager.send_update(task_id, task_update)
