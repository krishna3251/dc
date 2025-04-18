import os
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from models import Base, Guild, AutoRole, CustomCommand, RestrictedChannel, AllowedUser, UserSettings, AnimeGif
import functools

# Get database URL from environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")

# Create engine and session factory with optimized settings for better performance
if DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,          # Increase connection pool size
        max_overflow=20,       # Allow more overflow connections
        pool_recycle=1800,     # Recycle connections after 30 minutes
        pool_pre_ping=True,    # Verify connection is still valid before using
        pool_timeout=30,       # Don't wait too long for a connection
        echo=False             # No SQL debug logging
    )
    Session = scoped_session(sessionmaker(bind=engine))
else:
    engine = None
    Session = None

# Create cache dictionaries to reduce database queries
guild_settings_cache = {}
custom_commands_cache = {}
restricted_channels_cache = {}

def init_db():
    """Initialize database and tables"""
    if engine:
        # Create tables only if they don't exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        # Get existing tables
        existing_tables = inspector.get_table_names()
        
        if 'guilds' not in existing_tables:
            # Tables don't exist yet, create them
            Base.metadata.create_all(engine)
            print("✅ Database tables created!")
        else:
            print("✅ Database tables already exist!")
    else:
        print("❌ No database connection available.")

class DatabaseHandler:
    """Handles database operations for the bot"""
    
    @staticmethod
    def get_guild_settings(guild_id):
        """Get settings for a specific guild with caching for better performance"""
        # Check cache first
        if guild_id in guild_settings_cache:
            return guild_settings_cache[guild_id]
            
        if not Session:
            return None
            
        session = Session()
        try:
            # First try to find existing guild settings
            guild = session.query(Guild).filter_by(id=guild_id).first()
            
            if not guild:
                try:
                    # Create new guild settings if they don't exist
                    guild = Guild(id=guild_id)
                    session.add(guild)
                    session.commit()
                except Exception as e:
                    # If we get a duplicate key error, another process likely created it
                    # between our check and insert, so try to fetch it again
                    session.rollback()
                    
                    # Try to find it one more time
                    guild = session.query(Guild).filter_by(id=guild_id).first()
                    
                    # If still not found after the duplicate key error, something is wrong
                    if not guild:
                        print(f"Failed to create or retrieve guild settings for {guild_id}: {e}")
                        return None
                
            # Store in cache for faster future access
            # Make a copy to prevent detached instance issues
            guild_settings_cache[guild_id] = guild
            return guild
        except Exception as e:
            print(f"Error getting guild settings: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    @staticmethod
    def update_guild_settings(guild_id, **kwargs):
        """Update guild settings with provided values and update cache"""
        if not Session:
            return False
            
        session = Session()
        try:
            guild = session.query(Guild).filter_by(id=guild_id).first()
            if not guild:
                guild = Guild(id=guild_id, **kwargs)
                session.add(guild)
            else:
                for key, value in kwargs.items():
                    if hasattr(guild, key):
                        setattr(guild, key, value)
            
            session.commit()
            
            # Update the cache with the new settings
            if guild_id in guild_settings_cache:
                # Update existing cache entry
                for key, value in kwargs.items():
                    if hasattr(guild_settings_cache[guild_id], key):
                        setattr(guild_settings_cache[guild_id], key, value)
            else:
                # Add to cache
                guild_settings_cache[guild_id] = guild
                
            return True
        except Exception as e:
            print(f"Error updating guild settings: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    @staticmethod
    def add_auto_role(guild_id, role_id):
        """Add an auto-role for a guild"""
        if not Session:
            return False
            
        session = Session()
        try:
            # Check if the role is already set as auto-role
            existing = session.query(AutoRole).filter_by(guild_id=guild_id, role_id=role_id).first()
            if existing:
                return True  # Already exists
                
            # Get or create guild settings
            guild = session.query(Guild).filter_by(id=guild_id).first()
            if not guild:
                guild = Guild(id=guild_id)
                session.add(guild)
                
            # Add auto-role
            auto_role = AutoRole(guild_id=guild_id, role_id=role_id)
            session.add(auto_role)
            session.commit()
            return True
        except Exception as e:
            print(f"Error adding auto-role: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    @staticmethod
    def clear_cache(guild_id=None):
        """Clear caches to prevent stale data
        
        Args:
            guild_id: If provided, only clear caches for this guild
        """
        global guild_settings_cache, custom_commands_cache, restricted_channels_cache
        
        if guild_id is None:
            # Clear all caches
            guild_settings_cache = {}
            custom_commands_cache = {}
            restricted_channels_cache = {}
        else:
            # Clear only caches for the specified guild
            
            # Clear guild settings
            if guild_id in guild_settings_cache:
                del guild_settings_cache[guild_id]
                
            # Clear custom commands (keys are in format "{guild_id}_{command_name}")
            to_remove = []
            for key in custom_commands_cache:
                if key.startswith(f"{guild_id}_"):
                    to_remove.append(key)
                    
            for key in to_remove:
                del custom_commands_cache[key]
            
            # Clear restricted channels
            if guild_id in restricted_channels_cache:
                del restricted_channels_cache[guild_id]
                
    @staticmethod
    def add_custom_command(guild_id, command_name, command_response):
        """Add or update a custom command for a guild"""
        if not Session:
            return False
            
        session = Session()
        try:
            # Check if command already exists for this guild
            command = session.query(CustomCommand).filter_by(
                guild_id=guild_id, name=command_name
            ).first()
            
            if command:
                # Update existing command
                command.response = command_response
            else:
                # Create new command
                command = CustomCommand(
                    guild_id=guild_id,
                    name=command_name,
                    response=command_response
                )
                session.add(command)
                
            session.commit()
            
            # Update cache
            cache_key = f"{guild_id}_{command_name}"
            custom_commands_cache[cache_key] = command
            
            return True
        except Exception as e:
            print(f"Error adding custom command: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    @staticmethod
    def get_custom_command(guild_id, command_name):
        """Get a custom command for a guild with caching for better performance"""
        # Create a cache key
        cache_key = f"{guild_id}_{command_name}"
        
        # Check cache first
        if cache_key in custom_commands_cache:
            return custom_commands_cache[cache_key]
            
        if not Session:
            return None
            
        session = Session()
        try:
            command = session.query(CustomCommand).filter_by(
                guild_id=guild_id, name=command_name
            ).first()
            
            # Add to cache if found
            if command:
                custom_commands_cache[cache_key] = command
                
            return command
        except Exception as e:
            print(f"Error getting custom command: {e}")
            return None
        finally:
            session.close()
    
    @staticmethod
    def restrict_channel(guild_id, channel_id):
        """Add a channel to the restricted list"""
        if not Session:
            return False
            
        session = Session()
        try:
            # Check if channel is already restricted
            existing = session.query(RestrictedChannel).filter_by(
                guild_id=guild_id, channel_id=channel_id
            ).first()
            
            if not existing:
                channel = RestrictedChannel(guild_id=guild_id, channel_id=channel_id)
                session.add(channel)
                session.commit()
            
            return True
        except Exception as e:
            print(f"Error restricting channel: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    @staticmethod
    def add_allowed_user(guild_id, channel_id, user_id):
        """Allow a user to access a restricted channel"""
        if not Session:
            return False
            
        session = Session()
        try:
            # Find the restricted channel
            channel = session.query(RestrictedChannel).filter_by(
                guild_id=guild_id, channel_id=channel_id
            ).first()
            
            if not channel:
                # Create the restricted channel entry first
                channel = RestrictedChannel(guild_id=guild_id, channel_id=channel_id)
                session.add(channel)
                session.flush()  # Generate ID for the new channel
            
            # Check if user is already allowed
            existing = session.query(AllowedUser).filter_by(
                channel_id=channel.id, user_id=user_id
            ).first()
            
            if not existing:
                allowed_user = AllowedUser(channel_id=channel.id, user_id=user_id)
                session.add(allowed_user)
            
            session.commit()
            return True
        except Exception as e:
            print(f"Error adding allowed user: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    @staticmethod
    def increment_warning(guild_id, user_id):
        """Increment warning count for a user in a guild"""
        if not Session:
            return 0
            
        session = Session()
        try:
            # Find user settings
            user_settings = session.query(UserSettings).filter_by(
                guild_id=guild_id, user_id=user_id
            ).first()
            
            if not user_settings:
                user_settings = UserSettings(guild_id=guild_id, user_id=user_id, warn_count=1)
                session.add(user_settings)
            else:
                user_settings.warn_count += 1
            
            session.commit()
            return user_settings.warn_count
        except Exception as e:
            print(f"Error incrementing warning: {e}")
            session.rollback()
            return 0
        finally:
            session.close()
    
    @staticmethod
    def add_anime_gif(category, url):
        """Add an anime GIF to the database"""
        if not Session:
            return False
            
        session = Session()
        try:
            gif = AnimeGif(category=category, url=url)
            session.add(gif)
            session.commit()
            return True
        except Exception as e:
            print(f"Error adding anime GIF: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    @staticmethod
    def get_random_gif(category=None):
        """Get a random anime GIF, optionally filtered by category"""
        if not Session:
            return None
            
        session = Session()
        try:
            if category:
                query = session.query(AnimeGif).filter_by(category=category)
            else:
                query = session.query(AnimeGif)
                
            # Order by random and get first result
            gif = query.order_by(sa.func.random()).first()
            return gif
        except Exception as e:
            print(f"Error getting random GIF: {e}")
            return None
        finally:
            session.close()

# Initialize the database if possible
if engine:
    init_db()