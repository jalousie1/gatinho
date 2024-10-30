import discord
from discord import app_commands
from discord.ext import commands
from guild_config import MY_GUILD
from PIL import Image
import io
import aiohttp
import colorsys

class Basic(commands.Cog):
    """Comandos básicos do bot."""
    
    def __init__(self, bot: commands.Bot):
        """Inicializa o cog Basic."""
        self.bot = bot

    async def get_dominant_color(self, avatar_url):
        """
        Obtém a cor dominante de uma imagem de avatar.
        
        Args:
            avatar_url: URL do avatar do usuário
        Returns:
            discord.Color: Cor dominante do avatar
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(str(avatar_url)) as response:
                avatar_bytes = await response.read()

        # Processar a imagem para encontrar a cor dominante
        image = Image.open(io.BytesIO(avatar_bytes)).convert('RGBA')
        # Redimensionar para processamento mais rápido
        image.thumbnail((100, 100))
        
        # Coletar todas as cores não transparentes
        colors = []
        for pixel in image.getdata():
            if pixel[3] > 0:  # Se não for transparente
                colors.append(pixel[:3])
        
        if not colors:
            return discord.Color.default()

        # Calcular a cor média
        r = sum(color[0] for color in colors) // len(colors)
        g = sum(color[1] for color in colors) // len(colors)
        b = sum(color[2] for color in colors) // len(colors)
        
        return discord.Color.from_rgb(r, g, b)

    @app_commands.guilds(MY_GUILD)
    @app_commands.command(
        name="info",
        description="Mostra informações de conta de um usuário"
    )
    @app_commands.describe(
        usuario="Marque o usuario para ver as informações dele"
    )
    async def info(
        self, 
        interaction: discord.Interaction, 
        usuario: discord.Member = None
    ):
        """
        Exibe informações detalhadas sobre um usuário.
        
        Args:
            interaction: Interação do Discord
            usuario: Membro do servidor a ser consultado (opcional)
        """
        # Atualizar o membro para ter as informações mais recentes
        usuario = usuario or interaction.user
        try:
            usuario = await interaction.guild.fetch_member(usuario.id)
        except discord.NotFound:
            await interaction.response.send_message("Usuário não encontrado!", ephemeral=True)
            return
        
        # Pegar a cor dominante do avatar
        embed_color = await self.get_dominant_color(usuario.display_avatar.url)
        
        embed = discord.Embed(
            title=f"Informações do Usuário",
            description=f"**{usuario.name}**",
            color=embed_color
        )
        
        # Avatar grande e bonito
        embed.set_thumbnail(url=usuario.display_avatar.url)
        
        # Primeira seção - Informações básicas
        info_basica = f"**ID:** {usuario.id}\n"
        info_basica += f"**Tag Discord:** {usuario.name}#{usuario.discriminator}\n"
        info_basica += f"**Nome no Servidor:** {usuario.display_name}\n"
        info_basica += f"**Tipo:** {'Bot' if usuario.bot else 'Usuário'}"
        embed.add_field(name="Informações Básicas", value=info_basica, inline=False)
        
        # Segunda seção - Datas importantes
        datas = f"**Conta Criada:** {discord.utils.format_dt(usuario.created_at, 'F')}\n"
        datas += f"**Entrou no Servidor:** {discord.utils.format_dt(usuario.joined_at, 'F')}"
        embed.add_field(name="Datas", value=datas, inline=False)
        
        # Terceira seção - Boost e cargos
        outros = ""
        if usuario.premium_since:
            outros += f"**Booster desde:** {discord.utils.format_dt(usuario.premium_since, 'F')}\n"
        roles = [role.mention for role in usuario.roles[1:]]  # Usando mention ao invés de name
        if roles:
            outros += f"**Cargos [{len(roles)}]:** {' '.join(roles)}"
        else:
            outros += "**Cargos:** Nenhum"
        embed.add_field(name="Outros Detalhes", value=outros, inline=False)
        
        # Footer com timestamp
        embed.set_footer(text="Informações obtidas em")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Basic(bot))