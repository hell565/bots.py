import json
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Состояния разговора
NAME, SUBJECT, PAYMENT_METHOD, READY = range(4)

# ID администратора
ADMIN_CHAT_ID = 6715030024  # Замените на ваш ID

# Словарь для хранения данных о пользователях
user_data = {}

# Функции для загрузки и сохранения данных
def load_data():
    global user_data
    try:
        with open('user_data.json', 'r', encoding='utf-8') as f:
            user_data = json.load(f)
    except FileNotFoundError:
        user_data = {}  # Если файл не найден, инициализируем пустой словарь

def save_data():
    with open('user_data.json', 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4, sort_keys=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.message.chat.id

    # Загружаем или инициализируем данные пользователя
    if str(chat_id) not in user_data:
        user_data[str(chat_id)] = {
            'name': None,
            'successful_orders': 0,
            'used_discount_chance': False,
            'current_discount': 0,  # Добавляем переменную для хранения текущей скидки
            'transactions': []  # Инициализируем список транзакций
        }

    # Проверяем существование пользователя
    if user_data[str(chat_id)]['name'] is not None:
        await update.message.reply_text(
            f"Добро пожаловать обратно, {user_data[str(chat_id)]['name']}! Выберите предмет: \n1. История\n2. Общество"
        )
        return SUBJECT
    else:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Новый пользователь начал диалог: {chat_id}")
        await update.message.reply_text("Привет! Добро пожаловать в нашего бота. Пожалуйста, введи свое имя:")
        return NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.message.chat.id
    user_info = user_data[str(chat_id)]

    user_info['name'] = update.message.text  # Запоминаем имя
    await update.message.reply_text(
        f"Спасибо, {user_info['name']}! Теперь выберите предмет: \n1. История\n2. Общество"
    )
    save_data()  # Сохраняем данные после ввода имени
    return SUBJECT

async def receive_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    subject = update.message.text.lower()
    chat_id = update.message.chat.id
    user_info = user_data.get(str(chat_id))

    if subject in ['история', 'общество']:
        user_info['subject'] = subject  # Сохраняем предмет
        
        # Определяем цену заказа
        price = 50 if user_info['successful_orders'] == 0 else 100
        
        # Применяем скидку, если она доступна
        if user_info['current_discount'] > 0:
            price *= (1 - user_info['current_discount'] / 100)

        await update.message.reply_text(
            f"Вы выбрали {subject.capitalize()}. Цена: {price:.2f} руб.\nВыберите способ платежа: Наличка или Перевод?"
        )
        save_data()  # Сохраняем данные после выбора предмета
        return PAYMENT_METHOD
    else:
        await update.message.reply_text("Пожалуйста, выберите валидный предмет: История или Общество.")
        return SUBJECT

async def payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    method = update.message.text.lower()
    chat_id = update.message.chat.id
    user_info = user_data.get(str(chat_id))

    # Определяем цену заказа перед добавлением транзакции
    price = 50 if user_info['successful_orders'] == 0 else 100

    # Применяем скидку, если она доступна
    if user_info['current_discount'] > 0:
        price *= (1 - user_info['current_discount'] / 100)

    if method in ['наличка', 'перевод']:
        transaction_info = {
            'subject': user_info['subject'],
            'method': method,
            'price': price
        }
        user_info['transactions'].append(transaction_info)  # Добавляем транзакцию в список
        save_data()  # Сохраняем данные после новой транзакции
        user_info['payment_method'] = method  # Обновляем метод оплаты в данных
        save_data()  # Сохраняем данные после выбора метода оплаты

        if method == 'перевод':
            await update.message.reply_text(
                f"Ваш заказ на {user_info['subject']} успешно оформлен. Платеж: {price:.2f} руб.\nДля перевода воспользуйтесь номером телефона: +79934163348.\nНапишите Готово, когда закончите."
            )
        else:  # если метод наличка
            await update.message.reply_text(
                f"Ваш заказ на {user_info['subject']} успешно оформлен. Платеж: {price:.2f} руб.\nНапишите Готово, когда закончите."
            )
        return READY
    else:
        await update.message.reply_text("Пожалуйста, выберите валидный способ платежа: Наличка или Перевод.")
        return PAYMENT_METHOD

async def random_discount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat.id
    user_info = user_data.get(str(chat_id))

    # Убедимся, что пользователь зарегистрирован
    if user_info is None or user_info['name'] is None:
        await update.message.reply_text("Пожалуйста, сначала зарегистрируйтесь, введя свое имя.")
        return

    # Скидка доступна только после двух успешных заказов
    if user_info['successful_orders'] >= 2:
        if not user_info['used_discount_chance']:
            discount = get_discount()  # Получаем случайную скидку
            await update.message.reply_text(f"Поздравляем! Вы получили скидку {discount}%.")
            user_info['used_discount_chance'] = True  # Устанавливаем, что шанс скидки использован
            user_info['current_discount'] = discount  # Применяем скидку на следующий заказ
        else:
            await update.message.reply_text("Вы уже использовали свой шанс на скидку.")
    else:
        await update.message.reply_text("Сначала выполните два успешных заказа для получения скидки.")

async def ready(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.message.chat.id
    user_info = user_data.get(str(chat_id))

    # Уведомляем администратора о готовности пользователя
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=f"Пользователь {user_info['name']} (ID: {chat_id}) готов. Цена: {100 if user_info['successful_orders'] > 0 else 50} руб.\nПожалуйста, подтвердите платеж.")
    
    # Увеличиваем счетчик успешных заказов
    user_info['successful_orders'] += 1
    
    # Если теперь у пользователя 2 успешные транзакции, напомнить ему о скидке
    if user_info['successful_orders'] == 2:
        await update.message.reply_text("Вы теперь можете получить скидку, введите команду /random.")
    
    await update.message.reply_text("Спасибо! Мы проверим ваш платеж и свяжемся с вами.")

    # Сохраняем данные после завершения взаимодействия
    save_data()  
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Отменено. Если хотите, начните снова с /start.')
    return ConversationHandler.END

async def show_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("У вас нет прав для просмотра транзакций.")
        return

    transactions_summary = "Транзакции:\n"
    for chat_id, info in user_data.items():
        transactions_summary += f"Пользователь: {info['name']} (ID: {chat_id})\n"
        transactions_summary += "\n".join([f"- Предмет: {trans['subject']}, Способ: {trans['method']}, Цена: {trans['price']} руб." for trans in info.get('transactions', [])])
        transactions_summary += "\n\n"

    await update.message.reply_text(transactions_summary)

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("У вас нет прав для подтверждения платежей.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("Пожалуйста, укажите имя пользователя.")
        return

    user_name = " ".join(context.args)  # Получаем имя пользователя

    # Находим chat_id пользователя по имени
    user_chat_id = None
    for chat_id, info in user_data.items():
        if info['name'].lower() == user_name.lower():  # Игнорируем регистр
            user_chat_id = chat_id
            break

    if user_chat_id is None:
        await update.message.reply_text("Пользователь не найден.")
        return

    user_info = user_data[user_chat_id]

    # Подтверждаем платеж и уведомляем пользователя
    await update.message.reply_text(f"Платеж от {user_info['name']} (ID: {user_chat_id}) подтвержден. Спасибо за покупку!")
    
    # Обновляем информацию о платеже
    user_info['payment_confirmed'] = True
    save_data()  # Сохраняем данные после подтверждения платежа

def get_discount():
    """Возвращает случайную скидку от 10% до 100%"""
    discounts = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    return random.choice(discounts)

def main() -> None:
    load_data()  # Загружаем данные при старте

    # Создаем приложение бота
    app = ApplicationBuilder().token('7769564092:AAFoYInPOP3W7mMKrK1LRdLdYBl4PqwKU40').build()  # Замените на ваш токен бота

    # Создаем обработчик состояний разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_subject)],
            PAYMENT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_method)],
            READY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ready)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('random', random_discount))  # Обработчик для новой команды
    app.add_handler(CommandHandler('trans', show_transactions))  # Обработчик для показа транзакций
    app.add_handler(CommandHandler('confirm_payment', confirm_payment))  # Команда для подтверждения платежа

    # Запускаем бота
    app.run_polling()

if __name__ == '__main__':
    main()
