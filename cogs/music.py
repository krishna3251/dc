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

    # Song result cache to prevent repeated searches
    song_cache = {}
    
    def search_song(self, query):
        # Check cache first
        if query in self.song_cache:
            return self.song_cache[query]
            
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "extract_flat": True,  # Faster extraction
            "default_search": "ytsearch1",  # Only get the top result for faster search
            "ignoreerrors": True,
            "age_limit": 50,
            "cachedir": False,  # Disable cache for speed
            # Add more optimizations
            "skip_download": True,
            "no_warnings": True,
            "no_color": True,
            "geo_bypass": True,  # Bypass geo-restrictions where possible
            "socket_timeout": 3,  # Short timeout for faster failure
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                
                # Process results
                if "entries" in info and info["entries"]:
                    entry = info["entries"][0]
                    # For search results, we need to get the full info
                    if "_type" in entry and entry["_type"] == "url":
                        # This is just a URL, get the full info
                        full_info = ydl.extract_info(entry["url"], download=False)
                        result = (
                            full_info["url"], 
                            full_info["title"], 
                            full_info.get("duration", 0), 
                            full_info.get("thumbnail", None)
                        )
                    else:
                        # Direct result
                        result = (
                            entry["url"], 
                            entry["title"], 
                            entry.get("duration", 0), 
                            entry.get("thumbnail", None)
                        )
                elif "url" in info:
                    # Direct URL input
                    result = (
                        info["url"], 
                        info["title"], 
                        info.get("duration", 0), 
                        info.get("thumbnail", None)
                    )
                else:
                    result = (None, None, None, None)
                    
                # Cache the result (only if successful)
                if result[0]:
                    self.song_cache[query] = result
                    
                    # Limit cache size to prevent memory issues
                    if len(self.song_cache) > 100:
                        # Remove oldest entry
                        self.song_cache.pop(next(iter(self.song_cache)))
                        
                return result
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
        """Optimized play_song function with better error handling and latency reduction"""
        vc = await self.ensure_voice(ctx)
        if not vc:
            return

        # Send "processing" message to give immediate feedback
        processing_msg = await ctx.send("🔄 Processing audio stream...")
        
        # Optimized FFmpeg options for faster audio processing and lower latency
        FFMPEG_OPTIONS = {
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 2 -analyzeduration 512K -probesize 512K -thread_queue_size 4096",
            "options": "-vn -af loudnorm=I=-16:LRA=11:TP=-1.5 -b:a 128k -bufsize 128k"  # Normalize audio and use lower bitrate for consistent playback
        }
        
        try:
            # Create audio source
            source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
            
            # Add volume control if guild has volume setting
            if ctx.guild.id in self.volume:
                source = discord.PCMVolumeTransformer(source, volume=self.volume[ctx.guild.id])
            else:
                source = discord.PCMVolumeTransformer(source, volume=1.0)  # Default volume
                self.volume[ctx.guild.id] = 1.0
            
            # Play the audio with a callback function
            vc.play(
                source, 
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(ctx), 
                    self.bot.loop
                ).result() if e is None else print(f"Player error: {e}")
            )
            
            # Create rich embed for now playing
            embed = Embed(title="🎶 Now Playing", description=f"[{title}]({url})", color=0xFFA500)
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            
            # Format duration
            minutes = duration // 60
            seconds = duration % 60
            embed.set_footer(text=f"Duration: {minutes}:{seconds:02d}")
            
            # Delete processing message and send now playing
            await processing_msg.delete()
            await ctx.send(embed=embed, view=MusicView(ctx, self))
            
        except Exception as e:
            await processing_msg.delete()
            await ctx.send(f"❌ Error playing song: {e}")
            print(f"Music playback error: {e}")
            
            # Try to play next song if available
            if ctx.guild.id in self.song_queue and self.song_queue[ctx.guild.id]:
                await asyncio.sleep(1)  # Wait a bit before trying next
                await self.play_next(ctx)

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

    @commands.command(name="queue", help="Shows the current music queue")
    async def queue(self, ctx):
        if isinstance(ctx, discord.Interaction):
            # Handle interaction from button
            interaction = ctx
            ctx = interaction.message.channel  # Get the channel from interaction
            
        if ctx.guild.id not in self.song_queue or not self.song_queue[ctx.guild.id]:
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message("❌ The queue is empty!", ephemeral=True)
            else:
                await ctx.send("❌ The queue is empty!")
            return
            
        embed = discord.Embed(title="🎵 Music Queue", color=discord.Color.blue())
        
        # Add currently playing song
        if ctx.guild.id in self.current_song:
            title, duration, thumbnail = self.current_song[ctx.guild.id]
            embed.add_field(name="🎧 Now Playing", value=f"{title} ({duration // 60}:{duration % 60:02d})", inline=False)
            embed.set_thumbnail(url=thumbnail)
        
        # Add queued songs
        for i, (_, title, duration, _) in enumerate(self.song_queue[ctx.guild.id], 1):
            embed.add_field(name=f"#{i} in Queue", value=f"{title} ({duration // 60}:{duration % 60:02d})", inline=False)
        
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            await ctx.send(embed=embed)

    @commands.command(name="skip", help="Skips the current song")
    async def skip(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.stop()  # This will trigger the after function that plays the next song
            await ctx.send("⏭️ Skipped song.")
        else:
            await ctx.send("❌ Not playing any music right now.")

    @commands.command(name="stop", help="Stops playing music and clears the queue")
    async def stop(self, ctx):
        vc = ctx.voice_client
        if vc:
            if ctx.guild.id in self.song_queue:
                self.song_queue[ctx.guild.id] = []
            await vc.disconnect()
            await ctx.send("⏹️ Music stopped and queue cleared.")
        else:
            await ctx.send("❌ Not connected to a voice channel.")
    
    @commands.command(name="volume", help="Adjusts the volume of the music (1-100)")
    async def volume(self, ctx, volume: int):
        if volume < 1 or volume > 100:
            await ctx.send("❌ Volume must be between 1 and 100")
            return
            
        vc = ctx.voice_client
        if vc:
            # Convert volume to a scale of 0.0 to 2.0 (discord.py's FFmpegPCMAudio range)
            # 50 = normal volume (1.0)
            volume_float = volume / 50.0
            
            # Store the volume for this guild
            self.volume[ctx.guild.id] = volume_float
            
            if vc.source:
                vc.source.volume = volume_float
                
            await ctx.send(f"🔊 Volume set to {volume}%")
        else:
            await ctx.send("❌ Not connected to a voice channel.")

async def setup(bot):
    await bot.add_cog(Music(bot))
    print("✅ Music cog loaded!")
