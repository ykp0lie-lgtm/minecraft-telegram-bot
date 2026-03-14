import os
import logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

logger = logging.getLogger(__name__)

class FileManager:
    """Handle file operations for the bot."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.gif_dir = self.base_dir / "gifs"
        logger.info(f"FileManager initialized with gif directory: {self.gif_dir}")
    
    def get_gifs(self, player_count):
        """
        Get GIFs based on player count.
        Returns a list of GIF paths.
        """
        try:
            # Determine which folder to look in based on player count
            if player_count == 0:
                folder = self.gif_dir / "zero"
            elif player_count == 1:
                folder = self.gif_dir / "one"
            elif player_count == 2:
                folder = self.gif_dir / "two"
            else:
                folder = self.gif_dir / "more"
            
            logger.info(f"Looking for GIFs in: {folder}")
            
            if not folder.exists():
                logger.warning(f"GIF folder does not exist: {folder}")
                return []
            
            # Get all GIF files in the folder
            gifs = []
            for file in folder.iterdir():
                if file.is_file() and file.suffix.lower() in ['.gif']:
                    gifs.append(str(file))
            
            logger.info(f"Found {len(gifs)} GIFs")
            return gifs
            
        except Exception as e:
            logger.error(f"Error getting GIFs: {e}")
            return []


class ImageFeatures:
    """Handle image generation features for the bot."""
    
    @staticmethod
    def generate_users_pictures(usernames):
        """
        Generate a composite image of user pictures.
        Returns image bytes or None if no pictures found.
        """
        try:
            logger.info(f"Generating pictures for users: {usernames}")
            
            if not usernames:
                return None
            
            users_pictures_dir = Path("users_pictures")
            if not users_pictures_dir.exists():
                logger.info("No users_pictures directory found")
                return None
            
            # Collect user pictures
            user_images = []
            for username in usernames:
                # Look for user's picture folder (case-insensitive)
                user_folder = None
                for folder in users_pictures_dir.iterdir():
                    if folder.is_dir() and folder.name.lower() == username.lower():
                        user_folder = folder
                        break
                
                if user_folder:
                    # Find first image in the folder
                    for file in user_folder.iterdir():
                        if file.is_file() and file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                            try:
                                img = Image.open(file)
                                # Resize image to standard size
                                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                                user_images.append(img)
                                logger.info(f"Added picture for {username}")
                                break
                            except Exception as e:
                                logger.error(f"Error loading image for {username}: {e}")
            
            if not user_images:
                logger.info("No user pictures found")
                return None
            
            # Create composite image (arrange in a grid)
            images_per_row = 5
            rows = (len(user_images) + images_per_row - 1) // images_per_row
            
            # Create blank canvas
            composite = Image.new('RGB', (images_per_row * 110, rows * 110), color='white')
            draw = ImageDraw.Draw(composite)
            
            # Try to add usernames under pictures
            try:
                font = ImageFont.load_default()
            except:
                font = None
            
            # Paste images and add usernames
            for i, (img, username) in enumerate(zip(user_images, usernames[:len(user_images)])):
                row = i // images_per_row
                col = i % images_per_row
                x = col * 110 + 5
                y = row * 110 + 5
                composite.paste(img, (x, y))
                
                # Add username under picture
                if font:
                    draw.text((x, y + 105), username[:10], fill='black', font=font)
            
            # Convert to bytes for Telegram
            img_bytes = io.BytesIO()
            composite.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            logger.info(f"Generated composite image with {len(user_images)} pictures")
            return img_bytes.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating user pictures: {e}")
            return None
