from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image
import os
import io

# Input and output directories
INPUT_IMG = "input_img"
OUTPUT_IMG = "output_img"

# Ensure directories exist
os.makedirs(INPUT_IMG, exist_ok=True)
os.makedirs(OUTPUT_IMG, exist_ok=True)

def get_format_keyboard():
    """Returns inline keyboard with format selection options"""
    buttons = [
        [InlineKeyboardButton(text="PNG", callback_data="png")],
        [InlineKeyboardButton(text="JPG", callback_data="jpg")],
        [InlineKeyboardButton(text="WEBP", callback_data="webp")],
        [InlineKeyboardButton(text="BMP", callback_data="bmp")],
        [InlineKeyboardButton(text="GIF", callback_data="gif")],
        [InlineKeyboardButton(text="ICO", callback_data="ico")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def convert_image(image_bytes: bytes, output_format: str) -> bytes:
    """
    Convert image bytes to the specified format.
    Supports: PNG, JPG, WEBP, BMP, GIF, ICO
    """
    try:
        # Open image from bytes
        img = Image.open(io.BytesIO(image_bytes))
        
        # Handle RGBA to RGB conversion for JPG
        if output_format.lower() == "jpg" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # Handle ICO format
        if output_format.lower() == "ico":
            img = img.resize((256, 256))
        
        # Save to bytes buffer
        output_buffer = io.BytesIO()
        
        # Map format to PIL save format
        format_map = {
            "png": "PNG",
            "jpg": "JPEG",
            "jpeg": "JPEG",
            "webp": "WEBP",
            "bmp": "BMP",
            "gif": "GIF",
            "ico": "ICO",
        }
        
        save_format = format_map.get(output_format.lower(), "PNG")
        img.save(output_buffer, format=save_format)
        
        # Get the bytes from the buffer
        output_buffer.seek(0)
        return output_buffer.getvalue()
        
    except Exception as e:
        print(f"Conversion error: {e}")
        raise e
