import discord
from discord import app_commands
from discord.ext import commands
from guild_config import MY_GUILD

class Cleanup(commands.Cog):
    """Cog responsável por gerenciar a limpeza de mensagens no chat"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.guilds(MY_GUILD)
    @app_commands.command(
        name="limpar",
        description="Limpa mensagens do chat"
    )
    @app_commands.describe(
        quantidade="Número de mensagens para apagar (1-100)",
        usuario="Apagar mensagens apenas deste usuário"
    )
    async def limpar(
        self,
        interaction: discord.Interaction,
        quantidade: int,
        usuario: discord.Member = None
    ):
        if not 1 <= quantidade <= 100:
            await interaction.response.send_message(
                "A quantidade deve ser entre 1 e 100 mensagens.",
                ephemeral=True
            )
            return

        # Check if user has '*' role
        has_admin = any(role.name == '*' for role in interaction.user.roles)
        
        # If user doesn't have '*' role, they can only delete their own messages
        if not has_admin:
            if usuario and usuario.id != interaction.user.id:
                await interaction.response.send_message(
                    "Você só pode apagar suas próprias mensagens!",
                    ephemeral=True
                )
                return
            usuario = interaction.user

        # Responder primeiro para não causar erro
        await interaction.response.defer(ephemeral=True)

        # Função para filtrar mensagens
        def check_message(message):
            if usuario:
                return message.author.id == usuario.id
            return True  # Permite apagar todas as mensagens se tiver permissão

        # Apagar mensagens
        try:
            deleted = await interaction.channel.purge(
                limit=quantidade,
                check=check_message,
                reason=f"{interaction.user} limpou o chat"
            )
            
            msg = f"Apagadas {len(deleted)} mensagens"
            if usuario and usuario != interaction.user:
                msg += f" de {usuario.name}"
                
            await interaction.followup.send(msg, ephemeral=False)
            
        except discord.Forbidden:
            await interaction.followup.send("Não tenho permissão para apagar mensagens!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Erro ao apagar mensagens: {str(e)}", ephemeral=True)

    @limpar.error
    async def limpar_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "Você precisa ter permissão para gerenciar mensagens para usar este comando!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"Ocorreu um erro: {str(error)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Cleanup(bot))
