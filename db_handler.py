import os
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine
from models import Base, Guild, AutoRole, CustomCommand, RestrictedChannel, AllowedUser, UserSettings, AnimeGif

# Get database URL from environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")

# Create engine and session factory
engine = create_engine(DATABASE_URL) if DATABASE_URL else None
Session = scoped_session(sessionmaker(bind=engine)) if engine else None

def init_db():
    """Initialize database and tables"""
    if engine:
        Base.metadata.create_all(engine)
        print("✅ Database tables created!")
    else:
        print("❌ No database connection available.")

class DatabaseHandler:
    """Handles database operations for the bot"""
    
    @staticmethod
    def get_guild_settings(guild_id):
        """Get settings for a specific guild"""
        if not Session:
            return None
            
        session = Session()
        try:
            guild = session.query(Guild).filter_by(id=guild_id).first()
            if not guild:
                # Create new guild settings if they don't exist
                guild = Guild(id=guild_id)
                session.add(guild)
                session.commit()
            return guild
        except Exception as e:
            print(f"Error getting guild settings: {e}")
            session.rollback()
            return None
        finally:
            session.close()
    
    @staticmethod
    def update_guild_settings(guild_id, **kwargs):
        """Update guild settings with provided values"""
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
            return True
        except Exception as e:
            print(f"Error adding custom command: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    @staticmethod
    def get_custom_command(guild_id, command_name):
        """Get a custom command for a guild"""
        if not Session:
            return None
            
        session = Session()
        try:
            command = session.query(CustomCommand).filter_by(
                guild_id=guild_id, name=command_name
            ).first()
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