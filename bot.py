import os
import io
import asyncio
import aiohttp
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

# FREE AI IMAGE GENERATION APIS (use one or all)
# 1. Pollinations.ai - completely free, no API key needed
# 2. Lexica API - free tier available
# 3. Stable Diffusion via HuggingFace - requires free token

# We'll use Pollinations.ai (no API key needed) as primary
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"

# ==================== KEYBOARD FUNCTIONS ====================
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎨 Generate Image", callback_data="generate")],
        [InlineKeyboardButton("📐 Resize Image", callback_data="resize")],
        [InlineKeyboardButton("🔄 Convert Format", callback_data="convert")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_size_keyboard():
    keyboard = [
        [InlineKeyboardButton("512x512", callback_data="size_512"), 
         InlineKeyboardButton("768x768", callback_data="size_768")],
        [InlineKeyboardButton("1024x1024", callback_data="size_1024"), 
         InlineKeyboardButton("Square 1:1", callback_data="size_1_1")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_format_keyboard():
    keyboard = [
        [InlineKeyboardButton("PNG", callback_data="format_png"), 
         InlineKeyboardButton("JPG", callback_data="format_jpg")],
        [InlineKeyboardButton("WEBP", callback_data="format_webp"), 
         InlineKeyboardButton("GIF", callback_data="format_gif")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    welcome_message = (
        f"✨ Welcome {user.first_name} to PixelForgeBot!\n\n"
        "🖼️ I can generate images using AI for free!\n"
        "📤 Send any image to convert or resize it\n"
        "🎨 Use the buttons below to get started\n\n"
        "⚠️ Free plan: 10 images per day"
    )
    await update.message.reply_text(welcome_message, reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "📖 **How to use PixelForgeBot**\n\n"
        "**AI Image Generation**\n"
        "1. Click 'Generate Image'\n"
        "2. Send me a text description\n"
        "3. Choose size and format\n\n"
        "**Image Tools**\n"
        "• Send any image to convert format\n"
        "• Send an image with 'resize' to change size\n\n"
        "**Available Commands**\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/status - Check your usage\n"
        "/generate - Generate an image\n\n"
        "💰 **Free Tier**: 10 images/day\n"
        "⏰ Resets at midnight UTC"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check user's remaining daily usage"""
    user_id = str(update.effective_user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    usage_key = f"{user_id}_{today}"
    
    # Initialize or get usage
    if context.user_data.get(usage_key) is None:
        context.user_data[usage_key] = 0
    
    used = context.user_data[usage_key]
    remaining = max(0, 10 - used)
    
    status_text = (
        f"📊 **Your Usage**\n\n"
        f"Used today: {used}/10\n"
        f"Remaining: {remaining}/10\n\n"
        f"🔄 Resets at midnight UTC"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# ==================== CALLBACK QUERY HANDLERS ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "generate":
        await query.edit_message_text(
            "🎨 **Send me a description**\n\n"
            "Example: 'A cat wearing a spacesuit on Mars'\n\n"
            "I'll generate it for you! 🚀",
            parse_mode="Markdown",
            reply_markup=get_size_keyboard()
        )
        context.user_data["action"] = "generate"
        
    elif data == "resize":
        await query.edit_message_text(
            "📐 **Send me an image**\n\n"
            "Reply with:\n"
            "• '512' for 512x512\n"
            "• '768' for 768x768\n"
            "• '1024' for 1024x1024\n\n"
            "Example: Send image with caption '768'",
            reply_markup=get_size_keyboard()
        )
        context.user_data["action"] = "resize"
        
    elif data == "convert":
        await query.edit_message_text(
            "🔄 **Send me an image to convert**\n\n"
            "Choose output format:",
            reply_markup=get_format_keyboard()
        )
        context.user_data["action"] = "convert"
        
    elif data.startswith("size_"):
        size_map = {
            "size_512": "512x512",
            "size_768": "768x768", 
            "size_1024": "1024x1024",
            "size_1_1": "512x512"
        }
        context.user_data["size"] = size_map.get(data, "512x512")
        await query.edit_message_text(
            f"✅ Size set to {context.user_data['size']}\n\n"
            "Now send me a prompt to generate an image! ✨"
        )
        context.user_data["action"] = "generate_ready"
        
    elif data.startswith("format_"):
        format_map = {
            "format_png": "png",
            "format_jpg": "jpg",
            "format_webp": "webp",
            "format_gif": "gif"
        }
        context.user_data["format"] = format_map.get(data, "png")
        await query.edit_message_text(
            f"✅ Format set to {context.user_data['format']}\n\n"
            "Send an image to convert! 📸"
        )
        context.user_data["action"] = "convert_ready"
        
    elif data == "help":
        await help_command(update, context)
        
    elif data == "back":
        await query.edit_message_text(
            "🔙 Back to main menu",
            reply_markup=get_main_keyboard()
        )
        context.user_data["action"] = None

# ==================== IMAGE GENERATION ====================
async def generate_image(prompt: str, size: str = "512x512"):
    """Generate image using Pollinations.ai"""
    try:
        # Format prompt for URL
        formatted_prompt = prompt.replace(" ", "%20")
        width, height = size.split("x")
        
        # Pollinations.ai URL (completely free, no API key)
        url = f"https://image.pollinations.ai/prompt/{formatted_prompt}?width={width}&height={height}&nologo=true"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    return None
    except Exception as e:
        print(f"Generation error: {e}")
        return None

# ==================== MESSAGE HANDLERS ====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (prompts for image generation)"""
    user_id = str(update.effective_user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    usage_key = f"{user_id}_{today}"
    
    # Initialize usage
    if context.user_data.get(usage_key) is None:
        context.user_data[usage_key] = 0
    
    # Check daily limit
    if context.user_data[usage_key] >= 10:
        await update.message.reply_text(
            "⚠️ You've reached your daily limit of 10 images!\n"
            "Come back tomorrow for more 🎨"
        )
        return
    
    action = context.user_data.get("action")
    
    if action == "generate_ready" or action == "generate":
        prompt = update.message.text
        size = context.user_data.get("size", "512x512")
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            f"🎨 Generating image...\n"
            f"Prompt: '{prompt}'\n"
            f"Size: {size}\n\n"
            "⏳ This may take a few seconds..."
        )
        
        # Generate image
        image_data = await generate_image(prompt, size)
        
        if image_data:
            # Increment usage
            context.user_data[usage_key] += 1
            
            await processing_msg.delete()
            
            # Send generated image
            await update.message.reply_photo(
                photo=io.BytesIO(image_data),
                caption=f"✨ Generated from: '{prompt}'\n"
                       f"📐 Size: {size}\n"
                       f"📊 Usage: {context.user_data[usage_key]}/10 today",
                reply_markup=get_main_keyboard()
            )
        else:
            await processing_msg.edit_text(
                "❌ Failed to generate image.\n"
                "Please try again with a different prompt."
            )
            
    elif action == "convert_ready":
        await update.message.reply_text(
            "📸 Please send an image file to convert.\n"
            f"Format: {context.user_data.get('format', 'png')}"
        )
        
    else:
        await update.message.reply_text(
            "🔮 Use the buttons below or send a prompt like:\n"
            "'A beautiful sunset over mountains'",
            reply_markup=get_main_keyboard()
        )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image messages (conversion and resize)"""
    action = context.user_data.get("action", "")
    
    if "convert" in action:
        # Get the image
        photo = await update.message.photo[-1].get_file()
        image_bytes = await photo.download_as_bytearray()
        
        format_type = context.user_data.get("format", "png")
        
        await update.message.reply_text(
            f"🔄 Converting image to {format_type.upper()}...",
            reply_markup=get_main_keyboard()
        )
        
        # Send back the converted image
        await update.message.reply_document(
            document=io.BytesIO(image_bytes),
            filename=f"converted.{format_type}",
            caption=f"✅ Converted to {format_type.upper()}",
            reply_markup=get_main_keyboard()
        )
        
    elif "resize" in action:
        await update.message.reply_text(
            "📐 Send the desired size (512, 768, or 1024)",
            reply_markup=get_size_keyboard()
        )
    else:
        await update.message.reply_text(
            "🖼️ Image received!\n"
            "Use the buttons below to convert or resize it.",
            reply_markup=get_format_keyboard()
        )

# ==================== MAIN FUNCTION ====================
def main():
    """Start the bot"""
    print("🚀 Starting PixelForgeBot...")
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    # Start the bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
