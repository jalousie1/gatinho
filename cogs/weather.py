import discord
from discord import app_commands
from discord.ext import commands
from guild_config import MY_GUILD
import aiohttp
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os
import json
from pathlib import Path

load_dotenv()

class Weather(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = os.getenv('WEATHER_API_KEY')
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.geo_url = "http://api.openweathermap.org/geo/1.0/direct"
        # Modificar para usar caminho absoluto
        self.data_file = Path(__file__).parent.parent / 'data' / 'weather_history.json'
        self.ensure_data_file()

    def ensure_data_file(self):
        try:
            self.data_file.parent.mkdir(exist_ok=True)
            if not self.data_file.exists() or self.data_file.stat().st_size == 0:
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
        except Exception as e:
            print(f"Error creating data file: {e}")

    def save_weather_data(self, user_id: int, location: str, weather_data: dict, interaction: discord.Interaction):
        try:
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    history = json.loads(content) if content.strip() else []
            except (json.JSONDecodeError, FileNotFoundError):
                history = []
            
            current_time = datetime.utcnow()
            
            entry = {
                'usuario': {
                    'id': interaction.user.id,
                    'nome': interaction.user.name,
                    'nick': interaction.user.display_name
                },
                'data_mensagem': current_time.isoformat(),
                'chat_mensagem': {
                    'guild_id': interaction.guild_id,
                    'channel_id': interaction.channel_id,
                    'mensagem_id': interaction.id
                },
                'location': location,
                'weather_data': weather_data
            }
            
            history.append(entry)
            
            # Removida a limitação de 1000 entradas para manter todo histórico
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            print("Data saved successfully")
            
        except Exception as e:
            print(f"Error saving weather data: {e}")

    async def get_coordinates(self, location: str):
        async with aiohttp.ClientSession() as session:
            params = {
                'q': location,
                'limit': 1,
                'appid': self.api_key
            }
            async with session.get(self.geo_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data:
                        return data[0]['lat'], data[0]['lon']
                return None

    async def get_weather(self, lat: float, lon: float):
        async with aiohttp.ClientSession() as session:
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric',  # para Celsius
            }
            async with session.get(f"{self.base_url}/weather", params=params) as response:
                if response.status == 200:
                    return await response.json()
                return None

    @app_commands.command(
        name="tempo",
        description="teste"
    )
    @app_commands.describe(
        local="mome da cidade ou país"
    )
    @app_commands.guilds(MY_GUILD)
    async def tempo(self, interaction: discord.Interaction, local: str):
        await interaction.response.defer()

        try:
            # Obter coordenadas
            coords = await self.get_coordinates(local)
            if not coords:
                await interaction.followup.send("naoo encontrei esse lugar... ")
                return

            # Obter dados do tempo
            weather_data = await self.get_weather(*coords)
            if not weather_data:
                await interaction.followup.send("nao consegui obter as informações do tempo...")
                return

            # Save weather data
            self.save_weather_data(interaction.user.id, local, weather_data, interaction)

            # Criar embed
            embed = discord.Embed(
                title=f"tempo em {weather_data['name']}, {weather_data['sys']['country']}",
                color=discord.Color.blue()
            )

            # Temperatura e sensação térmica
            temp = weather_data['main']['temp']
            feels_like = weather_data['main']['feels_like']
            embed.add_field(
                name="temperatura",
                value=f"**atual:** {temp:.1f}°C\n**sensacao:** {feels_like:.1f}°C",
                inline=False
            )

            # Condição do tempo
            weather_desc = weather_data['weather'][0]['description'].capitalize()
            embed.add_field(
                name="condicão",
                value=weather_desc,
                inline=True
            )

            # Umidade
            humidity = weather_data['main']['humidity']
            embed.add_field(
                name="umidade",
                value=f"{humidity}%",
                inline=True
            )

            # Horário local
            timezone_offset = weather_data['timezone']  # offset em segundos
            local_time = datetime.utcnow().timestamp() + timezone_offset
            time_str = datetime.fromtimestamp(local_time).strftime('%d/%m/%Y %H:%M')
            embed.add_field(
                name="hora local",
                value=time_str,
                inline=False
            )

            # Ícone do tempo como thumbnail
            icon_code = weather_data['weather'][0]['icon']
            embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{icon_code}@2x.png")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"erro: {str(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Weather(bot))
