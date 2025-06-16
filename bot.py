
import os
import logging
from telegram import Update, ReplyKeyboardMarkup, Document
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from utils.fill_template import generate_contract_pdf
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = 527005102

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не найден.")

# Состояния
(FIO, PASSPORT, INN, ADDRESS, PHONE, EMAIL, SERVICE, POWER) = range(8)

user_data = {}
with open("pricing.json", "r", encoding="utf-8") as f:
    pricing = json.load(f)
services = list(pricing.keys())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text("Привет! Введите ФИО:")
    # Уведомление админу
    if ADMIN_ID:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 @{user.username or user.full_name} начал оформление"
🕒 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
    return FIO

async def get_fio(update, context): user_data["ФИО"] = update.message.text; await update.message.reply_text("Паспортные данные:"); return PASSPORT
async def get_passport(update, context): user_data["ПАСПОРТ"] = update.message.text; await update.message.reply_text("ИНН:"); return INN
async def get_inn(update, context): user_data["ИНН"] = update.message.text; await update.message.reply_text("Адрес регистрации:"); return ADDRESS
async def get_address(update, context): user_data["АДРЕС"] = update.message.text; await update.message.reply_text("Телефон:"); return PHONE
async def get_phone(update, context): user_data["ТЕЛЕФОН"] = update.message.text; await update.message.reply_text("Электронная почта:"); return EMAIL
async def get_email(update, context):
    user_data["EMAIL"] = update.message.text
    markup = ReplyKeyboardMarkup([[s] for s in services], one_time_keyboard=True)
    await update.message.reply_text("Выберите услугу:", reply_markup=markup)
    return SERVICE

async def get_service(update, context):
    service = update.message.text
    user_data["УСЛУГА"] = service
    if pricing[service]["type"] == "per_kwt":
        await update.message.reply_text("Введите мощность (кВт):")
        return POWER
    else:
        user_data["МОЩНОСТЬ"] = ""
        return await generate_and_send(update, context)

async def get_power(update, context):
    user_data["МОЩНОСТЬ"] = update.message.text
    return await generate_and_send(update, context)

async def generate_and_send(update, context):
    file_path = generate_contract_pdf(user_data)
    await update.message.reply_document(open(file_path, "rb"), filename=os.path.basename(file_path))
    await update.message.reply_text("Пожалуйста, подпишите PDF и отправьте обратно.")
    return ConversationHandler.END

async def receive_signed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document:
        doc: Document = update.message.document
        file = await doc.get_file()
        os.makedirs("signed", exist_ok=True)
        path = f"signed/{doc.file_name}"
        await file.download_to_drive(path)
        await context.bot.send_document(chat_id=ADMIN_ID, document=open(path, "rb"),
                                        caption="📄 Подписанный договор")
        await update.message.reply_text("Спасибо! Договор отправлен.")
    else:
        await update.message.reply_text("Пожалуйста, отправьте PDF.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fio)],
            PASSPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_passport)],
            INN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_inn)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_service)],
            POWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_power)],
        },
        fallbacks=[]
    )
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.Document.PDF, receive_signed))
    app.run_polling()

if __name__ == "__main__":
    main()
