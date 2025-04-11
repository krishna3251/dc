
import discord
from discord.ext import commands
import wavelink

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(self.start_nodes())

    async def start_nodes(self):
        await self.bot.wait_until_ready()
        node = wavelink.Node(
            uri='https://lava-v3.ajieblogs.eu.org:443',
            password='https://dsc.gg/ajidevserver'
        )
        await wavelink.NodePool.connect(client=self.bot, nodes=[node])

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
        if not ctx.voice_client:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect(cls=wavelink.Player)
            else:
                return await ctx.send("You need to be in a voice channel to play music.")

        player: wavelink.Player = ctx.voice_client
        tracks = await wavelink.YouTubeTrack.search(search)

        if not tracks:
            return await ctx.send("No tracks found.")

        track = tracks[0]
        await player.play(track)
        await ctx.send(f"Now playing: {track.title}")

    @commands.command()
    async def stop(self, ctx: commands.Context):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send("Stopped the music and disconnected.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
