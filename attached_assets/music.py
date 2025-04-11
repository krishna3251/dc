import discord
import yt_dlp
import asyncio
from discord.ext import commands
from discord import Embed, FFmpegPCMAudio, ui

class MusicView(ui.View):
    def __init__(self, ctx, music_cog):
        super().__init__()
        self.ctx = ctx
        self.music_cog = music_cog

    @ui.button(label="⏸ Pause", style=discord.ButtonStyle.primary)
    async def pause(self, interaction: discord.Interaction, button: ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ Music paused.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No music is playing.", ephemeral=True)

    @ui.button(label="▶ Resume", style=discord.ButtonStyle.success)
    async def resume(self, interaction: discord.Interaction, button: ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶ Music resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No music is paused.", ephemeral=True)

    @ui.button(label="⏭ Skip", style=discord.ButtonStyle.danger)
    async def skip(self, interaction: discord.Interaction, button: ui.Button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭ Skipped song.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No music is playing.", ephemeral=True)

    @ui.button(label="⏹ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("⏹ Music stopped and bot left the VC.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bot is not in a voice channel.", ephemeral=True)

    @ui.button(label="📜 Queue", style=discord.ButtonStyle.secondary)
    async def show_queue(self, interaction: discord.Interaction, button: ui.Button):
        await self.music_cog.queue(interaction)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queue = {}  # Stores song queues per guild
        self.current_song = {}  # Tracks the currently playing song
        self.volume = {}  # Stores volume per guild

    async def ensure_voice(self, ctx):
        if ctx.author.voice:
            if ctx.voice_client:
                return ctx.voice_client
            return await ctx.author.voice.channel.connect()
        else:
            await ctx.send("You need to be in a voice channel!")
            return None

    def search_song(self, query):
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "extract_flat": False,
            "default_search": "ytsearch10",  # Faster search
            "ignoreerrors": True,
            "age_limit": 50,
            "cachedir": False,  # Disable cache for speed
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                if "entries" in info and info["entries"]:
                    return info["entries"][0]["url"], info["entries"][0]["title"], info["entries"][0]["duration"], info["entries"][0]["thumbnail"]
                elif "url" in info:
                    return info["url"], info["title"], info["duration"], info.get("thumbnail")
                else:
                    return None, None, None, None
            except Exception as e:
                print(f"Error searching song: {e}")
                return None, None, None, None

    async def play_next(self, ctx):
        if ctx.guild.id in self.song_queue and self.song_queue[ctx.guild.id]:
            url, title, duration, thumbnail = self.song_queue[ctx.guild.id].pop(0)
            self.current_song[ctx.guild.id] = (title, duration, thumbnail)
            await self.play_song(ctx, url, title, duration, thumbnail)
        else:
            await ctx.send("Queue finished. Disconnecting.")
            await ctx.voice_client.disconnect()

    async def play_song(self, ctx, url, title, duration, thumbnail):
        vc = await self.ensure_voice(ctx)
        if not vc:
            return

        FFMPEG_OPTIONS = {
            "executable": "C:/ffmpeg/bin/ffmpeg.exe",
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 -analyzeduration 512K -probesize 512K",
            "options": "-vn"
        }
        try:
            source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
            vc.play(source, after=lambda e: asyncio.create_task(self.play_next(ctx)))
            embed = Embed(title="🎶 Now Playing", description=f"[{title}]({url})", color=0xFFA500)
            embed.set_thumbnail(url=thumbnail)
            embed.set_footer(text=f"Duration: {duration // 60}:{duration % 60:02d}")
            await ctx.send(embed=embed, view=MusicView(ctx, self))
        except Exception as e:
            await ctx.send(f"Error playing song: {e}")
@commands.command(name="play", help="Play music from YouTube")
async def play(self, ctx, *, query: str):
    pass  # Your play function code
@commands.command(name="play", help="Play music from YouTube or Spotify")
async def play(self, ctx, *, query: str):
    vc = await self.ensure_voice(ctx)
    if not vc:
        return

    url, title, duration, thumbnail = self.search_song(query)
    if not url:
        await ctx.send("❌ Could not find the song! Try another.")
        return

    if ctx.guild.id not in self.song_queue:
        self.song_queue[ctx.guild.id] = []

    if not vc.is_playing():
        self.current_song[ctx.guild.id] = (title, duration, thumbnail)
        await self.play_song(ctx, url, title, duration, thumbnail)
    else:
        self.song_queue[ctx.guild.id].append((url, title, duration, thumbnail))
        await ctx.send(f"🎶 Added to queue: {title}")


async def setup(bot):
    await bot.add_cog(Music(bot))  # ✅ Correct path
    print(" Music cog loaded!")
