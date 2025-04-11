# invite_cog.py (Enhanced Invite Embed)
import discord
from discord.ext import commands
from discord import app_commands

class InviteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.command(name="invite", help="Sends an invite link with an embedded message and button.")
    async def invite_command(self, ctx):
        await self.send_invite_embed(ctx)
    
    @app_commands.command(name="invite", description="Sends an invite link with an embedded message and button.")
    async def slash_invite_command(self, interaction: discord.Interaction):
        await self.send_invite_embed(interaction)
    
    async def send_invite_embed(self, ctx_or_interaction):
        permissions = discord.Permissions(administrator=True)
        invite_link = discord.utils.oauth_url(ctx_or_interaction.client.user.id, permissions=permissions)
        
        embed = discord.Embed(
            title="🌟 Invite Our Bot!",
            description="Enhance your server with powerful features! Click the button below to invite the bot now!",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=ctx_or_interaction.client.user.avatar.url)
        embed.add_field(name="✨ Features", value="✔️ Moderation\n✔️ Fun Commands\n✔️ Utility Tools", inline=False)
        embed.add_field(name="🛠️ Setup", value="Use `/help` to explore commands.", inline=False)
        embed.set_footer(text="Thank you for supporting our bot! 🚀")
        
        view = discord.ui.View()
        button = discord.ui.Button(label="🚀 Invite Bot", url=invite_link, style=discord.ButtonStyle.link)
        view.add_item(button)
        
        if isinstance(ctx_or_interaction, commands.Context):
            await ctx_or_interaction.send(embed=embed, view=view)
        else:
            await ctx_or_interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(InviteCog(bot))
