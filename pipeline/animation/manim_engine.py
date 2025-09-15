import os
import asyncio
import uuid
import tempfile
from typing import List, Dict, Any
import subprocess
import shutil


class ManimEngine:
    def __init__(self):
        self.output_dir = "/tmp/manim_outputs"
        self.quality = "high_quality"
        self.scene_templates = {}

    async def initialize(self):
        """Initialize Manim engine"""
        os.makedirs(self.output_dir, exist_ok=True)
        self._load_scene_templates()

    def _load_scene_templates(self):
        """Load predefined Manim scene templates"""
        self.scene_templates = {
            "intro": self._generate_intro_scene,
            "text": self._generate_text_scene,
            "code": self._generate_code_scene,
            "math": self._generate_math_scene,
            "diagram": self._generate_diagram_scene,
            "conclusion": self._generate_conclusion_scene
        }

    async def generate_video(self, slides: List[Dict], script: List[Dict], task_id: str) -> str:
        """
        Generate complete educational video from slides and script
        """
        scene_files = []
        temp_dir = os.path.join(self.output_dir, task_id)
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # Generate individual scenes
            for i, slide in enumerate(slides):
                scene_file = await self._create_scene(slide, script[i], i, temp_dir)
                scene_files.append(scene_file)

            # Combine all scenes into final video
            final_video = await self._combine_scenes(scene_files, temp_dir)

            return final_video

        except Exception as e:
            # Cleanup on error
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            raise Exception(f"Video generation failed: {str(e)}")

    async def _create_scene(self, slide: Dict, script: Dict, scene_number: int, temp_dir: str) -> str:
        """Create individual Manim scene"""
        scene_type = self._determine_scene_type(slide)
        scene_code = self._generate_scene_code(slide, script, scene_number, scene_type)

        # Write scene code to file
        scene_file = os.path.join(temp_dir, f"scene_{scene_number}.py")
        with open(scene_file, 'w') as f:
            f.write(scene_code)

        # Render scene
        output_file = await self._render_scene(scene_file, scene_number, temp_dir)
        return output_file

    def _determine_scene_type(self, slide: Dict) -> str:
        """Determine appropriate scene type based on slide content"""
        title = slide.get("title", "").lower()
        content = " ".join(slide.get("content", [])).lower()

        if slide.get("code_example") or "code" in content or "algorithm" in content:
            return "code"
        elif "formula" in content or "equation" in content or "theorem" in content:
            return "math"
        elif slide.get("slide_number") == 1:
            return "intro"
        elif slide.get("slide_number") >= 8:  # Assuming last slides are conclusions
            return "conclusion"
        elif "diagram" in content or "graph" in content or "tree" in content:
            return "diagram"
        else:
            return "text"

    def _generate_scene_code(self, slide: Dict, script: Dict, scene_number: int, scene_type: str) -> str:
        """Generate Manim Python code for the scene"""
        base_code = f'''
from manim import *
import numpy as np

class EducationalScene{scene_number}(Scene):
    def construct(self):
        # Scene configuration
        self.camera.background_color = WHITE

        # Title
        title = Text("{slide['title']}", 
                    font_size=48, 
                    color=BLUE_D, 
                    font="Arial Bold")
        title.to_edge(UP, buff=0.5)

        # Content based on scene type
        {self._generate_content_code(slide, script, scene_type)}

        # Animations
        self.play(FadeIn(title, shift=DOWN))
        self.wait(0.5)

        {self._generate_animation_code(slide, scene_type)}

        # Hold final frame
        self.wait(2)
'''
        return base_code

    def _generate_content_code(self, slide: Dict, script: Dict, scene_type: str) -> str:
        """Generate content-specific Manim code"""
        content = slide.get("content", [])

        if scene_type == "text":
            return f'''
        # Text content
        content_items = VGroup()
        content_texts = {content}

        for i, text in enumerate(content_texts):
            item = Text(f"• {{text}}", 
                       font_size=32, 
                       color=BLACK,
                       font="Arial")
            content_items.add(item)

        content_items.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        content_items.next_to(title, DOWN, buff=1)
        content_items.to_edge(LEFT, buff=1)
'''

        elif scene_type == "code":
            code_example = slide.get("code_example", "# Sample code")
            return f'''
        # Code content
        code_block = Code(
            code="""
{code_example}
            """,
            tab_width=4,
            background="window",
            language="python",
            font="Monospace",
            font_size=24
        )
        code_block.next_to(title, DOWN, buff=1)

        # Explanation text
        explanation = Text("Key Implementation Details:",
                          font_size=28,
                          color=BLUE_D)
        explanation.next_to(code_block, DOWN, buff=0.5)
'''

        elif scene_type == "math":
            return f'''
        # Mathematical content
        formula = MathTex(
            r"\\text{{Mathematical Concept}}",
            font_size=36,
            color=BLACK
        )
        formula.next_to(title, DOWN, buff=1)

        explanation = VGroup()
        for item in {content}:
            text = Text(f"• {{item}}", font_size=28, color=BLACK)
            explanation.add(text)
        explanation.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        explanation.next_to(formula, DOWN, buff=1)
'''

        return f'''
        # Default content
        content_group = VGroup()
        for item in {content}:
            text = Text(f"• {{item}}", font_size=30, color=BLACK)
            content_group.add(text)
        content_group.arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        content_group.next_to(title, DOWN, buff=1)
'''

    def _generate_animation_code(self, slide: Dict, scene_type: str) -> str:
        """Generate animation sequence code"""
        animation_type = slide.get("animation_type", "fade_in")

        animations = {
            "fade_in": """
        self.play(FadeIn(content_items, shift=UP))
        for item in content_items:
            self.play(Indicate(item, color=BLUE))
            self.wait(0.3)""",

            "write_gradually": """
        for item in content_items:
            self.play(Write(item))
            self.wait(0.5)""",

            "highlight": """
        self.play(FadeIn(content_items))
        self.wait(1)
        for item in content_items:
            self.play(
                item.animate.set_color(BLUE_D),
                run_time=0.5
            )
            self.wait(0.3)
            self.play(
                item.animate.set_color(BLACK),
                run_time=0.3
            )""",

            "transform": """
        temp_group = content_items.copy()
        temp_group.shift(LEFT * 3)
        self.play(Transform(temp_group, content_items))
        self.wait(1)"""
        }

        return animations.get(animation_type, animations["fade_in"])

    async def _render_scene(self, scene_file: str, scene_number: int, temp_dir: str) -> str:
        """Render individual scene using Manim"""
        class_name = f"EducationalScene{scene_number}"

        cmd = [
            "manim",
            scene_file,
            class_name,
            "-q", "high_quality",
            "--output_file", f"scene_{scene_number}",
            "--media_dir", temp_dir
        ]

        try:
            # Run Manim command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise Exception(f"Manim rendering failed: {stderr.decode()}")

            # Find output file
            video_file = os.path.join(temp_dir, "videos", f"{class_name}", "1080p60", f"scene_{scene_number}.mp4")

            if not os.path.exists(video_file):
                raise Exception(f"Output video file not found: {video_file}")

            return video_file

        except Exception as e:
            raise Exception(f"Scene rendering failed: {str(e)}")

    async def _combine_scenes(self, scene_files: List[str], temp_dir: str) -> str:
        """Combine multiple scenes into final video using FFmpeg"""
        # Create list file for FFmpeg
        list_file = os.path.join(temp_dir, "video_list.txt")
        with open(list_file, 'w') as f:
            for scene_file in scene_files:
                f.write(f"file '{scene_file}'\n")

        # Output file path
        output_file = os.path.join(temp_dir, "final_video.mp4")

        # FFmpeg command to concatenate videos
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            output_file,
            "-y"  # Overwrite output file
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise Exception(f"Video combination failed: {stderr.decode()}")

            return output_file

        except Exception as e:
            raise Exception(f"Video combination failed: {str(e)}")