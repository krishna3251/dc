import discord
from discord.ext import commands
from discord import app_commands
import os
import aiohttp
import asyncio
import base64
import json
import time
import re
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

class SpotifyView(discord.ui.View):
    """Interactive view for Spotify tracks with buttons"""
    
    def __init__(self, *, timeout: float = 180.0, author_id: int, tracks: List[Dict[str, Any]], 
                 query: str = None, cog=None):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.tracks = tracks
        self.query = query
        self.current_index = 0
        self.cog = cog
        self.total_tracks = len(tracks)
        self.is_playing = False
        self.volume = 100
        self.is_looping = False
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original command author to use the buttons"""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot control this music player.", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self):
        """Disable all buttons when the view times out"""
        for item in self.children:
            item.disabled = True
        
        # Try to update the message with disabled buttons
        try:
            if hasattr(self, 'message'):
                await self.message.edit(view=self)
        except:
            pass
    
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="⏮️", row=0)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show the previous track"""
        if self.total_tracks <= 1:
            await interaction.response.defer()
            return
            
        self.current_index = (self.current_index - 1) % self.total_tracks
        # Reset playing state for new track
        self.is_playing = False
        
        # Reset play/pause button visual state
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label and "Play" in child.label:
                child.emoji = "▶️"
                child.label = "Play/Pause"
                child.style = discord.ButtonStyle.success
                break
                
        await self.update_track(interaction, status_message="⏮️ Previous track")
    
    @discord.ui.button(label="Play/Pause", style=discord.ButtonStyle.success, emoji="▶️", row=0)
    async def play_pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle play/pause state"""
        if not self.tracks:
            await interaction.response.send_message("No tracks available.", ephemeral=True)
            return
        
        self.is_playing = not self.is_playing
        
        if self.is_playing:
            button.emoji = "⏸️"
            button.label = "Pause"
            button.style = discord.ButtonStyle.primary
            status_message = "▶️ Now playing"
        else:
            button.emoji = "▶️" 
            button.label = "Play"
            button.style = discord.ButtonStyle.success
            status_message = "⏸️ Paused"
        
        track = self.tracks[self.current_index]
        
        if self.is_playing:
            # When playing, share the external URL to open in Spotify
            external_url = track.get("external_urls", {}).get("spotify")
            if external_url:
                mini_embed = discord.Embed(
                    title=f"🎵 Play on Spotify: {track.get('name', 'Unknown')}",
                    url=external_url,
                    color=0x1DB954  # Spotify green
                )
                await interaction.response.send_message(embed=mini_embed, ephemeral=True)
        
        # Update the main view
        await self.update_track(interaction, status_message=status_message, response_edit=True)
    
    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji="⏭️", row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show the next track"""
        if self.total_tracks <= 1:
            await interaction.response.defer()
            return
            
        self.current_index = (self.current_index + 1) % self.total_tracks
        # Reset playing state for new track
        self.is_playing = False
        
        # Reset play/pause button visual state
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label and "Play" in child.label:
                child.emoji = "▶️"
                child.label = "Play/Pause"
                child.style = discord.ButtonStyle.success
                break
                
        await self.update_track(interaction, status_message="⏭️ Next track")
    
    @discord.ui.button(label="Loop", style=discord.ButtonStyle.secondary, emoji="🔁", row=0)
    async def loop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle track looping"""
        self.is_looping = not self.is_looping
        
        if self.is_looping:
            button.style = discord.ButtonStyle.success
            status_message = "🔁 Loop enabled"
        else:
            button.style = discord.ButtonStyle.secondary
            status_message = "➡️ Loop disabled"
        
        await self.update_track(interaction, status_message=status_message, response_edit=True)
    
    @discord.ui.button(label="Similar", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def similar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Find similar tracks to the current one"""
        if not self.tracks or not self.cog:
            await interaction.response.send_message("Cannot find similar tracks at this time.", ephemeral=True)
            return
        
        track = self.tracks[self.current_index]
        track_id = track.get("id")
        
        if not track_id:
            await interaction.response.send_message("Cannot find similar tracks for this song.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get recommendations based on this track
        recommendations = await self.cog.get_recommendations(seed_tracks=[track_id])
        
        if not recommendations:
            await interaction.followup.send("Could not find any similar tracks.")
            return
        
        # Create a new view with the recommendations
        new_view = SpotifyView(
            author_id=self.author_id,
            tracks=recommendations,
            query=f"Similar to {track.get('name')}",
            cog=self.cog
        )
        
        first_track = recommendations[0]
        embed = new_view.create_track_embed(first_track, f"Similar to {track.get('name')}")
        
        # Send as a new message
        new_message = await interaction.followup.send(embed=embed, view=new_view)
        new_view.message = await new_message.fetch()
    
    @discord.ui.button(label="Save", style=discord.ButtonStyle.success, emoji="💾", row=1)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Save track to favorites"""
        if not self.tracks or not self.cog:
            await interaction.response.send_message("Cannot save track at this time.", ephemeral=True)
            return
            
        track = self.tracks[self.current_index]
        success = await self.cog.save_favorite_track(
            interaction.user.id, 
            track
        )
        
        if success:
            await interaction.response.send_message("Track saved to your favorites!", ephemeral=True)
        else:
            await interaction.response.send_message("Failed to save track or it's already in your favorites.", ephemeral=True)
    
    @discord.ui.button(label="Share", style=discord.ButtonStyle.primary, emoji="📤", row=1)
    async def share_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Share the current track in the channel (not ephemeral)"""
        if not self.tracks:
            await interaction.response.send_message("No track to share.", ephemeral=True)
            return
        
        track = self.tracks[self.current_index]
        embed = self.create_track_embed(track, f"🎵 {interaction.user.display_name} shared")
        await interaction.response.send_message(embed=embed)
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌", row=1)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the track viewer"""
        for item in self.children:
            item.disabled = True
            
        await interaction.response.edit_message(view=self)
        self.stop()
    
    async def update_track(self, interaction: discord.Interaction, status_message: str = None, response_edit: bool = False):
        """Update the message with the current track"""
        if not self.tracks:
            await interaction.response.send_message("No tracks available.", ephemeral=True)
            return
            
        track = self.tracks[self.current_index]
        embed = self.create_track_embed(track, self.query, status_message)
        
        # Always use edit_message since both paths are the same
        await interaction.response.edit_message(embed=embed, view=self)
    
    def create_track_embed(self, track: Dict[str, Any], title_prefix: str = None, status_message: str = None) -> discord.Embed:
        """Create an embed for a Spotify track"""
        track_name = track.get("name", "Unknown Track")
        artist_names = ", ".join([artist.get("name", "Unknown Artist") for artist in track.get("artists", [])])
        album_name = track.get("album", {}).get("name", "Unknown Album")
        external_url = track.get("external_urls", {}).get("spotify", "")
        preview_url = track.get("preview_url")
        duration_ms = track.get("duration_ms", 0)
        duration_formatted = self.format_duration(duration_ms)
        
        # Create embed
        embed = discord.Embed(
            title=track_name,
            url=external_url,
            color=0x1DB954,  # Spotify green
            timestamp=datetime.utcnow()
        )
        
        # Add status message at the top if provided
        if status_message:
            embed.description = f"**{status_message}**"
        
        # Add title prefix or override with status info
        if title_prefix:
            embed.set_author(name=title_prefix)
        
        # Set album image as thumbnail
        album_images = track.get("album", {}).get("images", [])
        if album_images:
            embed.set_thumbnail(url=album_images[0].get("url"))
        
        # Add track info
        embed.add_field(name="Artist", value=artist_names, inline=True)
        embed.add_field(name="Album", value=album_name, inline=True)
        embed.add_field(name="Duration", value=duration_formatted, inline=True)
        
        # Add preview link if available
        if preview_url:
            embed.add_field(name="Preview", value=f"[Listen to preview]({preview_url})", inline=True)
        
        # Add popularity if available
        popularity = track.get("popularity")
        if popularity is not None:
            popularity_bar = self.create_progress_bar(popularity, 100, 10)
            embed.add_field(name="Popularity", value=f"{popularity}/100 {popularity_bar}", inline=True)
        
        # Add player status if we're playing
        if hasattr(self, 'is_playing') and self.is_playing:
            # Create a playback progress simulation
            # This is just visual - doesn't actually track real playback position
            progress = 30  # Simulate 30% through the track
            progress_bar = self.create_progress_bar(progress, 100, 15)
            embed.add_field(
                name="Playback",
                value=f"{progress_bar}\n{self.format_duration(duration_ms * progress // 100)} / {duration_formatted}",
                inline=False
            )
        
        # Add external link
        if external_url:
            embed.add_field(name="Open in Spotify", value=f"[Click here]({external_url})", inline=True)
            
        # Add footer
        if self.total_tracks > 1:
            embed.set_footer(text=f"Track {self.current_index + 1}/{self.total_tracks}")
        elif hasattr(self, 'is_looping') and self.is_looping:
            embed.set_footer(text="🔁 Loop enabled")
        
        return embed
    
    def format_duration(self, duration_ms: int) -> str:
        """Format milliseconds into mm:ss format"""
        total_seconds = duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Create a text-based progress bar"""
        filled_length = int(length * current / total)
        bar = "█" * filled_length + "░" * (length - filled_length)
        return bar
    
# Removed duplicate method - combined with the enhanced version above

class AlbumView(discord.ui.View):
    """Interactive view for Spotify albums with buttons"""
    
    def __init__(self, *, timeout: float = 60.0, author_id: int, album: Dict[str, Any], tracks: List[Dict[str, Any]], cog=None):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.album = album
        self.tracks = tracks
        self.cog = cog
        self.current_track_index = 0
        self.total_tracks = len(tracks)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original command author to use the buttons"""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot control this album navigation.", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self):
        """Disable all buttons when the view times out"""
        for item in self.children:
            item.disabled = True
        
        # Try to update the message with disabled buttons
        try:
            if hasattr(self, 'message'):
                await self.message.edit(view=self)
        except:
            pass
    
    @discord.ui.button(label="Previous Track", style=discord.ButtonStyle.primary, emoji="⬅️")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show the previous track in the album"""
        if self.total_tracks <= 1:
            await interaction.response.defer()
            return
            
        self.current_track_index = (self.current_track_index - 1) % self.total_tracks
        await self.update_track(interaction)
    
    @discord.ui.button(label="Play Album", style=discord.ButtonStyle.success, emoji="▶️")
    async def play_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send the album link to play"""
        external_url = self.album.get("external_urls", {}).get("spotify")
        
        if external_url:
            embed = discord.Embed(
                title=f"Play on Spotify: {self.album.get('name')}",
                description=f"Open this link to play the album on Spotify",
                url=external_url,
                color=0x1DB954,  # Spotify green
                timestamp=datetime.utcnow()
            )
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No play link available for this album.", ephemeral=True)
    
    @discord.ui.button(label="Next Track", style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show the next track in the album"""
        if self.total_tracks <= 1:
            await interaction.response.defer()
            return
            
        self.current_track_index = (self.current_track_index + 1) % self.total_tracks
        await self.update_track(interaction)
    
    @discord.ui.button(label="View Track", style=discord.ButtonStyle.secondary, emoji="🔍", row=1)
    async def view_track_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View the current track in detail"""
        if not self.tracks or not self.cog:
            await interaction.response.send_message("Cannot view track details at this time.", ephemeral=True)
            return
        
        track = self.tracks[self.current_track_index]
        track_id = track.get("id")
        
        if not track_id:
            await interaction.response.send_message("Cannot view details for this track.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get full track details
        full_track = await self.cog.get_track(track_id)
        
        if not full_track:
            await interaction.followup.send("Could not retrieve track details.")
            return
        
        # Create a new view with just this track
        new_view = SpotifyView(
            author_id=self.author_id,
            tracks=[full_track],
            query=f"From album: {self.album.get('name')}",
            cog=self.cog
        )
        
        embed = new_view.create_track_embed(full_track, f"From album: {self.album.get('name')}")
        
        # Send as a new message
        new_message = await interaction.followup.send(embed=embed, view=new_view)
        new_view.message = await new_message.fetch()
    
    @discord.ui.button(label="Save Album", style=discord.ButtonStyle.success, emoji="💾", row=1)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Save album to favorites"""
        if not self.cog:
            await interaction.response.send_message("Cannot save album at this time.", ephemeral=True)
            return
            
        success = await self.cog.save_favorite_album(
            interaction.user.id, 
            self.album
        )
        
        if success:
            await interaction.response.send_message("Album saved to your favorites!", ephemeral=True)
        else:
            await interaction.response.send_message("Failed to save album or it's already in your favorites.", ephemeral=True)
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌", row=1)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the album viewer"""
        for item in self.children:
            item.disabled = True
            
        await interaction.response.edit_message(view=self)
        self.stop()
    
    def create_album_embed(self) -> discord.Embed:
        """Create an embed for the album"""
        album_name = self.album.get("name", "Unknown Album")
        artist_names = ", ".join([artist.get("name", "Unknown Artist") for artist in self.album.get("artists", [])])
        release_date = self.album.get("release_date", "Unknown")
        external_url = self.album.get("external_urls", {}).get("spotify", "")
        total_tracks = self.album.get("total_tracks", 0)
        
        # Create embed
        embed = discord.Embed(
            title=album_name,
            url=external_url,
            color=0x1DB954,  # Spotify green
            timestamp=datetime.utcnow()
        )
        
        # Set album image
        album_images = self.album.get("images", [])
        if album_images:
            embed.set_image(url=album_images[0].get("url"))
        
        # Add album info
        embed.add_field(name="Artist", value=artist_names, inline=True)
        embed.add_field(name="Release Date", value=release_date, inline=True)
        embed.add_field(name="Total Tracks", value=str(total_tracks), inline=True)
        
        # Add album type if available
        album_type = self.album.get("album_type")
        if album_type:
            embed.add_field(name="Type", value=album_type.capitalize(), inline=True)
        
        # Add external link
        if external_url:
            embed.add_field(name="Open in Spotify", value=f"[Click here]({external_url})", inline=True)
        
        # Add current track info
        if self.tracks and self.current_track_index < len(self.tracks):
            current_track = self.tracks[self.current_track_index]
            track_name = current_track.get("name", "Unknown Track")
            track_number = current_track.get("track_number", 0)
            duration_ms = current_track.get("duration_ms", 0)
            duration_formatted = self.format_duration(duration_ms)
            
            embed.add_field(
                name="Current Track",
                value=f"#{track_number}: {track_name} ({duration_formatted})",
                inline=False
            )
            
            # Add track progress indicator
            if self.total_tracks > 1:
                progress_bar = self.create_progress_bar(self.current_track_index + 1, self.total_tracks, 20)
                embed.add_field(
                    name="Track Progress",
                    value=f"{progress_bar}\nTrack {self.current_track_index + 1}/{self.total_tracks}",
                    inline=False
                )
        
        return embed
    
    def format_duration(self, duration_ms: int) -> str:
        """Format milliseconds into mm:ss format"""
        total_seconds = duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Create a text-based progress bar"""
        filled_length = int(length * current / total)
        bar = "█" * filled_length + "░" * (length - filled_length)
        return bar
    
    async def update_track(self, interaction: discord.Interaction):
        """Update the message with the current track in the album"""
        embed = self.create_album_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class PlaylistView(discord.ui.View):
    """Interactive view for Spotify playlists with buttons"""
    
    def __init__(self, *, timeout: float = 60.0, author_id: int, playlist: Dict[str, Any], tracks: List[Dict[str, Any]], cog=None):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.playlist = playlist
        self.tracks = tracks
        self.cog = cog
        self.current_track_index = 0
        self.total_tracks = len(tracks)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Only allow the original command author to use the buttons"""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot control this playlist navigation.", ephemeral=True)
            return False
        return True
    
    async def on_timeout(self):
        """Disable all buttons when the view times out"""
        for item in self.children:
            item.disabled = True
        
        # Try to update the message with disabled buttons
        try:
            if hasattr(self, 'message'):
                await self.message.edit(view=self)
        except:
            pass
    
    @discord.ui.button(label="Previous Track", style=discord.ButtonStyle.primary, emoji="⬅️")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show the previous track in the playlist"""
        if self.total_tracks <= 1:
            await interaction.response.defer()
            return
            
        self.current_track_index = (self.current_track_index - 1) % self.total_tracks
        await self.update_track(interaction)
    
    @discord.ui.button(label="Play Playlist", style=discord.ButtonStyle.success, emoji="▶️")
    async def play_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Send the playlist link to play"""
        external_url = self.playlist.get("external_urls", {}).get("spotify")
        
        if external_url:
            embed = discord.Embed(
                title=f"Play on Spotify: {self.playlist.get('name')}",
                description=f"Open this link to play the playlist on Spotify",
                url=external_url,
                color=0x1DB954,  # Spotify green
                timestamp=datetime.utcnow()
            )
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("No play link available for this playlist.", ephemeral=True)
    
    @discord.ui.button(label="Next Track", style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show the next track in the playlist"""
        if self.total_tracks <= 1:
            await interaction.response.defer()
            return
            
        self.current_track_index = (self.current_track_index + 1) % self.total_tracks
        await self.update_track(interaction)
    
    @discord.ui.button(label="View Track", style=discord.ButtonStyle.secondary, emoji="🔍", row=1)
    async def view_track_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View the current track in detail"""
        if not self.tracks or not self.cog:
            await interaction.response.send_message("Cannot view track details at this time.", ephemeral=True)
            return
        
        track_item = self.tracks[self.current_track_index]
        track = track_item.get("track", {})
        track_id = track.get("id")
        
        if not track_id:
            await interaction.response.send_message("Cannot view details for this track.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get full track details
        full_track = await self.cog.get_track(track_id)
        
        if not full_track:
            await interaction.followup.send("Could not retrieve track details.")
            return
        
        # Create a new view with just this track
        new_view = SpotifyView(
            author_id=self.author_id,
            tracks=[full_track],
            query=f"From playlist: {self.playlist.get('name')}",
            cog=self.cog
        )
        
        embed = new_view.create_track_embed(full_track, f"From playlist: {self.playlist.get('name')}")
        
        # Send as a new message
        new_message = await interaction.followup.send(embed=embed, view=new_view)
        new_view.message = await new_message.fetch()
    
    @discord.ui.button(label="Follow Playlist", style=discord.ButtonStyle.success, emoji="✅", row=1)
    async def follow_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Follow the playlist"""
        if not self.cog:
            await interaction.response.send_message("Cannot follow playlist at this time.", ephemeral=True)
            return
            
        success = await self.cog.save_favorite_playlist(
            interaction.user.id, 
            self.playlist
        )
        
        if success:
            await interaction.response.send_message("Playlist saved to your favorites!", ephemeral=True)
        else:
            await interaction.response.send_message("Failed to save playlist or it's already in your favorites.", ephemeral=True)
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="❌", row=1)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the playlist viewer"""
        for item in self.children:
            item.disabled = True
            
        await interaction.response.edit_message(view=self)
        self.stop()
    
    def create_playlist_embed(self) -> discord.Embed:
        """Create an embed for the playlist"""
        playlist_name = self.playlist.get("name", "Unknown Playlist")
        owner_name = self.playlist.get("owner", {}).get("display_name", "Unknown")
        description = self.playlist.get("description", "No description")
        external_url = self.playlist.get("external_urls", {}).get("spotify", "")
        total_tracks = self.playlist.get("tracks", {}).get("total", 0)
        
        # Create embed
        embed = discord.Embed(
            title=playlist_name,
            url=external_url,
            description=description,
            color=0x1DB954,  # Spotify green
            timestamp=datetime.utcnow()
        )
        
        # Set playlist image
        playlist_images = self.playlist.get("images", [])
        if playlist_images:
            embed.set_image(url=playlist_images[0].get("url"))
        
        # Add playlist info
        embed.add_field(name="Created By", value=owner_name, inline=True)
        embed.add_field(name="Total Tracks", value=str(total_tracks), inline=True)
        
        # Add current track info
        if self.tracks and self.current_track_index < len(self.tracks):
            track_item = self.tracks[self.current_track_index]
            track = track_item.get("track", {})
            
            track_name = track.get("name", "Unknown Track")
            artist_names = ", ".join([artist.get("name", "Unknown Artist") for artist in track.get("artists", [])])
            album_name = track.get("album", {}).get("name", "Unknown Album")
            duration_ms = track.get("duration_ms", 0)
            duration_formatted = self.format_duration(duration_ms)
            
            added_at = track_item.get("added_at", "Unknown")
            try:
                # Try to parse the date
                added_datetime = datetime.strptime(added_at, "%Y-%m-%dT%H:%M:%SZ")
                added_timestamp = int(added_datetime.timestamp())
                added_str = f"<t:{added_timestamp}:R>"
            except:
                added_str = added_at
            
            track_info = (
                f"**{track_name}**\n"
                f"By: {artist_names}\n"
                f"Album: {album_name}\n"
                f"Duration: {duration_formatted}\n"
                f"Added: {added_str}"
            )
            
            embed.add_field(
                name=f"Track {self.current_track_index + 1}/{self.total_tracks}",
                value=track_info,
                inline=False
            )
            
            # Add track progress indicator
            if self.total_tracks > 1:
                progress_bar = self.create_progress_bar(self.current_track_index + 1, self.total_tracks, 20)
                embed.add_field(
                    name="Playlist Progress",
                    value=progress_bar,
                    inline=False
                )
        
        # Add external link
        if external_url:
            embed.add_field(name="Open in Spotify", value=f"[Click here]({external_url})", inline=True)
        
        return embed
    
    def format_duration(self, duration_ms: int) -> str:
        """Format milliseconds into mm:ss format"""
        total_seconds = duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """Create a text-based progress bar"""
        filled_length = int(length * current / total)
        bar = "█" * filled_length + "░" * (length - filled_length)
        return bar
    
    async def update_track(self, interaction: discord.Interaction):
        """Update the message with the current track in the playlist"""
        embed = self.create_playlist_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class SpotifyCog(commands.Cog):
    """Interact with Spotify to search and display music information"""
    
    def __init__(self, bot):
        self.bot = bot
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.session = None
        self.token = None
        self.token_expiry = 0
        self.favorites_path = os.path.join("data", "spotify", "favorites.json")
        self.ensure_directories()
        self.favorites = self.load_favorites()
    
    def ensure_directories(self):
        """Ensure required directories exist"""
        os.makedirs(os.path.join("data", "spotify"), exist_ok=True)
    
    def load_favorites(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Load user favorite Spotify items"""
        if not os.path.exists(self.favorites_path):
            return {}
            
        try:
            with open(self.favorites_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading Spotify favorites: {e}")
            return {}
    
    def save_favorites(self):
        """Save user favorite Spotify items"""
        try:
            with open(self.favorites_path, 'w') as f:
                json.dump(self.favorites, f, indent=4)
        except Exception as e:
            print(f"Error saving Spotify favorites: {e}")
    
    async def save_favorite_track(self, user_id: int, track: Dict[str, Any]) -> bool:
        """Save a track to user's favorites"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.favorites:
            self.favorites[user_id_str] = {"tracks": [], "albums": [], "playlists": []}
        
        # Check if track is already in favorites
        track_id = track.get("id")
        if any(saved_track.get("id") == track_id for saved_track in self.favorites[user_id_str]["tracks"]):
            return False
        
        # Add to favorites
        self.favorites[user_id_str]["tracks"].append({
            "id": track_id,
            "name": track.get("name"),
            "artists": [artist.get("name") for artist in track.get("artists", [])],
            "album": track.get("album", {}).get("name"),
            "uri": track.get("uri"),
            "external_urls": track.get("external_urls"),
            "saved_at": datetime.utcnow().isoformat()
        })
        
        # Limit to 50 favorites per category
        if len(self.favorites[user_id_str]["tracks"]) > 50:
            self.favorites[user_id_str]["tracks"] = self.favorites[user_id_str]["tracks"][-50:]
        
        self.save_favorites()
        return True
    
    async def save_favorite_album(self, user_id: int, album: Dict[str, Any]) -> bool:
        """Save an album to user's favorites"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.favorites:
            self.favorites[user_id_str] = {"tracks": [], "albums": [], "playlists": []}
        
        # Check if album is already in favorites
        album_id = album.get("id")
        if any(saved_album.get("id") == album_id for saved_album in self.favorites[user_id_str]["albums"]):
            return False
        
        # Add to favorites
        self.favorites[user_id_str]["albums"].append({
            "id": album_id,
            "name": album.get("name"),
            "artists": [artist.get("name") for artist in album.get("artists", [])],
            "uri": album.get("uri"),
            "external_urls": album.get("external_urls"),
            "saved_at": datetime.utcnow().isoformat()
        })
        
        # Limit to 50 favorites per category
        if len(self.favorites[user_id_str]["albums"]) > 50:
            self.favorites[user_id_str]["albums"] = self.favorites[user_id_str]["albums"][-50:]
        
        self.save_favorites()
        return True
    
    async def save_favorite_playlist(self, user_id: int, playlist: Dict[str, Any]) -> bool:
        """Save a playlist to user's favorites"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.favorites:
            self.favorites[user_id_str] = {"tracks": [], "albums": [], "playlists": []}
        
        # Check if playlist is already in favorites
        playlist_id = playlist.get("id")
        if any(saved_playlist.get("id") == playlist_id for saved_playlist in self.favorites[user_id_str]["playlists"]):
            return False
        
        # Add to favorites
        self.favorites[user_id_str]["playlists"].append({
            "id": playlist_id,
            "name": playlist.get("name"),
            "owner": playlist.get("owner", {}).get("display_name"),
            "uri": playlist.get("uri"),
            "external_urls": playlist.get("external_urls"),
            "saved_at": datetime.utcnow().isoformat()
        })
        
        # Limit to 50 favorites per category
        if len(self.favorites[user_id_str]["playlists"]) > 50:
            self.favorites[user_id_str]["playlists"] = self.favorites[user_id_str]["playlists"][-50:]
        
        self.save_favorites()
        return True
    
    async def cog_load(self):
        self.session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        if self.session:
            await self.session.close()
    
    async def get_access_token(self) -> str:
        """Get a Spotify API access token"""
        # Check if we have a valid token
        if self.token and time.time() < self.token_expiry:
            return self.token
        
        # Otherwise, get a new token
        if not self.client_id or not self.client_secret:
            return None
            
        # Prepare credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        # Prepare request
        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}
        
        try:
            async with self.session.post(url, headers=headers, data=data) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data.get("access_token")
                    # Set expiry time (subtract 60 seconds for safety)
                    expires_in = data.get("expires_in", 3600) - 60
                    self.token_expiry = time.time() + expires_in
                    return self.token
                else:
                    error_data = await response.text()
                    print(f"Spotify API error: {response.status}, {error_data}")
                    return None
        except Exception as e:
            print(f"Error getting Spotify access token: {e}")
            return None
    
    async def make_spotify_request(self, endpoint: str, params: Dict = None, method: str = "GET") -> Dict:
        """Make a request to the Spotify API"""
        token = await self.get_access_token()
        if not token:
            return {}
            
        url = f"https://api.spotify.com/v1/{endpoint}"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            if method == "GET":
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        # Token expired, get a new one and retry
                        self.token = None
                        token = await self.get_access_token()
                        if not token:
                            return {}
                        
                        headers = {"Authorization": f"Bearer {token}"}
                        async with self.session.get(url, headers=headers, params=params) as retry_response:
                            if retry_response.status == 200:
                                return await retry_response.json()
                            else:
                                error_data = await retry_response.text()
                                print(f"Spotify API error (retry): {retry_response.status}, {error_data}")
                                return {}
                    else:
                        error_data = await response.text()
                        print(f"Spotify API error: {response.status}, {error_data}")
                        return {}
            else:
                # For other methods like POST, PUT, DELETE
                async with self.session.request(method, url, headers=headers, json=params) as response:
                    if response.status in (200, 201, 204):
                        try:
                            return await response.json()
                        except:
                            return {"success": True}
                    elif response.status == 401:
                        # Token expired, get a new one and retry
                        self.token = None
                        token = await self.get_access_token()
                        if not token:
                            return {}
                        
                        headers = {"Authorization": f"Bearer {token}"}
                        async with self.session.request(method, url, headers=headers, json=params) as retry_response:
                            if retry_response.status in (200, 201, 204):
                                try:
                                    return await retry_response.json()
                                except:
                                    return {"success": True}
                            else:
                                error_data = await retry_response.text()
                                print(f"Spotify API error (retry): {retry_response.status}, {error_data}")
                                return {}
                    else:
                        error_data = await response.text()
                        print(f"Spotify API error: {response.status}, {error_data}")
                        return {}
        except Exception as e:
            print(f"Error making Spotify API request: {e}")
            return {}
    
    async def search_spotify(self, query: str, search_type: str = "track", limit: int = 10) -> Dict:
        """Search for items on Spotify"""
        valid_types = ["track", "album", "artist", "playlist"]
        if search_type not in valid_types:
            search_type = "track"
            
        params = {
            "q": query,
            "type": search_type,
            "limit": limit
        }
        
        return await self.make_spotify_request("search", params)
    
    async def get_track(self, track_id: str) -> Dict:
        """Get a specific track"""
        return await self.make_spotify_request(f"tracks/{track_id}")
    
    async def get_album(self, album_id: str) -> Dict:
        """Get a specific album"""
        return await self.make_spotify_request(f"albums/{album_id}")
    
    async def get_album_tracks(self, album_id: str, limit: int = 50) -> List[Dict]:
        """Get tracks from an album"""
        params = {"limit": limit}
        response = await self.make_spotify_request(f"albums/{album_id}/tracks", params)
        return response.get("items", [])
    
    async def get_artist(self, artist_id: str) -> Dict:
        """Get a specific artist"""
        return await self.make_spotify_request(f"artists/{artist_id}")
    
    async def get_artist_top_tracks(self, artist_id: str, market: str = "US") -> List[Dict]:
        """Get an artist's top tracks"""
        params = {"market": market}
        response = await self.make_spotify_request(f"artists/{artist_id}/top-tracks", params)
        return response.get("tracks", [])
    
    async def get_artist_albums(self, artist_id: str, limit: int = 10) -> List[Dict]:
        """Get an artist's albums"""
        params = {"limit": limit}
        response = await self.make_spotify_request(f"artists/{artist_id}/albums", params)
        return response.get("items", [])
    
    async def get_playlist(self, playlist_id: str) -> Dict:
        """Get a specific playlist"""
        return await self.make_spotify_request(f"playlists/{playlist_id}")
    
    async def get_playlist_tracks(self, playlist_id: str, limit: int = 50) -> List[Dict]:
        """Get tracks from a playlist"""
        params = {"limit": limit}
        response = await self.make_spotify_request(f"playlists/{playlist_id}/tracks", params)
        return response.get("items", [])
    
    async def get_recommendations(self, seed_tracks: List[str] = None, seed_artists: List[str] = None, 
                                 seed_genres: List[str] = None, limit: int = 10) -> List[Dict]:
        """Get track recommendations"""
        params = {"limit": limit}
        
        if seed_tracks:
            params["seed_tracks"] = ",".join(seed_tracks)
        
        if seed_artists:
            params["seed_artists"] = ",".join(seed_artists)
        
        if seed_genres:
            params["seed_genres"] = ",".join(seed_genres)
        
        # Need at least one seed parameter
        if not any([seed_tracks, seed_artists, seed_genres]):
            return []
        
        response = await self.make_spotify_request("recommendations", params)
        return response.get("tracks", [])
    
    async def extract_spotify_id(self, url_or_id: str, item_type: str = "track") -> str:
        """Extract Spotify ID from a URL or ID string"""
        # Check if it's already an ID
        if re.match(r'^[a-zA-Z0-9]{22}$', url_or_id):
            return url_or_id
        
        # Try to extract from URL
        url_patterns = {
            "track": r'spotify\.com/track/([a-zA-Z0-9]{22})',
            "album": r'spotify\.com/album/([a-zA-Z0-9]{22})',
            "artist": r'spotify\.com/artist/([a-zA-Z0-9]{22})',
            "playlist": r'spotify\.com/playlist/([a-zA-Z0-9]{22})'
        }
        
        if item_type in url_patterns:
            match = re.search(url_patterns[item_type], url_or_id)
            if match:
                return match.group(1)
        
        # Check all patterns if specific type doesn't match
        for pattern_type, pattern in url_patterns.items():
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        
        # If not found, return the original string
        return url_or_id
    
    @app_commands.command(name="spotifysearch", description="Search for tracks on Spotify")
    @app_commands.describe(
        query="What to search for",
        search_type="Type of content to search for"
    )
    @app_commands.choices(search_type=[
        app_commands.Choice(name="Tracks", value="track"),
        app_commands.Choice(name="Albums", value="album"),
        app_commands.Choice(name="Artists", value="artist"),
        app_commands.Choice(name="Playlists", value="playlist")
    ])
    async def slash_spotify(self, interaction: discord.Interaction, query: str, search_type: str = "track"):
        """Search for content on Spotify (slash command)"""
        await interaction.response.defer()
        
        # Search Spotify
        search_results = await self.search_spotify(query, search_type, 10)
        
        # Handle the results based on the search type
        if search_type == "track":
            tracks = search_results.get("tracks", {}).get("items", [])
            if not tracks:
                await interaction.followup.send(f"No tracks found for '{query}'.")
                return
            
            # Create view with buttons
            view = SpotifyView(
                author_id=interaction.user.id,
                tracks=tracks,
                query=f"Track Search: {query}",
                cog=self
            )
            
            # Create initial embed
            first_track = tracks[0]
            embed = view.create_track_embed(first_track, f"Track Search: {query}")
            
            # Send the message
            message = await interaction.followup.send(embed=embed, view=view)
            view.message = await message.fetch()
        
        elif search_type == "album":
            albums = search_results.get("albums", {}).get("items", [])
            if not albums:
                await interaction.followup.send(f"No albums found for '{query}'.")
                return
            
            # Get the first album
            first_album = albums[0]
            album_id = first_album.get("id")
            
            # Get the album tracks
            album_tracks = await self.get_album_tracks(album_id)
            
            # Create view with buttons
            view = AlbumView(
                author_id=interaction.user.id,
                album=first_album,
                tracks=album_tracks,
                cog=self
            )
            
            # Create initial embed
            embed = view.create_album_embed()
            
            # Send the message
            message = await interaction.followup.send(embed=embed, view=view)
            view.message = await message.fetch()
        
        elif search_type == "artist":
            artists = search_results.get("artists", {}).get("items", [])
            if not artists:
                await interaction.followup.send(f"No artists found for '{query}'.")
                return
            
            # Get the first artist
            first_artist = artists[0]
            artist_id = first_artist.get("id")
            
            # Get the artist's top tracks
            top_tracks = await self.get_artist_top_tracks(artist_id)
            
            if not top_tracks:
                await interaction.followup.send(f"No tracks found for this artist.")
                return
            
            # Create view with buttons
            view = SpotifyView(
                author_id=interaction.user.id,
                tracks=top_tracks,
                query=f"Top tracks for {first_artist.get('name')}",
                cog=self
            )
            
            # Create initial embed
            first_track = top_tracks[0]
            embed = view.create_track_embed(first_track, f"Top tracks for {first_artist.get('name')}")
            
            # Send the message
            message = await interaction.followup.send(embed=embed, view=view)
            view.message = await message.fetch()
        
        elif search_type == "playlist":
            playlists = search_results.get("playlists", {}).get("items", [])
            if not playlists:
                await interaction.followup.send(f"No playlists found for '{query}'.")
                return
            
            # Get the first playlist
            first_playlist = playlists[0]
            playlist_id = first_playlist.get("id")
            
            # Get the playlist tracks
            playlist_tracks = await self.get_playlist_tracks(playlist_id)
            
            if not playlist_tracks:
                await interaction.followup.send(f"No tracks found in this playlist.")
                return
            
            # Create view with buttons
            view = PlaylistView(
                author_id=interaction.user.id,
                playlist=first_playlist,
                tracks=playlist_tracks,
                cog=self
            )
            
            # Create initial embed
            embed = view.create_playlist_embed()
            
            # Send the message
            message = await interaction.followup.send(embed=embed, view=view)
            view.message = await message.fetch()
    
    @commands.hybrid_command(name="spotify_search", aliases=["spotify"], with_app_command=True)
    @app_commands.describe(
        query="What to search for",
        search_type="Type of content to search for (track, album, artist, playlist)"
    )
    async def spotify(self, ctx, *, query: str, search_type: str = "track"):
        """Search for content on Spotify"""
        # Validate search type
        valid_types = ["track", "album", "artist", "playlist"]
        if search_type.lower() not in valid_types:
            search_type = "track"
        else:
            search_type = search_type.lower()
        
        async with ctx.typing():
            # Search Spotify
            search_results = await self.search_spotify(query, search_type, 10)
            
            # Handle the results based on the search type
            if search_type == "track":
                tracks = search_results.get("tracks", {}).get("items", [])
                if not tracks:
                    await ctx.send(f"No tracks found for '{query}'.")
                    return
                
                # Create view with buttons
                view = SpotifyView(
                    author_id=ctx.author.id,
                    tracks=tracks,
                    query=f"Track Search: {query}",
                    cog=self
                )
                
                # Create initial embed
                first_track = tracks[0]
                embed = view.create_track_embed(first_track, f"Track Search: {query}")
                
                # Send the message
                message = await ctx.send(embed=embed, view=view)
                view.message = message
            
            elif search_type == "album":
                albums = search_results.get("albums", {}).get("items", [])
                if not albums:
                    await ctx.send(f"No albums found for '{query}'.")
                    return
                
                # Get the first album
                first_album = albums[0]
                album_id = first_album.get("id")
                
                # Get the album tracks
                album_tracks = await self.get_album_tracks(album_id)
                
                # Create view with buttons
                view = AlbumView(
                    author_id=ctx.author.id,
                    album=first_album,
                    tracks=album_tracks,
                    cog=self
                )
                
                # Create initial embed
                embed = view.create_album_embed()
                
                # Send the message
                message = await ctx.send(embed=embed, view=view)
                view.message = message
            
            elif search_type == "artist":
                artists = search_results.get("artists", {}).get("items", [])
                if not artists:
                    await ctx.send(f"No artists found for '{query}'.")
                    return
                
                # Get the first artist
                first_artist = artists[0]
                artist_id = first_artist.get("id")
                
                # Get the artist's top tracks
                top_tracks = await self.get_artist_top_tracks(artist_id)
                
                if not top_tracks:
                    await ctx.send(f"No tracks found for this artist.")
                    return
                
                # Create view with buttons
                view = SpotifyView(
                    author_id=ctx.author.id,
                    tracks=top_tracks,
                    query=f"Top tracks for {first_artist.get('name')}",
                    cog=self
                )
                
                # Create initial embed
                first_track = top_tracks[0]
                embed = view.create_track_embed(first_track, f"Top tracks for {first_artist.get('name')}")
                
                # Send the message
                message = await ctx.send(embed=embed, view=view)
                view.message = message
            
            elif search_type == "playlist":
                playlists = search_results.get("playlists", {}).get("items", [])
                if not playlists:
                    await ctx.send(f"No playlists found for '{query}'.")
                    return
                
                # Get the first playlist
                first_playlist = playlists[0]
                playlist_id = first_playlist.get("id")
                
                # Get the playlist tracks
                playlist_tracks = await self.get_playlist_tracks(playlist_id)
                
                if not playlist_tracks:
                    await ctx.send(f"No tracks found in this playlist.")
                    return
                
                # Create view with buttons
                view = PlaylistView(
                    author_id=ctx.author.id,
                    playlist=first_playlist,
                    tracks=playlist_tracks,
                    cog=self
                )
                
                # Create initial embed
                embed = view.create_playlist_embed()
                
                # Send the message
                message = await ctx.send(embed=embed, view=view)
                view.message = message
    
    @commands.hybrid_command(name="track", with_app_command=True)
    @app_commands.describe(query="The track name or Spotify URL to search for")
    async def track(self, ctx, *, query: str):
        """Search for a track on Spotify"""
        await self.spotify(ctx, query=query, search_type="track")
    
    @commands.hybrid_command(name="album", with_app_command=True)
    @app_commands.describe(query="The album name or Spotify URL to search for")
    async def album(self, ctx, *, query: str):
        """Search for an album on Spotify"""
        await self.spotify(ctx, query=query, search_type="album")
    
    @commands.hybrid_command(name="artist", with_app_command=True)
    @app_commands.describe(query="The artist name or Spotify URL to search for")
    async def artist(self, ctx, *, query: str):
        """Search for an artist on Spotify"""
        await self.spotify(ctx, query=query, search_type="artist")
    
    @commands.hybrid_command(name="playlist", with_app_command=True)
    @app_commands.describe(query="The playlist name or Spotify URL to search for")
    async def playlist(self, ctx, *, query: str):
        """Search for a playlist on Spotify"""
        await self.spotify(ctx, query=query, search_type="playlist")
    
    @commands.hybrid_command(name="spotifyfavorites", aliases=["spotifyfavs"], with_app_command=True)
    @app_commands.describe(favorite_type="The type of favorites to view")
    @app_commands.choices(favorite_type=[
        app_commands.Choice(name="Tracks", value="tracks"),
        app_commands.Choice(name="Albums", value="albums"),
        app_commands.Choice(name="Playlists", value="playlists")
    ])
    async def spotify_favorites(self, ctx, favorite_type: str = "tracks"):
        """View your favorite Spotify items"""
        user_id_str = str(ctx.author.id)
        
        if user_id_str not in self.favorites:
            await ctx.send("You don't have any Spotify favorites yet.")
            return
        
        # Validate favorite type
        valid_types = ["tracks", "albums", "playlists"]
        if favorite_type.lower() not in valid_types:
            favorite_type = "tracks"
        else:
            favorite_type = favorite_type.lower()
        
        # Get the user's favorites
        favorites = self.favorites[user_id_str].get(favorite_type, [])
        
        if not favorites:
            await ctx.send(f"You don't have any favorite {favorite_type} yet.")
            return
        
        # Create paginated embeds
        embeds = []
        items_per_page = 10
        
        for i in range(0, len(favorites), items_per_page):
            chunk = favorites[i:i + items_per_page]
            
            embed = discord.Embed(
                title=f"Your Spotify {favorite_type.capitalize()}",
                color=0x1DB954,
                timestamp=datetime.utcnow()
            )
            
            for j, item in enumerate(chunk, 1):
                name = item.get("name", "Unknown")
                
                if favorite_type == "tracks":
                    artists = ", ".join(item.get("artists", ["Unknown"]))
                    album = item.get("album", "Unknown")
                    value = f"By: {artists}\nAlbum: {album}"
                elif favorite_type == "albums":
                    artists = ", ".join(item.get("artists", ["Unknown"]))
                    value = f"By: {artists}"
                else:  # playlists
                    owner = item.get("owner", "Unknown")
                    value = f"Created by: {owner}"
                
                # Add external URL if available
                external_url = item.get("external_urls", {}).get("spotify")
                if external_url:
                    value += f"\n[Open in Spotify]({external_url})"
                
                # Add saved time
                saved_at = item.get("saved_at", "Unknown")
                try:
                    saved_datetime = datetime.fromisoformat(saved_at)
                    saved_timestamp = int(saved_datetime.timestamp())
                    value += f"\nSaved: <t:{saved_timestamp}:R>"
                except:
                    value += f"\nSaved: {saved_at}"
                
                embed.add_field(
                    name=f"{i + j}. {name}",
                    value=value,
                    inline=False
                )
            
            embed.set_footer(text=f"Page {i // items_per_page + 1}/{(len(favorites) - 1) // items_per_page + 1}")
            embeds.append(embed)
        
        if not embeds:
            await ctx.send(f"You don't have any favorite {favorite_type} yet.")
            return
        
        # Send the first page
        current_page = 0
        message = await ctx.send(embed=embeds[current_page])
        
        # Add navigation reactions if there are multiple pages
        if len(embeds) > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")
            await message.add_reaction("❌")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️", "❌"] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    # Remove the user's reaction
                    try:
                        await message.remove_reaction(reaction, user)
                    except:
                        pass
                    
                    # Handle the reaction
                    if str(reaction.emoji) == "➡️" and current_page < len(embeds) - 1:
                        current_page += 1
                        await message.edit(embed=embeds[current_page])
                    elif str(reaction.emoji) == "⬅️" and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=embeds[current_page])
                    elif str(reaction.emoji) == "❌":
                        await message.clear_reactions()
                        break
                        
                except asyncio.TimeoutError:
                    await message.clear_reactions()
                    break
    
    @commands.hybrid_command(name="recommend", with_app_command=True)
    @app_commands.describe(query="Track or artist to base recommendations on")
    async def recommend(self, ctx, *, query: str):
        """Get music recommendations based on a track or artist"""
        async with ctx.typing():
            # First try to search for a track
            search_results = await self.search_spotify(query, "track", 1)
            tracks = search_results.get("tracks", {}).get("items", [])
            
            seed_tracks = []
            seed_artists = []
            
            if tracks:
                track = tracks[0]
                seed_tracks.append(track.get("id"))
                search_source = f"track: {track.get('name')} by {track.get('artists', [{}])[0].get('name', 'Unknown')}"
            else:
                # If no track found, try artist
                search_results = await self.search_spotify(query, "artist", 1)
                artists = search_results.get("artists", {}).get("items", [])
                
                if not artists:
                    await ctx.send(f"No tracks or artists found for '{query}'.")
                    return
                
                artist = artists[0]
                seed_artists.append(artist.get("id"))
                search_source = f"artist: {artist.get('name')}"
            
            # Get recommendations
            recommendations = await self.get_recommendations(
                seed_tracks=seed_tracks,
                seed_artists=seed_artists
            )
            
            if not recommendations:
                await ctx.send("Could not find any recommendations.")
                return
            
            # Create view with buttons
            view = SpotifyView(
                author_id=ctx.author.id,
                tracks=recommendations,
                query=f"Recommendations based on {search_source}",
                cog=self
            )
            
            # Create initial embed
            first_track = recommendations[0]
            embed = view.create_track_embed(first_track, f"Recommendations based on {search_source}")
            
            # Send the message
            message = await ctx.send(embed=embed, view=view)
            view.message = message
    
    @commands.hybrid_command(name="spotifyhelp", with_app_command=True)
    async def spotifyhelp(self, ctx):
        """Show available Spotify commands"""
        embed = discord.Embed(
            title="Spotify Commands",
            description="Here are all the available Spotify commands:",
            color=0x1DB954,
            timestamp=datetime.utcnow()
        )
        
        # Search commands
        embed.add_field(
            name="Search Commands",
            value=(
                f"`{ctx.prefix}spotify <query> [type]` - Search Spotify\n"
                f"`{ctx.prefix}track <query>` - Search for tracks\n"
                f"`{ctx.prefix}album <query>` - Search for albums\n"
                f"`{ctx.prefix}artist <query>` - Search for artists\n"
                f"`{ctx.prefix}playlist <query>` - Search for playlists"
            ),
            inline=False
        )
        
        # Favorite commands
        embed.add_field(
            name="Favorites",
            value=(
                f"`{ctx.prefix}spotifyfavorites [type]` - View your favorites\n"
                f"Type can be: tracks, albums, or playlists"
            ),
            inline=False
        )
        
        # Recommendation commands
        embed.add_field(
            name="Recommendations",
            value=(
                f"`{ctx.prefix}recommend <query>` - Get recommendations\n"
                f"Based on a track or artist that matches your query"
            ),
            inline=False
        )
        
        # Features explanation
        embed.add_field(
            name="Features",
            value=(
                "• Interactive buttons to navigate music content\n"
                "• Save your favorite tracks, albums, and playlists\n"
                "• Get personalized music recommendations\n"
                "• Search by tracks, albums, artists, or playlists"
            ),
            inline=False
        )
        
        # Examples
        embed.add_field(
            name="Examples",
            value=(
                f"`{ctx.prefix}spotify imagine dragons`\n"
                f"`{ctx.prefix}track believer`\n"
                f"`{ctx.prefix}album origins`\n"
                f"`{ctx.prefix}artist imagine dragons`\n"
                f"`{ctx.prefix}recommend thunder`"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SpotifyCog(bot))
