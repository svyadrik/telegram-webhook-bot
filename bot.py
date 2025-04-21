import os
import logging
from flask import Flask, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ChannelPostHandler,
    ContextTypes,
    filters,
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === ИНИЦИАЛИЗАЦИЯ ===
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH

# === Google Sheets ===
if "GOOGLE_CREDS" in os.environ:
    with open("credentials.json", "w") as f:
        f.write(os.environ["GOOGLE_CREDS"])

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
GSHEET = gspread.authorize(CREDS)
SHEET = GSHEET.open("Заказы Бутер").worksheet("Лист1")

# === Telegram Application ===
application = ApplicationBuilder().token(TOKEN).build()
user_state = {}

# === ОБРАБОТЧИКИ ===

# 🔸 Обработка постов в канале
async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and (update.channel_post.caption or update.channel_post.text):
        keyboard = [[InlineKeyboardButton("🛒 Замовити", callback_data="order")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=update.channel_post.chat_id,
                message_id=update.channel_post.message_id,
                reply_markup=reply_markup
            )
            logging.info("✅ Кнопка успешно добавлена к посту.")
        except Exception as e:
            logging.error(f"❌ Не вдалося додати кнопку: {e}")

# 🔸 Обработка нажатия кнопки
async def order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    product = query.message.caption or query.message.text or "Без назви"
    user_state[user_id] = {"product": product}
    await query.message.reply_text("Введіть, будь ласка, кількість товару:")

# 🔸 Обработка ввода количества
async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_state:
        user_state[user_id]["quantity"] = update.message.text
        data = user_state[user_id]
        SHEET.append_row([data["product"], data["quantity"]])
        await update.message.reply_text("✅ Дякуємо! Ваше замовлення прийнято.")
        del user_state[user_id]

# 🔸 Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот працює через Webhook!")

# === Webhook ===
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook_handler():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    application.update_queue.put_nowait(update)
    return "OK"

# === Установить Webhook и запустить Flask ===
async def setup_webhook():
    await application.bot.set_webhook(url=WEBHOOK_URL)

# === Регистрация ===
application.add_handler(ChannelPostHandler(channel_post_handler))  # 🔥 ключевой момент
application.add_handler(CallbackQueryHandler(order_handler, pattern="^order$"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity))
application.add_handler(CommandHandler("start", start))

# === Запуск ===
if __name__ == "__main__":
    import asyncio
    asyncio.run(setup_webhook())
    app.run(host="0.0.0.0", port=8080)
