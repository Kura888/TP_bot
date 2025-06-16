import os
from aiogram import Bot, Dispatcher
from aiogram.utils.executor import start_webhook

# Явная проверка токена
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    raise RuntimeError("Токен бота не найден! Проверьте переменные окружения.")

print(f"Бот запускается с токеном: {TOKEN[:5]}...")  # Логируем начало токена для проверки

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Конфигурация вебхука
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', f"https://your-service-name.onrender.com{WEBHOOK_PATH}")
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.environ.get('PORT', 8080))

@dp.message_handler(commands=['start'])
async def start(message):
    await message.answer("✅ Бот успешно запущен!")

async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown(dp):
    await bot.delete_webhook()
    print("Бот остановлен")

if __name__ == '__main__':
    print("Запуск вебхука...")
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT
    )
