import discord
from discord import app_commands
from discord.ext import commands
from guild_config import MY_GUILD
import logging
import asyncio
import aiohttp
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('friendship_deleter.log')
    ]
)

class StopButton(discord.ui.View):
    def __init__(self, command_user: discord.Member):
        super().__init__()
        self.stopped = False
        self.command_user = command_user

    @discord.ui.button(label="Stop process", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.command_user.id:
            await interaction.response.send_message("Only the command initiator can use this button!", ephemeral=True)
            return
        
        self.stopped = True
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("The process will be stopped...", ephemeral=True)

class FriendshipDeleterCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_sessions = {}
        self.session = None

    async def setup_session(self):
        self.session = aiohttp.ClientSession()

    async def cog_load(self):
        await self.setup_session()

    async def cog_unload(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_relationships(self, token: str):
        # get user relationships
        headers = {'Authorization': token}
        async with self.session.get('https://discord.com/api/v9/users/@me/relationships', headers=headers) as response:
            if response.status == 200:
                return await response.json()
            return []

    async def get_dm_channels(self, token: str):
        # get dms
        headers = {'Authorization': token}
        async with self.session.get('https://discord.com/api/v9/users/@me/channels', headers=headers) as response:
            if response.status == 200:
                channels = await response.json()
                return [c for c in channels if c['type'] == 1]  # Type 1 is DM
            return []

    async def delete_relationship(self, user_id: str, token: str):
        # remove friend
        headers = {'Authorization': token}
        async with self.session.delete(f'https://discord.com/api/v9/users/@me/relationships/{user_id}', headers=headers) as response:
            return response.status == 204

    async def delete_dm_channel(self, channel_id: str, token: str):
        # delete dm
        headers = {'Authorization': token}
        async with self.session.delete(f'https://discord.com/api/v9/channels/{channel_id}', headers=headers) as response:
            return response.status == 200

    @app_commands.command(name='removefriend', description='Delete all friendships and DMs')
    @app_commands.guilds(MY_GUILD)
    @app_commands.describe(token="Your Discord user token")
    async def friendship_deleter(self, interaction: discord.Interaction, token: str):
        # create private channel
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        
        channel = await interaction.guild.create_text_channel(
            f'cleanup-{interaction.user.name}',
            overwrites=overwrites
        )
        
        await interaction.response.send_message(
            f"Private channel created: {channel.mention}",
            ephemeral=True
        )

        self.active_sessions[interaction.user.id] = channel.id

        try:
            # verify token
            async with self.session.get('https://discord.com/api/v9/users/@me', 
                                      headers={'Authorization': token}) as response:
                if response.status != 200:
                    await channel.send("❌ Invalid token!")
                    return

            stop_view = StopButton(command_user=interaction.user)
            status_message = await channel.send("🔍 Getting list of friends and DMs...", view=stop_view)

            # Get relationships and DMs
            relationships = await self.get_relationships(token)
            dm_channels = await self.get_dm_channels(token)

            total_friends = len(relationships)
            total_dms = len(dm_channels)

            await status_message.edit(content=f"""
📊 Found:
- {total_friends} friendships
- {total_dms} private conversations

💬 Type 'confirm' to start the cleanup:
""")

            def check(m):
                return m.author.id == interaction.user.id and m.channel == channel

            try:
                confirm = await self.bot.wait_for('message', timeout=30.0, check=check)
                if confirm.content.lower() != 'confirm':
                    await status_message.edit(content="❌ Operation cancelled!", view=None)
                    return
            except asyncio.TimeoutError:
                await status_message.edit(content="⏰ Time's up!", view=None)
                return

            # Delete friends
            deleted_friends = 0
            failed_friends = 0
            
            for friend in relationships:
                if stop_view.stopped:
                    break

                try:
                    if await self.delete_relationship(friend['id'], token):
                        deleted_friends += 1
                    else:
                        failed_friends += 1

                    progress = (deleted_friends / total_friends) * 100
                    await status_message.edit(content=f"""
🔄 Removing friendships... 
Progress: {deleted_friends}/{total_friends} ({progress:.1f}%)
✅ Success: {deleted_friends}
❌ Failed: {failed_friends}
""", view=stop_view)
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logging.error(f"Error deleting friendship: {e}")
                    failed_friends += 1

            # delete dms
            deleted_dms = 0
            failed_dms = 0

            for dm in dm_channels:
                if stop_view.stopped:
                    break

                try:
                    if await self.delete_dm_channel(dm['id'], token):
                        deleted_dms += 1
                    else:
                        failed_dms += 1

                    progress = (deleted_dms / total_dms) * 100
                    await status_message.edit(content=f"""
🔄 Removing conversations... 
Progress: {deleted_dms}/{total_dms} ({progress:.1f}%)
✅ Success: {deleted_dms}
❌ Failed: {failed_dms}
""", view=stop_view)
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logging.error(f"Error deleting DM: {e}")
                    failed_dms += 1

            final_status = f"""
✨ Process completed!

📊 Results:
👥 Friendships:
   - Removed: {deleted_friends}
   - Failed: {failed_friends}

💬 Conversations:
   - Removed: {deleted_dms}
   - Failed: {failed_dms}
"""
            await status_message.edit(content=final_status, view=None)

        except Exception as e:
            logging.error(f"Error in friendship deleter: {e}")
            await channel.send(f"❌ Error during process: {str(e)}")

        finally:
            await asyncio.sleep(5)
            await channel.delete()
            del self.active_sessions[interaction.user.id]

async def setup(bot: commands.Bot):
    await bot.add_cog(FriendshipDeleterCog(bot))
