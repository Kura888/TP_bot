import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.executor import start_webhook
from jinja2 import Template
import pdfkit
import tempfile

# Конфигурация
TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
EXPERT_CHAT_ID = "@ExpertEnergo"  # Или числовой ID чата
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.getenv('PORT', 8080))

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Шаблон договора (упрощенная версия из вашего файла)
CONTRACT_TEMPLATE = """
**Договор возмездного оказания услуг № {{номер}}**

г. Краснодар {{дата}}.

Индивидуальный предприниматель Куропятников Дмитрий Васильевич, ОГРНИП
324237500097030 от «11» марта 2024 г., выданным Межрайонной инспекцией
Федеральной налоговой службы № 16 по Краснодарскому краю, именуемый в
дальнейшем "Исполнитель", с одной стороны, и

**{{фио}} {{паспорт}} {{инн}} {{огрн}},** именуемый в
дальнейшем «Заказчик», с другой стороны, заключили настоящий договор:

1. **Предмет Договора**
   1. Исполнитель обязуется оказать услугу {{услуга}} до {{мощность}} кВт по адресу {{адрес}}.
   2. Стоимость услуг: {{стоимость}} рублей.

2. **Реквизиты и подписи Сторон**

Исполнитель:                           Заказчик:
___________________                    ___________________
Куропятников Д.В.                      {{фио}}

Дата: {{дата}}                         Дата: {{дата}}
"""

# Состояния для сбора данных
class FormStates:
    waiting_for_fio = 1
    waiting_for_passport = 2
    waiting_for_inn = 3
    waiting_for_ogrn = 4
    waiting_for_service = 5
    waiting_for_power = 6
    waiting_for_address = 7
    waiting_for_price = 8

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer("Добрый день! Давайте составим договор.\nВведите ваше ФИО:")
    await FormStates.waiting_for_fio.set()

@dp.message_handler(state=FormStates.waiting_for_fio)
async def process_fio(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['фио'] = message.text
    await message.answer("Введите паспортные данные (серия, номер, кем и когда выдан):")
    await FormStates.waiting_for_passport.set()

@dp.message_handler(state=FormStates.waiting_for_passport)
async def process_passport(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['паспорт'] = message.text
    await message.answer("Введите ИНН:")
    await FormStates.waiting_for_inn.set()

@dp.message_handler(state=FormStates.waiting_for_inn)
async def process_inn(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['инн'] = message.text
    await message.answer("Введите ОГРН (если есть):")
    await FormStates.waiting_for_ogrn.set()

@dp.message_handler(state=FormStates.waiting_for_ogrn)
async def process_ogrn(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['огрн'] = message.text
    await message.answer("Опишите услугу (например: 'подготовка документов для ТП'):")
    await FormStates.waiting_for_service.set()

@dp.message_handler(state=FormStates.waiting_for_service)
async def process_service(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['услуга'] = message.text
    await message.answer("Введите мощность (кВт):")
    await FormStates.waiting_for_power.set()

@dp.message_handler(state=FormStates.waiting_for_power)
async def process_power(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['мощность'] = message.text
    await message.answer("Введите адрес объекта:")
    await FormStates.waiting_for_address.set()

@dp.message_handler(state=FormStates.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['адрес'] = message.text
    await message.answer("Введите стоимость услуг (руб):")
    await FormStates.waiting_for_price.set()

@dp.message_handler(state=FormStates.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['стоимость'] = message.text
        data['дата'] = datetime.now().strftime('%d.%m.%Y')
        data['номер'] = datetime.now().strftime('%d%m%Y%H%M')
        
        # Генерация договора
        template = Template(CONTRACT_TEMPLATE)
        contract_html = template.render(data)
        
        # Создание временного PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            pdfkit.from_string(contract_html, tmp.name)
            
            # Отправка PDF пользователю
            with open(tmp.name, 'rb') as doc:
                await message.answer_document(
                    document=doc,
                    caption="Ваш договор готов!"
                )
            
            # Отправка PDF эксперту
            with open(tmp.name, 'rb') as doc:
                await bot.send_document(
                    chat_id=EXPERT_CHAT_ID,
                    document=doc,
                    caption=f"Новый договор от {data['фио']}\n№{data['номер']}"
                )
            
            os.unlink(tmp.name)
    
    await state.finish()

# Настройка вебхуков для Render
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()

if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path='/webhook',
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT
    )
