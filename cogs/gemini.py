import discord
from discord import app_commands
from dotenv import load_dotenv
from discord.ext import commands
import google.generativeai as genai
import os
from guild_config import MY_GUILD

load_dotenv()

class GeminiCog(commands.Cog):
    """Cog para interação com IA Gemini no Discord"""
    
    def __init__(self, bot: commands.Bot):
        """Inicializa bot e configurações do Gemini"""
        self.bot = bot
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.chat_sessions = {}
        
        # Configurações de segurança para filtrar conteúdo inadequado
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
        ]
        
        # Configurações de geração de texto
        self.generation_config = {
            "temperature": 0.9,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
    
    @app_commands.command(
        name="chat",
        description="conversa sozinho com a ia ai"
    )
    @app_commands.describe(
        pergunta="pergunta ai"
    )
    @app_commands.guilds(MY_GUILD)
    async def chat(self, interaction: discord.Interaction, pergunta: str):
        """Processa perguntas do usuário e retorna respostas da IA"""
        await interaction.response.defer()
        
        try:
            user_id = interaction.user.id
            
            # Initialize chat session for new users
            if user_id not in self.chat_sessions:
                self.chat_sessions[user_id] = self.model.start_chat(history=[])
            
            response = await self.chat_sessions[user_id].send_message_async(
                pergunta,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                await interaction.followup.send(
                    "digita direito ai fdp tenha educacao",
                    ephemeral=True
                )
                return

            # Split response into chunks of 2000 characters (Discord limit)
            chunks = [response.text[i:i+2000] for i in range(0, len(response.text), 2000)]
            
            # Send first chunk as reply
            await interaction.followup.send(chunks[0])
            
            # Send remaining chunks if any
            for chunk in chunks[1:]:
                await interaction.channel.send(chunk)
                    
        except Exception as e:
            await interaction.followup.send(
                f"erro: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    """Carrega o cog no bot"""
    await bot.add_cog(GeminiCog(bot))