from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Guild(Base):
    """Represents server-specific settings and configurations"""
    __tablename__ = 'guilds'
    
    id = Column(BigInteger, primary_key=True)  # Discord guild ID
    prefix = Column(String(10), default="lx ")  # Custom prefix for this guild
    welcome_channel_id = Column(BigInteger, nullable=True)  # Channel for welcome messages
    welcome_message = Column(Text, nullable=True)  # Custom welcome message
    log_channel_id = Column(BigInteger, nullable=True)  # Channel for logging
    mod_role_id = Column(BigInteger, nullable=True)  # Moderator role ID
    mute_role_id = Column(BigInteger, nullable=True)  # Muted role ID
    anti_spam_enabled = Column(Boolean, default=True)  # Whether anti-spam is enabled
    mention_limit = Column(Integer, default=3)  # Max mentions allowed per message
    
    # Relationships
    auto_roles = relationship("AutoRole", back_populates="guild", cascade="all, delete-orphan")
    custom_commands = relationship("CustomCommand", back_populates="guild", cascade="all, delete-orphan")
    restricted_channels = relationship("RestrictedChannel", back_populates="guild", cascade="all, delete-orphan")
    user_settings = relationship("UserSettings", back_populates="guild", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Guild id={self.id}>"

class AutoRole(Base):
    """Roles automatically assigned to new members"""
    __tablename__ = 'auto_roles'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id', ondelete='CASCADE'))
    role_id = Column(BigInteger)
    
    guild = relationship("Guild", back_populates="auto_roles")
    
    def __repr__(self):
        return f"<AutoRole guild_id={self.guild_id} role_id={self.role_id}>"

class CustomCommand(Base):
    """Custom commands defined by server admins"""
    __tablename__ = 'custom_commands'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id', ondelete='CASCADE'))
    name = Column(String(50), nullable=False)  # Command name
    response = Column(Text, nullable=False)  # Command response
    
    guild = relationship("Guild", back_populates="custom_commands")
    
    def __repr__(self):
        return f"<CustomCommand guild_id={self.guild_id} name={self.name}>"

class RestrictedChannel(Base):
    """Voice channels with restricted access"""
    __tablename__ = 'restricted_channels'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id', ondelete='CASCADE'))
    channel_id = Column(BigInteger, nullable=False)
    
    guild = relationship("Guild", back_populates="restricted_channels")
    allowed_users = relationship("AllowedUser", back_populates="channel", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<RestrictedChannel guild_id={self.guild_id} channel_id={self.channel_id}>"

class AllowedUser(Base):
    """Users allowed to access restricted voice channels"""
    __tablename__ = 'allowed_users'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, ForeignKey('restricted_channels.id', ondelete='CASCADE'))
    user_id = Column(BigInteger, nullable=False)
    
    channel = relationship("RestrictedChannel", back_populates="allowed_users")
    
    def __repr__(self):
        return f"<AllowedUser channel_id={self.channel_id} user_id={self.user_id}>"

class UserSettings(Base):
    """User-specific settings within a guild"""
    __tablename__ = 'user_settings'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(BigInteger, ForeignKey('guilds.id', ondelete='CASCADE'))
    user_id = Column(BigInteger, nullable=False)
    warn_count = Column(Integer, default=0)  # Number of warnings
    birthday = Column(String(10), nullable=True)  # Birthday in MM-DD format
    
    guild = relationship("Guild", back_populates="user_settings")
    
    def __repr__(self):
        return f"<UserSettings guild_id={self.guild_id} user_id={self.user_id}>"

class AnimeGif(Base):
    """Anime GIFs for the random anime gif command"""
    __tablename__ = 'anime_gifs'
    
    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False)  # e.g., "dog", "cat", "anime"
    url = Column(String(255), nullable=False)  # URL to the GIF
    
    def __repr__(self):
        return f"<AnimeGif id={self.id} category={self.category}>"