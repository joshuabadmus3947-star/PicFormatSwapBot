import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from PIL import Image
import io

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

# Format selection keyboard
def get_format_keyboard():
    buttons = [
        [types.InlineKeyboardButton(text="PNG", callback_data="png")],
        [types.InlineKeyboardButton(text="JPG", callback_data="jpg")],
        [types.InlineKeyboardButton(text="WEBP", callback_data="webp")],
        [types.InlineKeyboardButton(text="BMP", callback_data="bmp")],
        [types.InlineKeyboardButton(text="GIF", callback_data="gif")],
        [types.InlineKeyboardButton(text="ICO", callback_data="ico")],
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

# Image conversion function
def convert_image(image_bytes: bytes, output_format: str) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        if output_format.lower() == "jpg" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        if output_format.lower() == "ico":
            img = img.resize((256, 256))
        
        output_buffer = io.BytesIO()
        
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
        
        output_buffer.seek(0)
        return output_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        raise e

@dp.message(Command("start"))
async def start_command(message: types.Message):
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
    await message.answer(
        "📤 Please send me an image to convert.\n\n"
        "You can send it as a file (document) or as a photo."
    )
    await state.set_state(ConversionState.waiting_for_image)

@dp.message(Command("help"))
async def help_command(message: types.Message):
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
    await message.answer(
        "🤖 PicFormatSwapBot v1.0\n\n"
        "A Telegram bot for converting images between various formats.\n\n"
        "Built with Aiogram 3 and Pillow.\n"
        "Deployed on Railway.\n\n"
        "Source code available on GitHub."
    )

@dp.message(ConversionState.waiting_for_image, F.photo)
async def handle_photo_image(message: types.Message, state: FSMContext):
    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_data = file_bytes.getvalue()
        
        await state.update_data(image_data=image_data)
        
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
    try:
        document = message.document
        allowed_mime_types = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"]
        
        if document.mime_type not in allowed_mime_types:
            await message.answer(
                "❌ Unsupported file type. Please send a valid image.\n"
                "Supported formats: JPEG, PNG, WEBP, GIF, BMP"
            )
            return
        
        file = await bot.get_file(document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_data = file_bytes.getvalue()
        
        await state.update_data(image_data=image_data)
        
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
    try:
        selected_format = callback.data
        data = await state.get_data()
        image_data = data.get("image_data")
        
        if not image_data:
            await callback.message.answer("❌ No image found. Please start over with /convert")
            await state.clear()
            await callback.answer()
            return
        
        await callback.message.edit_text(
            f"⏳ Converting your image to **{selected_format.upper()}**...\n"
            "Please wait..."
        )
        
        converted_data = convert_image(image_data, selected_format)
        
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
        
        await callback.message.delete()
        await callback.message.answer_document(
            types.BufferedInputFile(
                file=converted_data,
                filename=filename
            ),
            caption=f"✅ Conversion complete!\n\n**Output format:** {selected_format.upper()}\n"
                    "Send /convert to convert another image."
        )
        
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
    logger.info("🤖 Bot is starting...")
    
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Show welcome message"),
        types.BotCommand(command="convert", description="Start image conversion"),
        types.BotCommand(command="help", description="Show help message"),
        types.BotCommand(command="about", description="About this bot"),
    ])
    
    logger.info("✅ Bot is ready! Starting polling...")
    
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Polling error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
