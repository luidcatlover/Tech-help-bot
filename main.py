import telebot
from telebot import TeleBot
from config import TOKEN
from config import ADMINS as BASE_ADMINS
from logic import DB_Manager
import json
import os
import sqlite3
from config import HEAD_ADMIN

bot = TeleBot(TOKEN)
db = DB_Manager('support.db')
db.create_tables()

ADMINS_FILE = "admins.json"

def load_admins():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return BASE_ADMINS.copy()  # копия списка из config.py

def save_admins(admins):
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(admins, f, ensure_ascii=False, indent=2)

# Загрузка списка админов
ADMINS = load_admins()


@bot.message_handler(commands=["start"])
def startmessage(message):
    db.add_user(message.from_user.id, message.from_user.first_name)
    bot.send_message(message.chat.id, '''Я - бот поддержки магазина "Продаем все на свете",
                     Мои команды:
                     /report - обратная связь, чтобы сделать запрос, который позже будет передан специалистам
                     /faq - для ответов на часто задаваемые вопросы
                     /requests - если вы администратор, и хотите посмотреть запросы
                     /addadmin - если вы администратор и хотите добавить нового администратора
                     /deladmin - если вы владелец и хотите удалить другого администратора
                     /showadmin - если вы администратор и хотите посмотреть список других администраторов''')

@bot.message_handler(commands=["faq"])
def freq_ask_que(message):
    bot.send_message(message.chat.id, '''Вопрос: Как оформить заказ?
Ответ: Для оформления заказа, пожалуйста, выберите интересующий вас товар и нажмите кнопку "Добавить в корзину", затем перейдите в корзину и следуйте инструкциям для завершения покупки.

Вопрос: Как узнать статус моего заказа?
Ответ: Вы можете узнать статус вашего заказа, войдя в свой аккаунт на нашем сайте и перейдя в раздел "Мои заказы". Там будет указан текущий статус вашего заказа.

Вопрос: Как отменить заказ?
Ответ: Если вы хотите отменить заказ, пожалуйста, свяжитесь с нашей службой поддержки как можно скорее. Мы постараемся помочь вам с отменой заказа до его отправки.

Вопрос: Что делать, если товар пришел поврежденным?
Ответ: При получении поврежденного товара, пожалуйста, сразу свяжитесь с нашей службой поддержки и предоставьте фотографии повреждений. Мы поможем вам с обменом или возвратом товара.

Вопрос: Как связаться с вашей технической поддержкой?
Ответ: Вы можете связаться с нашей технической поддержкой через телефон на нашем сайте или написать нам в чат-бота.

Вопрос: Как узнать информацию о доставке?
Ответ: Информацию о доставке вы можете найти на странице оформления заказа на нашем сайте. Там указаны доступные способы доставки и сроки.
''')

@bot.message_handler(commands=["report"])
def report_comm(message):
    tg_id = message.from_user.id
    if db.can_user_send_request(tg_id) == False:
        bot.send_message(message.chat.id, "Вы можете отправлять запрос только раз в час. Попробуйте позже.")
        return
    messag = bot.send_message(message.chat.id, "Введите ваш запрос.")
    bot.register_next_step_handler(messag, process_report)

def process_report(message):
    text = message.text
    tg_id = message.from_user.id
    db.add_request(tg_id, text)
    bot.send_message(message.chat.id, "Ваш запрос принят и передан специалистам. Спасибо!")

@bot.message_handler(commands=["requests"])
def show_rights(message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")
        return
    
    requests = db.get_all_requests()

    if not requests:
        bot.send_message(message.chat.id, "Пока нет ни одного запроса.")
        return
        
    response = "Список запросов:\n\n"
    for req_id, name, text, created in requests[:20]:  # последние 20 запросов
        response += f"Номер: {req_id} | Пользователь: {name}\nДата: {created}\nЗапрос: {text}\n\n"

    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=["addadmin"])
def add_admin(message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        bot.send_message(message.chat.id, "У вас отсутствуют права на добавление нового администратора")
        return

    msg = bot.send_message(message.chat.id, "Введите ID пользователя, которого нужно сделать администратором.")
    bot.register_next_step_handler(msg, new_admin)

def new_admin(message):
    global ADMINS
    try:
        new_admin_id = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Неккоректный ID, нужно ввести число.")
        return
    
    if new_admin_id in ADMINS:
        bot.send_message(message.chat.id, "Ошибка, пользователь уже является администратором.")
        return
    
    ADMINS.append(new_admin_id)
    save_admins(ADMINS)
    bot.send_message(message.chat.id, f"Пользователь с ID {new_admin_id} добавлен в список администраторов.")

@bot.message_handler(commands=["deladmin"])
def del_admin(message):
    if message.from_user.id != HEAD_ADMIN:
        bot.send_message(message.chat.id, "Недостаточно прав.")
        return

    msg = bot.send_message(message.chat.id, "Введите ID администратора, которого нужно удалить:")
    bot.register_next_step_handler(msg, process_remove_admin)

def process_remove_admin(message):
    global ADMINS
    try:
        remove_id = int(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "Некорректный ID. Нужно ввести число.")
        return

    if remove_id not in ADMINS:
        bot.send_message(message.chat.id, "Пользователь не является администратором.")
        return

    if remove_id == HEAD_ADMIN:
        bot.send_message(message.chat.id, "Вы не можете удалить главного администратора.")
        return

    ADMINS.remove(remove_id)
    save_admins(ADMINS)
    bot.send_message(message.chat.id, f"Пользователь с ID {remove_id} удалён из списка администраторов.")

@bot.message_handler(commands=['showadmin'])
def show_admins(message):
    user_id = message.from_user.id
    if user_id not in ADMINS and user_id != HEAD_ADMIN:
        bot.send_message(message.chat.id, "Только администраторы могут просматривать список.")
        return
    
    conn = sqlite3.connect(db.database)
    with conn:
        main_admin_name = conn.execute("SELECT name FROM users WHERE id = ?", (HEAD_ADMIN,)).fetchone()
    main_admin_name = main_admin_name[0] if main_admin_name else "Неизвестно"

    admin_list_text = ""
    conn = sqlite3.connect(db.database)
    with conn:
        for admin_id in ADMINS:
            name = conn.execute("SELECT name FROM users WHERE id = ?", (admin_id,)).fetchone()
            name = name[0] if name else "Неизвестно"
            admin_list_text += f"ID: {admin_id} | Пользователь: {name}\n"

    response = f"Главные администраторы:\nID: {HEAD_ADMIN} | Пользователь: {main_admin_name}\n\n" \
               f"Администраторы:\n{admin_list_text if admin_list_text else 'Пока нет администраторов.'}"

    bot.send_message(message.chat.id, response)


bot.infinity_polling()