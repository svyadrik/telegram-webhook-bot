import os
import logging
from datetime import datetime
from flask import Flask, request
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация Flask
app = Flask(__name__)

# Google Sheets авторизация
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE)
GSHEET = gspread.authorize(CREDS)
worksheet = GSHEET.open("Заказы Бутер").worksheet("Лист1")

# Переменные среды
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH

# Telegram Application
application = ApplicationBuilder().token(TOKEN).build()
application.bot_data["worksheet"] = worksheet

# Обработка нажатия кнопки "Замовити"
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["step"] = "quantity"
    context.user_data["post_text"] = query.message.text_html
    await query.message.reply_text("Вкажіть кількість:")

# Обработка сообщений пользователя
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")

    if step == "quantity":
        context.user_data["quantity"] = update.message.text
        context.user_data["step"] = "phone"
        await update.message.reply_text("Тепер, будь ласка, вкажіть номер телефону:")

    elif step == "phone":
        quantity = context.user_data.get("quantity")
        phone = update.message.text
        user_name = update.message.from_user.full_name
        user_id = update.message.from_user.id
        product = context.user_data.get("post_text", "Без опису").split('\n')[0][:50]
        now = datetime.now().strftime("%d.%m.%Y %H:%M")

        worksheet = context.bot_data["worksheet"]
        worksheet.append_row([
            datetime.now().strftime("%d.%m.%Y"),
            user_name,
            user_id,
            product,
            quantity,
            phone,
            now,
            "Новий"
        ])

        context.user_data.clear()
        await update.message.reply_text("Дякуємо! Ваше замовлення прийнято ✅")
        await context.bot.send_message(chat_id=7333104516, text=f"Нове замовлення:\n{product}\n{quantity} шт\nТелефон: {phone}")

# Роутинг Webhook
@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        application.update_queue.put(update)
        return "OK"

# Регистрация обработчиков
application.add_handler(CallbackQueryHandler(button_handler, pattern="order"))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# Запуск Flask
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8443)
