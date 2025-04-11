import discord
from discord.ext import commands

class MassRoleAddCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="massrole", help="Adds a role to all members.")
    @commands.has_permissions(manage_roles=True)
    async def mass_role_add(self, ctx, role: discord.Role):
        for member in ctx.guild.members:
            await member.add_roles(role)
        await ctx.send(f"✅ Role {role.name} added to all members.")

async def setup(bot):
    await bot.add_cog(MassRoleAddCog(bot))