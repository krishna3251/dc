import discord
from discord.ext import commands
import wavelink
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

load_dotenv()

# Set up Spotify API
discord.utils.setup_logging()

sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
    scope="user-read-playback-state user-modify-playback-state"
))

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.loop.create_task(self.start_nodes())

    async def start_nodes(self):
        await self.bot.wait_until_ready()
        await wavelink.NodePool.create_node(
            bot=self.bot,
            host='localhost',
            port=2333,
            password='youshallnotpass',
            https=False
        )

    @commands.command()
    async def play(self, ctx, *, query: str):
        vc: wavelink.Player = ctx.voice_client
        if not vc:
            vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)

        if 'open.spotify.com' in query:
            # Handle Spotify links
            if 'track' in query:
                track_id = query.split('/')[-1].split('?')[0]
                track = sp.track(track_id)
                search = f"{track['name']} {track['artists'][0]['name']}"
            elif 'playlist' in query:
                playlist_id = query.split('/')[-1].split('?')[0]
                playlist = sp.playlist(playlist_id)
                tracks = [
                    f"{item['track']['name']} {item['track']['artists'][0]['name']}"
                    for item in playlist['tracks']['items']
                ]
                for search in tracks:
                    yt_tracks = await wavelink.YouTubeTrack.search(search)
                    await vc.queue.put_wait(yt_tracks[0])
                await ctx.send(f"Added {len(tracks)} Spotify playlist tracks to the queue.")
                if not vc.is_playing():
                    await vc.play(vc.queue.get())
                return
            else:
                await ctx.send("Unsupported Spotify URL.")
                return
        else:
            search = query

        yt_tracks = await wavelink.YouTubeTrack.search(search)
        if not yt_tracks:
            await ctx.send("No results found.")
            return

        track = yt_tracks[0]
        await vc.queue.put_wait(track)

        if not vc.is_playing():
            await vc.play(vc.queue.get())
        await ctx.send(f"Now playing: {track.title}")

    @commands.command()
    async def skip(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.is_playing():
            await vc.stop()
            await ctx.send("Skipped current track.")

    @commands.command()
    async def stop(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc:
            await vc.disconnect()
            await ctx.send("Stopped music and disconnected.")

    @commands.command()
    async def pause(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.is_playing():
            await vc.pause()
            await ctx.send("Paused.")

    @commands.command()
    async def resume(self, ctx):
        vc: wavelink.Player = ctx.voice_client
        if vc and vc.is_paused():
            await vc.resume()
            await ctx.send("Resumed.")

async def setup(bot):
    await bot.add_cog(Music(bot))
