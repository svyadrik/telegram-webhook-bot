import subprocess
import sys

# 💥 Установка нужной версии python-telegram-bot
subprocess.run([sys.executable, "-m", "pip", "install", "python-telegram-bot==21.1.1"])

# 🚀 Запуск основного бота
subprocess.run([sys.executable, "bot.py"])
