import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random

CATEGORY_EMOJIS = {
    "Music": "🎵",
    "Moderation": "🛡️",
    "Fun": "🎉",
    "Utility": "🧰",
    "General": "📌"
}

HELP_GIFS = [
    "https://media.tenor.com/5LWyJ6I_8KIAAAAd/xtreme-bot-help.gif",
    "https://media.tenor.com/Tz_GALR2e-QAAAAC/discord-help.gif",
    "https://media.tenor.com/OWU8NpyjTksAAAAC/bot-help-help.gif",
    "https://media.tenor.com/8QzhY8J8RjcAAAAC/help-command-discord.gif"
]

class CategorySelect(discord.ui.Select):
    def __init__(self, bot, help_view):
        self.bot = bot
        self.help_view = help_view

        options = []
        for cog_name, cog in bot.cogs.items():
            if cog_name.lower().startswith("help"):
                continue
            emoji = CATEGORY_EMOJIS.get(cog_name, "📁")
            options.append(discord.SelectOption(
                label=cog_name,
                value=cog_name,
                emoji=emoji,
                description=f"View commands in {cog_name}"
            ))

        super().__init__(
            placeholder="🔍 Choose a command category...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        cog = self.bot.get_cog(selected)

        embed = discord.Embed(
            title=f"{CATEGORY_EMOJIS.get(selected, '📁')} {selected} Commands",
            color=discord.Color.orange()
        )
        for cmd in cog.get_commands():
            embed.add_field(
                name=f"• `{cmd.name}`",
                value=cmd.help or "No description.",
                inline=False
            )

        embed.set_footer(text="🔙 Use the button below to return • Auto-deletes after 60s of inactivity.")
        await interaction.response.edit_message(embed=embed, view=self.help_view)

class HelpView(discord.ui.View):
    def __init__(self, bot, timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.message = None
        self.select_menu = CategorySelect(bot, self)
        self.add_item(self.select_menu)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except:
                pass

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💫 Command Help Menu",
            description="Use the dropdown below to explore commands by category.",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Dropdown active • Auto-deletes after 60s")
        embed.set_image(url=random.choice(HELP_GIFS))
        await interaction.response.edit_message(embed=embed, view=self)

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="📜 Opens an interactive help menu with categories.")
    async def help_slash(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💫 Command Help Menu",
            description="Use the dropdown below to explore commands by category.",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Dropdown active • Auto-deletes after 60s")
        embed.set_image(url=random.choice(HELP_GIFS))

        view = HelpView(self.bot)
        await interaction.response.defer()
        await interaction.followup.send(embed=embed, view=view)
        view.message = await interaction.original_response()

    @commands.command(name="help", help="📜 Opens an interactive help menu.")
    async def help_prefix(self, ctx):
        embed = discord.Embed(
            title="💫 Command Help Menu",
            description="Use the dropdown below to explore commands by category.",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Dropdown active • Auto-deletes after 60s")
        embed.set_image(url=random.choice(HELP_GIFS))

        view = HelpView(self.bot)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg
        await asyncio.sleep(60)
        try:
            await msg.delete()
        except:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            synced = await self.bot.tree.sync()
            print(f"✅ Synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"❌ Failed to sync slash commands: {e}")

async def setup(bot):
    await bot.add_cog(Help(bot))
