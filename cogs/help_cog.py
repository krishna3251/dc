import discord
from discord.ext import commands
import asyncio

class HelpView(discord.ui.View):
    """Interactive help menu with only a back button."""
    
    def __init__(self, bot, ctx, timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.message = None  # No dropdown added here
       
    async def on_timeout(self):
        """Auto-deletes the help message after timeout."""
        if self.message:
            try:
                await self.message.delete()
            except:
                pass
            
    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Returns to the main help menu."""
        main_embed = discord.Embed(
            title="💫 Command Help",
            description="This is the main help menu. (Dropdown disabled)",
            color=discord.Color.purple()
        )
        main_embed.set_footer(text="Message will auto-delete after 60 seconds")
        
        await interaction.response.edit_message(embed=main_embed, view=self)

class HelpCog(commands.Cog):
    """Help System with Back Button Only."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", help="📜 Opens an interactive help menu.")
    async def help_command(self, ctx):
        """Sends the help menu with just a back button."""
        embed = discord.Embed(
            title="💫 Command Help",
            description="This is the main help menu. (Dropdown disabled)",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Message will auto-delete after 60 seconds")
        
        view = HelpView(self.bot, ctx)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg
        
        # Auto-delete after 60 seconds
        await asyncio.sleep(60)
        try:
            await msg.delete()
        except:
            pass

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
