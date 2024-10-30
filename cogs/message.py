import discord
from discord import app_commands
from discord.ext import commands
from guild_config import MY_GUILD
import aiohttp
from PIL import Image
from io import BytesIO

class Message(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def is_valid_image_url(self, url: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '')
                        return 'image' in content_type or 'gif' in content_type
            return False
        except:
            return False

    async def get_dominant_color(self, url: str) -> discord.Color:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.read()
                        image = Image.open(BytesIO(data))
                        # Convert to RGB if image is in RGBA mode
                        if image.mode == 'RGBA':
                            image = image.convert('RGB')
                        # Resize image to speed up processing
                        image = image.resize((100, 100))
                        # Get colors from image
                        pixels = image.getcolors(10000)
                        # Sort by count and get the most common color
                        sorted_pixels = sorted(pixels, key=lambda t: t[0], reverse=True)
                        dominant_color = sorted_pixels[0][1]
                        return discord.Color.from_rgb(*dominant_color)
            return discord.Color.blue()
        except:
            return discord.Color.blue()

    @app_commands.guilds(MY_GUILD)
    @app_commands.command(
        name="enviar",
        description="Envia uma mensagem pro pcr ai..."
    )
    @app_commands.describe(
        usuario="usuario",
        mensagem="mensagem",
        imagem="imagem ou gif",
        url_imagem="ou link de imagem ou gif"
    )
    async def enviar(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        mensagem: str,
        imagem: discord.Attachment = None,
        url_imagem: str = None
    ):
        # verifica se fez upload ou botou url
        if not imagem and not url_imagem:
            await interaction.response.send_message(
                "bota imagem ou url de imagem/gif ai...",
                ephemeral=True
            )
            return

        # se botou os dois vai priorizar o upload
        image_url = imagem.url if imagem else url_imagem

        # verifica se a url funciona
        if not imagem and not await self.is_valid_image_url(url_imagem):
            await interaction.response.send_message(
                "TA ERRADO ISSO AI MERMAO",
                ephemeral=True
            )
            return

        # pega a cor pra botar no embed
        embed_color = await self.get_dominant_color(image_url)

        # cria o embed
        embed = discord.Embed(
            description=mensagem,
            color=embed_color
        )
        embed.set_image(url=image_url)
        embed.set_footer(text=f"enviado por {interaction.user.name}")

        # envia a mensagem
        try:
            await interaction.channel.send(
                content=usuario.mention,
                embed=embed
            )
            await interaction.response.send_message(
                "mensagem enviada com sucesso!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "não tenho permissão para enviar mensagens neste canal!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"erro ao enviar mensagem: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Message(bot))
