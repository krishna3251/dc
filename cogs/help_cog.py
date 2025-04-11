import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class HelpView(discord.ui.View):
    """Interactive help menu with dropdown and back button functionality."""
    
    def __init__(self, bot, ctx, timeout=60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.add_item(HelpDropdown(bot, ctx))
        self.message = None
        
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
            description="Select a command category from the dropdown menu below.",
            color=discord.Color.purple()
        )
        main_embed.set_footer(text="Message will auto-delete after 60 seconds")
        
        # Reset the dropdown
        self.remove_item(self.children[0])  # Remove existing dropdown
        self.add_item(HelpDropdown(self.bot, self.ctx))  # Add a fresh dropdown
        
        await interaction.response.edit_message(embed=main_embed, view=self)

class HelpDropdown(discord.ui.Select):
    """Dropdown to select a help category and get detailed explanation."""
    
    def __init__(self, bot, ctx):
        self.bot = bot
        self.ctx = ctx

        # Get all available commands, grouped by functionality
        commands = self.get_commands_by_function()
        
        # Dropdown options - use emojis and friendlier group names
        options = []
        for group, info in commands.items():
            emoji = info["emoji"]
            options.append(
                discord.SelectOption(
                    label=group,
                    description=f"{info['description']}", 
                    emoji=emoji
                )
            )
        
        super().__init__(placeholder="📜 Select command category...", options=options, row=0)

    def get_commands_by_function(self):
        """Groups commands by functionality rather than cog names."""
        command_groups = {
            "Moderation": {
                "emoji": "🛡️",
                "description": "Server moderation commands",
                "commands": []
            },
            "Information": {
                "emoji": "ℹ️",
                "description": "Server and user info commands",
                "commands": []
            },
            "Permissions": {
                "emoji": "🔒",
                "description": "Role and channel permission management",
                "commands": []
            },
            "Utility": {
                "emoji": "🔧",
                "description": "General utility commands",
                "commands": []
            },
            "Fun": {
                "emoji": "🎮",
                "description": "Fun and entertainment commands",
                "commands": []
            }
        }
        
        # Categorize commands based on cog or name
        for command in self.bot.commands:
            if not command.hidden:
                if command.cog_name in ["Moderation", "PurgeMemberCog", "AntiSpamCog", "AntiReplyCog"]:
                    command_groups["Moderation"]["commands"].append(command)
                elif command.cog_name in ["ServerInfo", "MemberInfo"]:
                    command_groups["Information"]["commands"].append(command)
                elif command.cog_name in ["ChannelPermsCog", "VCPermissionCog", "MassRoleAddCog"]:
                    command_groups["Permissions"]["commands"].append(command)
                elif command.cog_name in ["PingCog", "InviteCog"]:
                    command_groups["Utility"]["commands"].append(command)
                elif command.cog_name in ["BirthdayResponder"]:
                    command_groups["Fun"]["commands"].append(command)
                else:
                    # Default categorization based on command name
                    if command.name in ["ban", "kick", "mute", "warn", "purge"]:
                        command_groups["Moderation"]["commands"].append(command)
                    elif command.name in ["help", "ping", "invite"]:
                        command_groups["Utility"]["commands"].append(command)
                    elif command.name in ["serverinfo", "userinfo", "members", "moderators"]:
                        command_groups["Information"]["commands"].append(command)
                    else:
                        command_groups["Utility"]["commands"].append(command)
        
        return command_groups

    async def callback(self, interaction: discord.Interaction):
        """Handles category selection and displays detailed help."""
        selected_category = self.values[0]  # Get selected category
        
        # Get all commands from this category
        command_groups = self.get_commands_by_function()
        selected_group = command_groups[selected_category]
        
        embed = discord.Embed(
            title=f"{selected_group['emoji']} {selected_category} Commands",
            description=f"{selected_group['description']}",
            color=discord.Color.blue()
        )

        # Add commands to embed
        if selected_group["commands"]:
            for cmd in selected_group["commands"]:
                embed.add_field(
                    name=f"`lx {cmd.name}`", 
                    value=f"{cmd.help or 'No description available'}", 
                    inline=False
                )
        else:
            embed.add_field(name="No Commands", value="This category has no commands yet.", inline=False)
            
        embed.set_footer(text="Use the Back button to return to categories")
        
        # Find the view this dropdown is part of
        view = self.view
        if view:
            await interaction.response.edit_message(embed=embed, view=view)

class HelpCog(commands.Cog):
    """Help System with Dropdown Menu and Auto-Delete."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", help="📜 Opens an interactive help menu.")
    async def help_command(self, ctx):
        """Sends the help menu with an interactive dropdown."""
        embed = discord.Embed(
            title="💫 Command Help",
            description="Select a command category from the dropdown menu below.",
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
