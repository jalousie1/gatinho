import discord
from discord import app_commands
from discord.ext import commands
from guild_config import MY_GUILD
import os
from moviepy.editor import VideoFileClip
import tempfile
import asyncio
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path
import subprocess
import shutil

@dataclass
class ConversionSettings:
    ffmpeg_path: str = "C:\\ffmpeg\\ffmpeg.exe"
    max_size_mb: int = 8

class GifConverter:
    def __init__(self, settings: ConversionSettings):
        self.settings = settings

    def convert(self, input_path: str, output_path: str) -> Tuple[bool, Optional[str]]:
        try:
            if not os.path.exists(input_path):
                return False, "Video file not found"
            
            ffmpeg = self.settings.ffmpeg_path
            if not os.path.exists(ffmpeg):
                return False, f"ffmpeg not found at {ffmpeg}"

            palette_path = output_path + "_palette.png"
            
            # Run commands silently
            palette_cmd = [
                ffmpeg, '-i', input_path,
                '-vf', 'palettegen',
                '-y', '-loglevel', 'error',  # Suppress output
                palette_path
            ]
            
            convert_cmd = [
                ffmpeg, '-i', input_path, '-i', palette_path,
                '-lavfi', '[0:v][1:v]paletteuse=dither=sierra2_4a',
                '-y', '-loglevel', 'error',  # Suppress output
                output_path
            ]
            
            try:
                subprocess.run(palette_cmd, check=True, capture_output=True)
                subprocess.run(convert_cmd, check=True, capture_output=True)
            finally:
                if os.path.exists(palette_path):
                    os.unlink(palette_path)
            
            if not self._verify_output(output_path):
                return False, "mt grande o gif q merda q eu fiz"
                
            return True, None
            
        except Exception as e:
            return False, f"erro pra converter: {str(e)}"

    def _verify_output(self, output_path: str) -> bool:
        if not os.path.exists(output_path):
            return False
        
        size = os.path.getsize(output_path)
        if size == 0:
            return False
            
        if size > self.settings.max_size_mb * 1024 * 1024:
            return False
            
        return True

class MP4ToGif(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.max_file_size = 25 * 1024 * 1024
        self.supported_formats = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        self.converter = GifConverter(ConversionSettings())

    @app_commands.command(
        name="mp4togif",
        description="converte video pra gif"
    )
    @app_commands.describe(
        video="faz upload ai de ate 25mb"
    )
    @app_commands.guilds(MY_GUILD)
    async def mp4togif(self, interaction: discord.Interaction, video: discord.Attachment):
        await interaction.response.defer(thinking=True)
        
        temp_files = []
        try:
            if not self._validate_input(video):
                await interaction.followup.send(
                    f"nao tem esse formato aqui nao, so esses aqui q pode: {', '.join(self.supported_formats)}",
                    ephemeral=True
                )
                return

            # Setup temp files
            video_path, gif_path = await self._create_temp_files(video, interaction.id)
            temp_files.extend([video_path, gif_path])

            # Download and convert
            await video.save(video_path)
            success, error_msg = await self._convert_video(video_path, gif_path)

            if success:
                await self._send_success_response(interaction, gif_path)
            else:
                await self._send_error_response(interaction, error_msg)

        except Exception as e:
            await interaction.followup.send(
                f"erro ao processar: {str(e)}",
                ephemeral=True
            )
        finally:
            await self._cleanup_files(temp_files)

    def _validate_input(self, video: discord.Attachment) -> bool:
        if video.size > self.max_file_size:
            return False
        return os.path.splitext(video.filename)[1].lower() in self.supported_formats

    async def _create_temp_files(self, video: discord.Attachment, interaction_id: int) -> Tuple[str, str]:
        temp_dir = Path(tempfile.gettempdir())
        video_path = str(temp_dir / f"temp_video_{interaction_id}{os.path.splitext(video.filename)[1]}")
        gif_path = str(temp_dir / f"temp_gif_{interaction_id}.gif")
        return video_path, gif_path

    async def _convert_video(self, video_path: str, gif_path: str) -> Tuple[bool, Optional[str]]:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            self.converter.convert,  # Call without lambda
            video_path,
            gif_path
        )
        return result

    async def _send_success_response(self, interaction: discord.Interaction, gif_path: str):
        await interaction.followup.send(
            "gif aq man:",
            file=discord.File(gif_path, filename="converted.gif")
        )

    async def _send_error_response(self, interaction: discord.Interaction, error_msg: Optional[str]):
        await interaction.followup.send(
            error_msg or "deu erro vei tenta um vídeo menor ou mais curto.",
            ephemeral=True
        )

    async def _cleanup_files(self, files: list[str]):
        for file in files:
            try:
                if file and os.path.exists(file):
                    os.unlink(file)
            except Exception as e:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(MP4ToGif(bot))
