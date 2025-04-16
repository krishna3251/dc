"""
Database models for the Discord bot
"""
import os
import json
import datetime
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Create SQLAlchemy instance
db = SQLAlchemy(model_class=Base)

# User model
class User(db.Model):
    """Discord user data"""
    id = db.Column(db.BigInteger, primary_key=True)  # Discord user ID
    username = db.Column(db.String(100), nullable=False)
    discriminator = db.Column(db.String(10), nullable=True)  # May be None with new Discord username system
    bot = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=True)
    last_seen = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    command_usages = db.relationship('CommandUsage', back_populates='user', cascade='all, delete-orphan')
    gif_favorites = db.relationship('GifFavorite', back_populates='user', cascade='all, delete-orphan')
    search_history = db.relationship('SearchHistory', back_populates='user', cascade='all, delete-orphan')
    spotify_history = db.relationship('SpotifyHistory', back_populates='user', cascade='all, delete-orphan')
    warnings = db.relationship('Warning', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User id={self.id} username={self.username}>'

# Guild (Server) model
class Guild(db.Model):
    """Discord guild/server data"""
    id = db.Column(db.BigInteger, primary_key=True)  # Discord guild ID
    name = db.Column(db.String(100), nullable=False)
    icon_url = db.Column(db.String(255), nullable=True)
    owner_id = db.Column(db.BigInteger, nullable=True)
    member_count = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=True)
    joined_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Configuration as JSON
    prefix = db.Column(db.String(10), default="!")
    config = db.Column(db.Text, nullable=True)  # JSON string for config
    
    # Relationships
    warnings = db.relationship('Warning', back_populates='guild', cascade='all, delete-orphan')
    command_usages = db.relationship('CommandUsage', back_populates='guild', cascade='all, delete-orphan')
    
    def get_config(self):
        """Get configuration as dict"""
        if not self.config:
            return {}
        try:
            return json.loads(self.config)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse config JSON for guild {self.id}")
            return {}
    
    def set_config(self, config_dict):
        """Set configuration from dict"""
        self.config = json.dumps(config_dict)
    
    def __repr__(self):
        return f'<Guild id={self.id} name={self.name}>'

# Command Usage tracking
class CommandUsage(db.Model):
    """Track command usage"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), nullable=False)
    guild_id = db.Column(db.BigInteger, db.ForeignKey('guild.id'), nullable=True)  # Nullable for DM commands
    command_name = db.Column(db.String(50), nullable=False)
    used_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='command_usages')
    guild = db.relationship('Guild', back_populates='command_usages')
    
    def __repr__(self):
        return f'<CommandUsage id={self.id} command={self.command_name}>'

# GIF Favorites
class GifFavorite(db.Model):
    """User's favorite GIFs"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), nullable=False)
    gif_id = db.Column(db.String(100), nullable=False)  # GIPHY ID
    url = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(255), nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='gif_favorites')
    
    def __repr__(self):
        return f'<GifFavorite id={self.id} gif_id={self.gif_id}>'

# Search History
class SearchHistory(db.Model):
    """User's search history"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), nullable=False)
    query = db.Column(db.String(255), nullable=False)
    search_type = db.Column(db.String(20), nullable=False, default='web')  # web, image, etc.
    searched_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='search_history')
    
    def __repr__(self):
        return f'<SearchHistory id={self.id} query={self.query}>'

# Spotify History
class SpotifyHistory(db.Model):
    """User's Spotify search history"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), nullable=False)
    item_id = db.Column(db.String(100), nullable=False)  # Spotify ID
    item_type = db.Column(db.String(20), nullable=False)  # track, album, artist, playlist
    name = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    searched_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='spotify_history')
    
    def __repr__(self):
        return f'<SpotifyHistory id={self.id} item_type={self.item_type} name={self.name}>'

# Warning model for moderations
class Warning(db.Model):
    """User warnings"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('user.id'), nullable=False)
    guild_id = db.Column(db.BigInteger, db.ForeignKey('guild.id'), nullable=False)
    moderator_id = db.Column(db.BigInteger, nullable=False)
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', back_populates='warnings')
    guild = db.relationship('Guild', back_populates='warnings')
    
    def __repr__(self):
        return f'<Warning id={self.id} user_id={self.user_id} guild_id={self.guild_id}>'

def init_app(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    
    # Create all tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created")