# main.py
import discord
from discord.ext import commands
import os
import config
from guild_config import MY_GUILD

# Configurar intents
intents = discord.Intents.all()
intents.members = True
intents.message_content = True
intents.presences = True

# Criar o bot
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=1301020872664023153
        )
    
    async def setup_hook(self):
        print("bot zikaaaa")
        
        # Limpar comandos antigos
        print("arrumando os comandos antigo aqui")
        self.tree.clear_commands(guild=None)
        self.tree.clear_commands(guild=MY_GUILD)
        await self.tree.sync(guild=None)
        print("limpei...")

        # Carregar cogs
        print("carregando cogs:")
        cogs_folder = './cogs'
        cogs_carregados = 0
        cogs_falhados = 0
        
        for filename in os.listdir(cogs_folder):
            if filename.endswith('.py') and not filename.startswith('__'):
                cog_name = filename[:-3]
                try:
                    await self.load_extension(f'cogs.{cog_name}')
                    print(f"✓ {cog_name}")
                    cogs_carregados += 1
                except Exception as e:
                    print(f"✗ {cog_name}: {str(e)}")
                    cogs_falhados += 1

        # Sincronizar comandos
        print("botando comandos novos")
        await self.tree.sync(guild=MY_GUILD)
        
        # Resumo
        print(f"\nTERMINEI")
        print(f"cogs funcionando: {cogs_carregados}")
        print(f"cogs com erro: {cogs_falhados}")
        print("-----------------")
    
    async def on_ready(self):
        print(f'Bot conectado como: {self.user} (ID: {self.user.id})')
        
    # Sobrescrever process_commands para ignorar comandos de prefixo
    async def process_commands(self, message: discord.Message):
        return
    
bot = Bot()

# Executar o bot
bot.run(config.TOKEN)
