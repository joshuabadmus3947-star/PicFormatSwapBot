import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from convert import convert_image, get_format_keyboard

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required!")

BOT_NAME = os.getenv("BOT_NAME", "PicFormatSwapBot")
BOT_USERNAME = os.getenv("BOT_USERNAME", "@PicFormatSwapBot")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# FSM States for the conversion flow
class ConversionState(StatesGroup):
    waiting_for_image = State()
    waiting_for_format = State()


@dp.message(Command("start"))
async def start_command(message: types.Message):
    """Handler for /start command"""
    welcome_text = (
        f"🎨 Welcome to {BOT_NAME}!\n\n"
        "I can convert your images between different formats.\n\n"
        "📌 How to use:\n"
        "1️⃣ Send /convert to start the conversion process\n"
        "2️⃣ Upload an image (as file or photo)\n"
        "3️⃣ Select your desired output format\n"
        "4️⃣ Receive your converted image!\n\n"
        f"📱 Bot Username: {BOT_USERNAME}\n\n"
        "Supported formats: PNG, JPG, WEBP, BMP, GIF, ICO"
    )
    await message.answer(welcome_text)


@dp.message(Command("convert"))
async def convert_command(message: types.Message, state: FSMContext):
    """Handler for /convert command - starts the conversion process"""
    await message.answer(
        "📤 Please send me an image to convert.\n\n"
        "You can send it as a file (document) or as a photo."
    )
    await state.set_state(ConversionState.waiting_for_image)


@dp.message(Command("help"))
async def help_command(message: types.Message):
    """Handler for /help command"""
    help_text = (
        "🆘 Help Center\n\n"
        "Commands:\n"
        "/start - Show welcome message\n"
        "/convert - Start the image conversion process\n"
        "/help - Show this help message\n"
        "/about - About this bot\n\n"
        "Supported formats: PNG, JPG, WEBP, BMP, GIF, ICO"
    )
    await message.answer(help_text)


@dp.message(Command("about"))
async def about_command(message: types.Message):
    """Handler for /about command"""
    await message.answer(
        "🤖 PicFormatSwapBot v1.0\n\n"
        "A Telegram bot for converting images between various formats.\n\n"
        "Built with Aiogram 3 and Pillow.\n"
        "Deployed on Railway.\n\n"
        "Source code available on GitHub."
    )


@dp.message(ConversionState.waiting_for_image, F.photo)
async def handle_photo_image(message: types.Message, state: FSMContext):
    """Handle photo input from user"""
    try:
        # Get the largest photo (highest quality)
        photo = message.photo[-1]
        
        # Download the photo
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_data = file_bytes.getvalue()
        
        # Store image data in FSM context
        await state.update_data(image_data=image_data)
        
        # Ask for output format
        await message.answer(
            "🔄 Select the output format:",
            reply_markup=get_format_keyboard()
        )
        await state.set_state(ConversionState.waiting_for_format)
        
    except Exception as e:
        logger.error(f"Error handling photo: {e}")
        await message.answer("❌ Failed to process the image. Please try again.")
        await state.clear()


@dp.message(ConversionState.waiting_for_image, F.document)
async def handle_document_image(message: types.Message, state: FSMContext):
    """Handle document (file) input from user"""
    try:
        document = message.document
        
        # Check if the file is an image
        allowed_mime_types = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"]
        if document.mime_type not in allowed_mime_types:
            await message.answer(
                "❌ Unsupported file type. Please send a valid image.\n"
                "Supported formats: JPEG, PNG, WEBP, GIF, BMP"
            )
            return
        
        # Download the document
        file = await bot.get_file(document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_data = file_bytes.getvalue()
        
        # Store image data in FSM context
        await state.update_data(image_data=image_data)
        
        # Ask for output format
        await message.answer(
            "🔄 Select the output format:",
            reply_markup=get_format_keyboard()
        )
        await state.set_state(ConversionState.waiting_for_format)
        
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        await message.answer("❌ Failed to process the image. Please try again.")
        await state.clear()


@dp.callback_query(ConversionState.waiting_for_format)
async def handle_format_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle the format selection from inline keyboard"""
    try:
        selected_format = callback.data
        
        # Get the stored image data
        data = await state.get_data()
        image_data = data.get("image_data")
        
        if not image_data:
            await callback.message.answer("❌ No image found. Please start over with /convert")
            await state.clear()
            await callback.answer()
            return
        
        # Show processing message
        await callback.message.edit_text(
            f"⏳ Converting your image to **{selected_format.upper()}**...\n"
            "Please wait..."
        )
        
        # Convert the image
        converted_data = convert_image(image_data, selected_format)
        
        # Determine file extension
        ext_map = {
            "png": "png",
            "jpg": "jpg",
            "jpeg": "jpg",
            "webp": "webp",
            "bmp": "bmp",
            "gif": "gif",
            "ico": "ico",
        }
        extension = ext_map.get(selected_format.lower(), "png")
        filename = f"converted_image.{extension}"
        
        # Send the converted image back to the user
        await callback.message.delete()
        await callback.message.answer_document(
            types.BufferedInputFile(
                file=converted_data,
                filename=filename
            ),
            caption=f"✅ Conversion complete!\n\n**Output format:** {selected_format.upper()}\n"
                    "Send /convert to convert another image."
        )
        
        # Clear the state
        await state.clear()
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        await callback.message.edit_text(
            "❌ Conversion failed. Please try again with /convert"
        )
        await state.clear()
        await callback.answer()


@dp.message()
async def fallback_handler(message: types.Message, state: FSMContext):
    """Handle any other messages"""
    current_state = await state.get_state()
    
    if current_state == ConversionState.waiting_for_image:
        await message.answer(
            "📤 Please send an image file or photo.\n"
            "Send /convert to restart the process."
        )
    else:
        await message.answer(
            "🤔 I don't understand that command.\n"
            "Send /start to see available commands."
        )


async def main():
    """Main entry point"""
    logger.info("🤖 Bot is starting...")
    
    # Set bot commands for Telegram menu
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Show welcome message"),
        types.BotCommand(command="convert", description="Start image conversion"),
        types.BotCommand(command="help", description="Show help message"),
        types.BotCommand(command="about", description="About this bot"),
    ])
    
    logger.info("✅ Bot is ready! Starting polling...")
    
    # Start polling
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Polling error: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
