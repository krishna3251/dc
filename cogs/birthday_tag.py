import discord
from discord.ext import commands

class BirthdayResponder(commands.Cog):
    """🎉 Auto-response when someone tags a specific user for birthday wishes."""

    def __init__(self, bot):
        self.bot = bot
        self.target_user_id = 486555340670894080  # Replace with Krishna's Discord ID

    @commands.Cog.listener()
    async def on_message(self, message):
        """Detects when someone tags the target user and replies + DMs them."""
        if message.author.bot:
            return  # Ignore bot messages

        if str(self.target_user_id) in message.content and "happy birthday" in message.content.lower():
            # Respond to the user who tagged
            await message.reply(f"🎉 Thanks {message.author.mention}! <@{self.target_user_id}> is absent now, he will talk to you later.")

            # Fetch the target user properly
            try:
                target_user = await self.bot.fetch_user(self.target_user_id)  # Fetch from API
                if target_user:
                    await target_user.send(f"🎂 **{message.author}** tagged you with a birthday wish:\n> {message.content}")
            except discord.Forbidden:
                print(f"❌ Cannot DM {self.target_user_id}. DMs might be disabled.")
            except discord.HTTPException as e:
                print(f"❌ Failed to send DM: {e}")

async def setup(bot):
    await bot.add_cog(BirthdayResponder(bot))
