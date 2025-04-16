import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os

class MusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}
        self.queue = {}
        self.spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=os.getenv("SPOTIFY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
        ))

    async def ensure_vc(self, interaction: discord.Interaction):
        user = interaction.user
        if user.voice is None:
            await interaction.response.send_message("❌ You're not in a voice channel.", ephemeral=True)
            return None

        vc = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        if vc and vc.is_connected():
            return vc

        vc = await user.voice.channel.connect()
        self.voice_clients[interaction.guild.id] = vc
        return vc

    async def extract_audio(self, query):
        ytdl_opts = {
            "format": "bestaudio[ext=webm][acodec=opus]/bestaudio",
            "noplaylist": True,
            "quiet": True,
            "default_search": "ytsearch",
            "skip_download": True,
        }
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
            if "entries" in info:
                info = info["entries"][0]
            return info["url"], info.get("title", "Unknown Title")

    async def play_next(self, guild_id):
        if self.queue[guild_id]:
            vc = self.voice_clients.get(guild_id)
            if not vc:
                return

            url, title = self.queue[guild_id].pop(0)
            source = await discord.FFmpegOpusAudio.from_probe(
                url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn"
            )

            def after_play(e):
                fut = self.play_next(guild_id)
                asyncio.run_coroutine_threadsafe(fut, self.bot.loop)

            vc.play(source, after=after_play)

    def create_button_view(self):
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.grey, label="Pause", custom_id="pause"))
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.blurple, label="Skip", custom_id="skip"))
        view.add_item(discord.ui.Button(style=discord.ButtonStyle.red, label="Stop", custom_id="stop"))
        return view

    @app_commands.command(name="spotiplay", description="Play a Spotify track by URL or name")
    @app_commands.describe(query="Spotify song name or Spotify URL")
    async def spotiplay(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        guild_id = interaction.guild.id

        vc = await self.ensure_vc(interaction)
        if not vc:
            return

        # Use Spotify API to get track info
        try:
            if "open.spotify.com" in query:
                track_id = query.split("track/")[1].split("?")[0]
                track = self.spotify.track(track_id)
            else:
                result = self.spotify.search(q=query, type="track", limit=1)
                track = result["tracks"]["items"][0]
        except Exception as e:
            await interaction.followup.send(f"❌ Spotify lookup failed: {e}")
            return

        title = track["name"] + " - " + track["artists"][0]["name"]
        url, yt_title = await self.extract_audio(title)

        if guild_id not in self.queue:
            self.queue[guild_id] = []

        self.queue[guild_id].append((url, yt_title))

        if not vc.is_playing():
            await self.play_next(guild_id)

        embed = discord.Embed(title="🎶 Now playing from Spotify", description=f"**{title}**", color=0x1DB954)
        await interaction.followup.send(embed=embed, view=self.create_button_view())

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not interaction.type == discord.InteractionType.component:
            return

        guild_id = interaction.guild.id
        vc = self.voice_clients.get(guild_id)

        if not vc:
            await interaction.response.send_message("⚠ Bot not in a voice channel.", ephemeral=True)
            return

        match interaction.data["custom_id"]:
            case "pause":
                if vc.is_playing():
                    vc.pause()
                    await interaction.response.send_message("⏸ Paused", ephemeral=True)
                elif vc.is_paused():
                    vc.resume()
                    await interaction.response.send_message("▶ Resumed", ephemeral=True)
                else:
                    await interaction.response.send_message("⚠ Nothing to pause/resume.", ephemeral=True)

            case "skip":
                if vc.is_playing():
                    vc.stop()
                    await interaction.response.send_message("⏭ Skipped", ephemeral=True)
                else:
                    await interaction.response.send_message("⚠ Nothing to skip.", ephemeral=True)

            case "stop":
                if vc.is_connected():
                    await vc.disconnect()
                    self.queue[guild_id] = []
                    await interaction.response.send_message("🛑 Stopped and left VC.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MusicPlayer(bot))
