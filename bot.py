import os

# Вставляем credentials.json из переменной окружения
if "GOOGLE_CREDS" in os.environ:
    with open("credentials.json", "w") as f:
        f.write(os.environ["GOOGLE_CREDS"])
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH

# Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
GSHEET = gspread.authorize(CREDS)
SHEET = GSHEET.open("Заказы Бутер").worksheet("Лист1")

user_state = {}
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

application = ApplicationBuilder().token(TOKEN).build()

# Обработчик постов
async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.text:
        keyboard = [[InlineKeyboardButton("🛒 Замовити", callback_data="order")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=update.channel_post.chat_id,
                message_id=update.channel_post.message_id,
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.error(f"Не вдалося додати кнопку: {e}")

# Кнопка заказа
async def order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_state[user_id] = {"product": query.message.text}
    await query.message.reply_text("Введіть, будь ласка, кількість товару:")

# Ввод количества
async def handle_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_state:
        user_state[user_id]["quantity"] = update.message.text
        data = user_state[user_id]
        SHEET.append_row([data["product"], data["quantity"]])
        await update.message.reply_text("✅ Дякуємо! Ваше замовлення прийнято.")
        del user_state[user_id]

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот працює через Webhook!")

# Flask Webhook
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook_handler():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    application.update_queue.put_nowait(update)
    return "OK"

# Установка Webhook
async def setup_webhook():
    await application.bot.set_webhook(url=WEBHOOK_URL)

application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post_handler))
application.add_handler(CallbackQueryHandler(order_handler, pattern="^order$"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quantity))
application.add_handler(CommandHandler("start", start))

if __name__ == "__main__":
    import asyncio
    asyncio.run(setup_webhook())
    app.run(host="0.0.0.0", port=8080)