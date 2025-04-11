import discord
from discord.ext import commands
from discord import app_commands

class HelpDropdown(discord.ui.Select):
    """Dropdown to select a help category and get detailed explanation."""
    
    def __init__(self, bot, ctx, language="English"):
        self.bot = bot
        self.ctx = ctx
        self.language = language  

        # Get all available categories
        self.categories = self.get_categories()
        
        # Dropdown options
        options = [
            discord.SelectOption(label=category, description=f"View commands for {category}") 
            for category in self.categories
        ]
        
        super().__init__(placeholder="📂 Select a command category...", options=options)

    def get_categories(self):
        """Fetches all command categories dynamically from bot cogs."""
        categories = set()
        for command in self.bot.commands:
            if command.cog_name:
                categories.add(command.cog_name)
        return sorted(categories)

    async def callback(self, interaction: discord.Interaction):
        """Handles category selection and displays detailed help."""
        selected_category = self.values[0]  # Get selected category
        embed = discord.Embed(title=f"📂 {selected_category} Commands", color=discord.Color.blue())

        commands_list = [cmd for cmd in self.bot.commands if cmd.cog_name == selected_category]
        
        for cmd in commands_list:
            embed.add_field(name=f"`lx {cmd.name}`", value=f"🔹 {cmd.help or 'No description available'}", inline=False)

        await interaction.response.edit_message(embed=embed, view=None)

class HelpCog(commands.Cog):
    """📜 Help System with Dropdown Menu."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", help="📜 Opens an interactive help menu.")
    async def help_command(self, ctx):
        """Sends the help menu with an interactive dropdown."""
        embed = discord.Embed(title="📜 Help Menu", description="📂 Select a category below.", color=discord.Color.green())

        view = discord.ui.View()
        view.add_item(HelpDropdown(self.bot, ctx))
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
# Compare this snippet from cogs/anti_reply_cog.py:
# import discord