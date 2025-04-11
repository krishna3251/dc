import discord
from discord.ext import commands
import wavelink

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.start_nodes())

    async def start_nodes(self):
        await self.bot.wait_until_ready()
        await wavelink.Pool.connect(
            uri="http://localhost:2333",
            password="youshallnotpass",
            user_id=self.bot.user.id
        )

    @commands.command()
    async def join(self, ctx: commands.Context):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            player: wavelink.Player = await channel.connect(cls=wavelink.Player)
            await ctx.send(f"Connected to {channel.name}!")
        else:
            await ctx.send("You are not connected to a voice channel.")

    @commands.command()
    async def play(self, ctx: commands.Context, *, search: str):
        player: wavelink.Player = wavelink.Pool.get_node().get_player(ctx.guild)
        if not player.is_connected:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect(cls=wavelink.Player)
            else:
                return await ctx.send("You need to be in a voice channel to play music.")

        track = await wavelink.YouTubeTrack.search(search, return_first=True)
        await player.play(track)
        await ctx.send(f"Now playing: {track.title}")

    @commands.command()
    async def stop(self, ctx: commands.Context):
        player: wavelink.Player = wavelink.Pool.get_node().get_player(ctx.guild)
        await player.disconnect()
        await ctx.send("Stopped the music and disconnected.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
