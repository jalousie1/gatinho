import discord
from discord.ext import commands
from discord import app_commands
from guild_config import MY_GUILD
import json
from datetime import datetime
from pathlib import Path

class Nuke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = Path(__file__).parent.parent / 'data' / 'nuke_history.json'
        self.ensure_data_file()

    def ensure_data_file(self):
        try:
            self.data_file.parent.mkdir(exist_ok=True)
            if not self.data_file.exists() or self.data_file.stat().st_size == 0:
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
        except Exception as e:
            print(f"Error creating data file: {e}")

    async def save_nuke_data(self, interaction: discord.Interaction, channel: discord.TextChannel):
        try:
            # Get message count from channel
            message_count = 0
            async for _ in channel.history(limit=None):
                message_count += 1

            with open(self.data_file, 'r', encoding='utf-8') as f:
                content = f.read()
                history = json.loads(content) if content.strip() else []
            
            current_time = datetime.now()
            
            entry = {
                'usuario': interaction.user.name,
                'data': current_time.strftime('%d/%m/%Y'),
                'hora': current_time.strftime('%H:%M:%S'),
                'numero_de_mensagens': message_count,
                'canal_nukado': channel.name
            }
            
            history.append(entry)
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            print("Nuke data saved successfully")
            
        except Exception as e:
            print(f"Error saving nuke data: {e}")

    @app_commands.command(name="nuke", description="nukando")
    @app_commands.guilds(MY_GUILD)
    @app_commands.default_permissions(manage_channels=True)
    async def nuke(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not discord.utils.get(interaction.user.roles, name="*"):
            await interaction.response.send_message("sem cargo bro", ephemeral=True)
            return

        try:
            # Save nuke data before executing
            await self.save_nuke_data(interaction, channel)

            # Rest of the existing code...
            position = channel.position
            category = channel.category
            overwrites = channel.overwrites
            name = channel.name
            topic = channel.topic
            slowmode = channel.slowmode_delay
            nsfw = channel.nsfw

            await interaction.response.send_message(f"ACABANDO COM TUDO {channel.mention}...")

            await channel.delete()
            new_channel = await interaction.guild.create_text_channel(
                name=name,
                overwrites=overwrites,
                category=category,
                topic=topic,
                slowmode_delay=slowmode,
                nsfw=nsfw,
                position=position
            )

            await new_channel.send(f"nukado por {interaction.user.name}")

        except discord.Forbidden:
            await interaction.response.send_message("to sem perm", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"erro: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Nuke(bot))
