import discord
from discord.ext import commands
import asyncio

class CategorySelect(discord.ui.Select):
    def __init__(self, bot, ctx, view):
        self.bot = bot
        self.ctx = ctx
        self.view = view

        options = [
            discord.SelectOption(
                label=cog_name,
                description=f"Commands from {cog_name} category",
                value=cog_name
            )
            for cog_name in bot.cogs.keys()
            if not cog_name.startswith("Help")  # Skip HelpCog itself
        ]

        super().__init__(placeholder="Choose a command category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_cog = self.values[0]
        cog = self.bot.get_cog(selected_cog)
        embed = discord.Embed(
            title=f"📚 {selected_cog} Commands",
            color=discord.Color.orange()
        )

        for command in cog.get_commands():
            embed.add_field(
                name=f"🔸 {command.name}",
                value=command.help or "No description.",
                inline=False
            )

        embed.set_footer(text="Use the dropdown to switch categories | Back button to return")

        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, bot, ctx, timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.message = None

        self.select = CategorySelect(bot, ctx, self)
        self.add_item(self.select)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except:
                pass

    @discord.ui.button(label="🔙 Back", style=discord.ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="💫 Command Help",
            description="Use the dropdown below to view commands by category.",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Message will auto-delete after 60 seconds")

        await interaction.response.edit_message(embed=embed, view=self)


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", help="📜 Opens an interactive help menu with categories.")
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="💫 Command Help",
            description="Use the dropdown below to view commands by category.",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Message will auto-delete after 60 seconds")

        view = HelpView(self.bot, ctx)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

        await asyncio.sleep(60)
        try:
            await msg.delete()
        except:
            pass


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
