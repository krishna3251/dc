
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
        node = wavelink.Node(
            uri='http://localhost:2333',
            password='youshallnotpass'
        )
        await wavelink.Pool.connect(nodes=[node], client=self.bot)

    @commands.command()
    async def play(self, ctx, *, query: str):
        if not ctx.voice_client:
            vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc = ctx.voice_client

        if 'open.spotify.com' in query:
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
                    track = await wavelink.YouTubeTrack.search(search)
                    await vc.queue.put_wait(track[0])
                await ctx.send(f"Added {len(tracks)} Spotify playlist tracks to the queue.")
                if not vc.is_playing():
                    await vc.play(await vc.queue.get_wait())
                return
            else:
                await ctx.send("Unsupported Spotify URL.")
                return
        else:
            search = query

        tracks = await wavelink.YouTubeTrack.search(search)
        if not tracks:
            await ctx.send("No results found.")
            return

        track = tracks[0]
        await vc.queue.put_wait(track)

        if not vc.is_playing():
            await vc.play(await vc.queue.get_wait())
        await ctx.send(f"Now playing: {track.title}")

    @commands.command()
    async def skip(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            await vc.stop()
            await ctx.send("Skipped current track.")

    @commands.command()
    async def stop(self, ctx):
        vc = ctx.voice_client
        if vc:
            await vc.disconnect()
            await ctx.send("Stopped music and disconnected.")

    @commands.command()
    async def pause(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            await vc.pause()
            await ctx.send("Paused.")

    @commands.command()
    async def resume(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_paused():
            await vc.resume()
            await ctx.send("Resumed.")

async def setup(bot):
    await bot.add_cog(Music(bot))
