#!/bin/bash
echo "🔥 Принудительная установка зависимостей..."
pip install python-telegram-bot==20.7 Flask==2.3.3 gspread==5.12.0 google-auth==2.28.1 oauth2client==4.1.3
pip freeze
