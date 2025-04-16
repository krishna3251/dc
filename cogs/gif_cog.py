import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from typing import Dict, List, Optional, Any, Union
import datetime

class HelpDropdown(discord.ui.Select):
    """Dropdown menu for the help command"""
    
    def __init__(self, help_command, categories: Dict[str, dict]):
        self.help_command = help_command
        self.categories = categories
        
        # Create options for each category
        options = []
        for category, data in categories.items():
            if category == "No Category":
                emoji = "📋"
            else:
                # Choose emoji based on category name
                emoji_map = {
                    "Moderation": "🛡️",
                    "Server": "🌐",
                    "Utility": "🔧",
                    "GIF": "🎬",
                    "Fun": "🎮",
                    "Info": "ℹ️",
                    "Channel": "📺",
                    "Voice": "🔊",
                    "Anti-Spam": "🚫",
                    "Logging": "📝",
                    "Stats": "📊",
                    "Welcome": "👋",
                    "Channels": "🏠",
                    "Backup": "💾",
                    "Roles": "👑",
                    "Activity": "🏆",
                    "Custom": "⚙️",
                    "Filter": "🚫",
                    "Search": "🔍",
                    "Spotify": "🎵",
                    "Music": "🎵"
                }
                emoji = emoji_map.get(category, "📦")
            
            # Calculate total command count (prefix + slash)
            prefix_cmds = data.get("prefix", [])
            slash_cmds = data.get("slash", [])
            cmd_count = len(prefix_cmds) + len(slash_cmds)
            
            options.append(
                discord.SelectOption(
                    label=category,
                    description=f"{cmd_count} command{'s' if cmd_count != 1 else ''}",
                    emoji=emoji,
                    value=category
                )
            )
        
        # Add default home option
        options.insert(0, discord.SelectOption(
            label="Home",
            description="Main help page",
            emoji="🏠",
            value="home"
        ))
        
        super().__init__(
            placeholder="Select a category...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle dropdown selection"""
        selected_value = self.values[0]
        
        if selected_value == "home":
            # Show main help page
            await interaction.response.edit_message(embed=self.help_command.get_main_help_embed())
        else:
            # Show commands for the selected category
            await interaction.response.edit_message(embed=self.help_command.get_category_embed(selected_value))

class HelpView(discord.ui.View):
    """View containing the help dropdown"""
    
    def __init__(self, help_command, categories, *, timeout=180):
        super().__init__(timeout=timeout)
        self.add_item(HelpDropdown(help_command, categories))

class CommandTypeView(discord.ui.View):
    """View for switching between prefix and slash commands"""
    
    def __init__(self, help_command, category, *, timeout=180):
        super().__init__(timeout=timeout)
        self.help_command = help_command
        self.category = category
        self.command_type = "all"  # Default to showing all commands
    
    @discord.ui.button(label="All Commands", style=discord.ButtonStyle.primary)
    async def all_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.command_type = "all"
        await interaction.response.edit_message(embed=self.help_command.get_category_embed(self.category, self.command_type))
    
    @discord.ui.button(label="Prefix Commands", style=discord.ButtonStyle.secondary)
    async def prefix_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.command_type = "prefix"
        await interaction.response.edit_message(embed=self.help_command.get_category_embed(self.category, self.command_type))
    
    @discord.ui.button(label="Slash Commands", style=discord.ButtonStyle.secondary)
    async def slash_commands(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.command_type = "slash"
        await interaction.response.edit_message(embed=self.help_command.get_category_embed(self.category, self.command_type))
    
    @discord.ui.button(label="Back to Categories", style=discord.ButtonStyle.danger)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Go back to category selection
        embed = self.help_command.get_main_help_embed()
        view = HelpView(self.help_command, self.help_command.get_all_categories())
        await interaction.response.edit_message(embed=embed, view=view)

class HelpCog(commands.Cog):
    """Enhanced help command with interactive dropdown menus and slash commands support"""
    
    def __init__(self, bot):
        self.bot = bot
        self.original_help_command = bot.help_command
        bot.help_command = None  # Remove the default help command
        
        # Bot theme color
        self.embed_color = 0x3a9efa
        
        # Command emojis
        self.command_emojis = {
            "lock": "🔒",
            "unlock": "🔓",
            "ban": "🔨",
            "kick": "👢",
            "mute": "🔇",
            "unmute": "🔊",
            "purge": "🧹",
            "warn": "⚠️",
            "slowmode": "🕒",
            "ping": "📶",
            "pinginfo": "📶",
            "serverinfo": "📋",
            "userinfo": "👤",
            "avatar": "🖼️",
            "invite": "📩",
            "search": "🔍",
            "hug": "🤗",
            "slap": "👋",
            "kiss": "💋",
            "dance": "💃",
            "gif": "🎬",
            "spotify": "🎵",
            "track": "🎵",
            "album": "💿",
            "artist": "🎤",
            "playlist": "📜",
            "recommend": "👍",
            "bothelp": "❓",
            "stats": "📊",
            "user": "👤",
            "server": "🌐",
            "roles": "👑"
        }
    
    def cog_unload(self):
        """Reset the original help command when cog is unloaded"""
        self.bot.help_command = self.original_help_command
    
    @commands.command(name="help")
    async def help_command(self, ctx, *, command_name: Optional[str] = None):
        """Shows help for commands and categories"""
        if command_name:
            # Show help for a specific command
            await self.show_command_help(ctx, command_name)
        else:
            # Show main help menu with dropdown
            await self.show_help_menu(ctx)
    
    @app_commands.command(name="help", description="Shows help for all bot commands")
    @app_commands.describe(command_name="Specific command to get help for")
    async def help_slash(self, interaction: discord.Interaction, command_name: Optional[str] = None):
        """Slash command version of help"""
        ctx = await self.bot.get_context(interaction)
        
        if command_name:
            await self.show_command_help(ctx, command_name, interaction=interaction)
        else:
            await self.show_help_menu(ctx, interaction=interaction)
    
    def get_all_categories(self) -> Dict[str, dict]:
        """Get all command categories with both prefix and slash commands"""
        categories = {}
        
        # Gather prefix commands
        for command in self.bot.commands:
            if command.hidden:
                continue
                
            cog_name = command.cog_name or "No Category"
            
            if cog_name not in categories:
                categories[cog_name] = {"prefix": [], "slash": []}
                
            categories[cog_name]["prefix"].append(command)
        
        # Gather slash commands
        for command in self.bot.tree.get_commands():
            # Determine category based on command group or module
            cog_name = getattr(command, "cog_name", None)
            if not cog_name and hasattr(command, "module"):
                # Try to extract cog name from module
                module_parts = command.module.split(".")
                for part in module_parts:
                    if part.lower().endswith("cog"):
                        cog_name = part.replace("_", " ").title()
                        break
            
            cog_name = cog_name or "No Category"
            
            if cog_name not in categories:
                categories[cog_name] = {"prefix": [], "slash": []}
                
            categories[cog_name]["slash"].append(command)
        
        return categories
    
    async def show_help_menu(self, ctx, interaction: Optional[discord.Interaction] = None):
        """Display the main help menu with dropdown"""
        # Get all commands and organize them by category
        categories = self.get_all_categories()
        
        # Create the main help embed
        embed = self.get_main_help_embed()
        
        # Create and send the view with the dropdown
        view = HelpView(self, categories)
        
        if interaction:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, view=view)
            else:
                await interaction.response.send_message(embed=embed, view=view)
        else:
            await ctx.send(embed=embed, view=view)
    
    async def show_command_help(self, ctx, command_name: str, interaction: Optional[discord.Interaction] = None):
        """Show help for a specific command"""
        # First try to find a prefix command
        command = self.bot.get_command(command_name)
        is_slash = False
        
        if not command:
            # Try to find a slash command
            for cmd in self.bot.tree.get_commands():
                if cmd.name == command_name:
                    command = cmd
                    is_slash = True
                    break
        
        if not command:
            message = f"Command `{command_name}` not found."
            if interaction:
                if interaction.response.is_done():
                    await interaction.followup.send(message)
                else:
                    await interaction.response.send_message(message)
            else:
                await ctx.send(message)
            return
        
        # For prefix commands, check if user can run it
        if not is_slash and hasattr(command, "can_run"):
            try:
                if not await command.can_run(ctx):
                    message = f"You don't have permission to use `{command_name}`."
                    if interaction:
                        if interaction.response.is_done():
                            await interaction.followup.send(message)
                        else:
                            await interaction.response.send_message(message)
                    else:
                        await ctx.send(message)
                    return
            except Exception:
                # If can_run raises an exception, we'll just show the help anyway
                pass
        
        # Create an embed for the command
        emoji = self.get_command_emoji(command.name)
        title = f"{emoji} {'Slash' if is_slash else 'Prefix'} Command: {command.name}"
        
        # Get description
        if is_slash:
            description = command.description or "No description available."
        else:
            description = command.help or "No description available."
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=self.embed_color
        )
        
        # Add usage information
        if is_slash:
            usage = f"/{command.name}"
            if hasattr(command, "parameters") and command.parameters:
                params = []
                for param in command.parameters:
                    if param.required:
                        params.append(f"<{param.name}>")
                    else:
                        params.append(f"[{param.name}]")
                if params:
                    usage += " " + " ".join(params)
            
            embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
        else:
            signature = self.get_command_signature(command)
            embed.add_field(name="Usage", value=f"`{ctx.prefix}{command.name} {signature}`", inline=False)
        
        # Add aliases for prefix commands
        if not is_slash and hasattr(command, "aliases") and command.aliases:
            aliases = ", ".join(f"`{ctx.prefix}{alias}`" for alias in command.aliases)
            embed.add_field(name="Aliases", value=aliases, inline=False)
        
        # Add cooldown information for prefix commands
        if not is_slash and hasattr(command, "_buckets") and command._buckets and command._buckets._cooldown:
            cooldown = command._buckets._cooldown
            embed.add_field(
                name="Cooldown",
                value=f"{cooldown.rate} use{'s' if cooldown.rate != 1 else ''} every {cooldown.per:.0f} seconds",
                inline=False
            )
        
        # Add subcommands for prefix commands if any
        if not is_slash and hasattr(command, "commands") and command.commands:
            subcommands = ", ".join(f"`{ctx.prefix}{command.name} {subcommand.name}`" for subcommand in command.commands)
            if subcommands:
                embed.add_field(name="Subcommands", value=subcommands, inline=False)
        
        # Add subcommands for slash commands if any
        if is_slash and hasattr(command, "options"):
            subcommands = []
            for option in command.options:
                if option.type == discord.AppCommandOptionType.subcommand:
                    subcommands.append(f"`/{command.name} {option.name}`")
            
            if subcommands:
                embed.add_field(name="Subcommands", value=", ".join(subcommands), inline=False)
        
        # Add cog/category information
        cog_name = getattr(command, "cog_name", None)
        if cog_name:
            embed.set_footer(text=f"Category: {cog_name}")
        
        # Send the embed
        if interaction:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed)
            else:
                await interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)
    
    def get_main_help_embed(self) -> discord.Embed:
        """Create the main help embed"""
        embed = discord.Embed(
            title=f"{self.bot.user.name} Help",
            description=(
                f"Use the dropdown menu below to navigate through command categories.\n\n"
                f"• You can use both **prefix commands** (`{self.bot.command_prefix}command`) and **slash commands** (`/command`)\n"
                f"• For detailed help: `{self.bot.command_prefix}help [command]` or `/help command`\n"
                f"• Example: `{self.bot.command_prefix}help ping` or `/help ping`\n\n"
                f"**Key Features:**\n"
                f"• Moderation commands to manage your server\n"
                f"• Anti-spam protection to keep your channels clean\n"
                f"• Logging system to track server events\n"
                f"• Fun commands and GIFs for entertainment\n"
                f"• Music integration with Spotify\n"
                f"• Google Search and image search\n"
                f"• And much more!"
            ),
            color=self.embed_color,
            timestamp=datetime.datetime.utcnow()
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Select a category from the dropdown menu • Version {getattr(self.bot, 'version', '2.0.0')}")
        
        return embed
    
    def get_category_embed(self, category: str, command_type: str = "all") -> discord.Embed:
        """Create an embed for a specific command category
        
        Parameters:
        -----------
        category: str
            The category name
        command_type: str
            Which commands to show: "all", "prefix", or "slash"
        """
        # Get all categories
        all_categories = self.get_all_categories()
        
        # Get commands in the category
        if category not in all_categories:
            return discord.Embed(
                title="Category Not Found",
                description=f"Category `{category}` not found.",
                color=discord.Color.red()
            )
        
        category_data = all_categories[category]
        prefix_commands = category_data["prefix"]
        slash_commands = category_data["slash"]
        
        # Create embed
        embed = discord.Embed(
            title=f"{category} Commands",
            description=f"Here are the {'prefix and slash' if command_type == 'all' else command_type} commands in the {category} category:",
            color=self.embed_color,
            timestamp=datetime.datetime.utcnow()
        )
        
        # Add command fields based on command_type
        if command_type in ["all", "prefix"] and prefix_commands:
            embed.add_field(
                name="📝 Prefix Commands",
                value="These commands can be used with the prefix `" + str(self.bot.command_prefix) + "`",
                inline=False
            )
            
            for command in sorted(prefix_commands, key=lambda x: x.name):
                emoji = self.get_command_emoji(command.name)
                name = f"{emoji} {command.name}"
                
                # Get brief description or the first line of the full help
                description = command.brief or (command.help.split("\n")[0] if command.help else "No description")
                
                embed.add_field(name=name, value=description, inline=False)
        
        if command_type in ["all", "slash"] and slash_commands:
            embed.add_field(
                name="/ Slash Commands",
                value="These commands can be used with Discord's slash command interface",
                inline=False
            )
            
            for command in sorted(slash_commands, key=lambda x: x.name):
                emoji = self.get_command_emoji(command.name)
                name = f"{emoji} {command.name}"
                
                # Get description
                description = command.description or "No description available."
                
                embed.add_field(name=name, value=description, inline=False)
        
        if (command_type in ["all", "prefix"] and not prefix_commands) and (command_type in ["all", "slash"] and not slash_commands):
            embed.add_field(name="No Commands", value="This category has no available commands.")
        elif command_type == "prefix" and not prefix_commands:
            embed.add_field(name="No Prefix Commands", value="This category has no prefix commands.")
        elif command_type == "slash" and not slash_commands:
            embed.add_field(name="No Slash Commands", value="This category has no slash commands.")
        
        # Set footer with command type info
        if command_type == "all":
            footer_text = "Showing all commands • "
        elif command_type == "prefix":
            footer_text = f"Showing only prefix commands ({self.bot.command_prefix}) • "
        else:  # slash
            footer_text = "Showing only slash commands (/) • "
            
        embed.set_footer(text=footer_text + f"Use {self.bot.command_prefix}help [command] for more details")
        
        return embed
    
    def get_command_signature(self, command: commands.Command) -> str:
        """Get the command signature (parameters)"""
        if not command.signature:
            return ""
        
        return command.signature
    
    def get_command_emoji(self, command_name: str) -> str:
        """Get an emoji for a command"""
        return self.command_emojis.get(command_name.lower(), "🔹")

async def setup(bot):
    # Add the cog
    help_cog = HelpCog(bot)
    await bot.add_cog(help_cog)
    
    # Register slash commands
    bot.tree.add_command(help_cog.help_slash)
