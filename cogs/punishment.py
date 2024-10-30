import discord
from discord import app_commands
from discord.ext import commands
from guild_config import MY_GUILD
from datetime import timedelta
import re

class Punishment(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channel_id = 1295621384373932074  # mesmo canal de logs do role_checker

    async def send_log(self, message):
        channel = self.bot.get_channel(self.log_channel_id)
        if channel:
            await channel.send(message)

    def parse_time(self, time_str: str) -> int:
        """Converte string de tempo (1d, 2h, 30m) para minutos"""
        time_dict = {'d': 1440, 'h': 60, 'm': 1}  # multiplicadores para converter em minutos
        match = re.match(r'(\d+)([dhm])', time_str.lower())
        
        if not match:
            raise ValueError("tempo inválido ve o exemplo fdp")
        
        num, unit = match.groups()
        return int(num) * time_dict[unit]

    @app_commands.command(
        name="castigo",
        description="Coloca um usuário de castigo (timeout)"
    )
    @app_commands.describe(
        usuario="user",
        tempo="tempo do castigo (ex: 1d, 2h, 30m)",
        motivo="motivo"
    )
    @app_commands.guilds(MY_GUILD)
    @app_commands.default_permissions(moderate_members=True)
    async def castigo(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        tempo: str,
        motivo: str
    ):
        try:
            # Verificar se o usuário tem o cargo "*"
            if not any(role.name == "*" for role in interaction.user.roles):
                await interaction.response.send_message("ta sem permissao ai fdp", ephemeral=True)
                await self.send_log(
                    f"**SEM CARGO OTARIO**\n"
                    f"comando: /castigo\n"
                    f"quem deu: {interaction.user.name}\n"
                    f"motivo: NAO TEM CARGO HAHAHAHAH *"
                )
                return

            # Verificar permissões
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message("ta sem permissao ai fdp", ephemeral=True)
                await self.send_log(
                    f"**SEM PERM SE FUDEU**\n"
                    f"comando: /castigo\n"
                    f"quem deu: {interaction.user.name}\n"
                    f"motivo: Sem permissão moderate_members"
                )
                return

            # Verificar se pode moderar o usuário alvo
            if usuario.top_role.position >= interaction.user.top_role.position:
                await interaction.response.send_message("Você não tem permissão para castigar este usuário.", ephemeral=True)
                await self.send_log(
                    f"**Tentativa de castigo falhou**\n"
                    f"Comando: /castigo\n"
                    f"Executado por: {interaction.user.name}\n"
                    f"Usuário alvo: {usuario.name}\n"
                    f"Motivo: O usuário alvo possui um cargo igual ou superior."
                )
                return

            # Converter tempo para minutos
            try:
                minutos = self.parse_time(tempo)
                if minutos > 40320:  # máximo de 28 dias
                    await interaction.response.send_message("so pode so ate 28 dias vei...", ephemeral=True)
                    await self.send_log(
                        f"**ARRUMA O TEMPO AI**\n"
                        f"Comando: /castigo\n"
                        f"Quem deu: {interaction.user.name}\n"
                        f"Tempo: {tempo}\n"
                        f"Motivo: mais de 28 dias"
                    )
                    return
            except ValueError:
                await interaction.response.send_message("usa: 1d, 2h ou 30m", ephemeral=True)
                await self.send_log(
                    f"**FORMATO INVALIDO**\n"
                    f"Comando: /castigo\n"
                    f"Quem deu: {interaction.user.name}\n"
                    f"Tempo informado: {tempo}\n"
                    f"Motivo: BURRO NAO SABE LER O EXEMPLO"
                )
                return

            # Aplicar timeout
            await usuario.timeout(
                timedelta(minutes=minutos),
                reason=f"castigo feito por: {interaction.user}: {motivo}"
            )

            # Criar embed para resposta
            embed = discord.Embed(
                title="castigado bb",
                color=discord.Color.red()
            )
            embed.add_field(name="usuario", value=f"{usuario.mention} ({usuario.name})", inline=False)
            embed.add_field(name="tempo", value=tempo, inline=True)
            embed.add_field(name="motivo", value=motivo, inline=True)
            embed.set_footer(text=f"aplicado por {interaction.user.name}")

            # Enviar confirmação
            await interaction.response.send_message(embed=embed)
            
            # Log de sucesso
            await self.send_log(
                f"**SE FUDEU CASTIGADO**\n"
                f"Comando: /castigo\n"
                f"Quem deu: {interaction.user.name}\n"
                f"El castigado: {usuario.name}\n"
                f"Tempo: {tempo}\n"
                f"Motivo: {motivo}"
            )

        except discord.Forbidden:
            await interaction.response.send_message("NAO CONSIGO O CARA EH MAIOR QUE EU", ephemeral=True)
            await self.send_log(
                f"**PERM DO CARA EH MAIOR QUE EU DO BOT**\n"
                f"Comando: /castigo\n"
                f"Quem deu: {interaction.user.name}\n"
                f"A tentativa: {usuario.name}\n"
                f"Motivo: NEM EU QUE SOU BOT CONSIGO"
            )
        except Exception as e:
            await interaction.response.send_message(f"NAO CONSEGUI DAR O CASTIGO: {str(e)}", ephemeral=True)
            await self.send_log(
                f"**dei pau**\n"
                f"Comando: /castigo\n"
                f"Quem deu: {interaction.user.name}\n"
                f"Erro: {str(e)}"
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Punishment(bot))
