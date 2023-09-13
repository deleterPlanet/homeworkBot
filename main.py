import telebot
from telebot import types
import sqlite3
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import config

load_dotenv()

bot = telebot.TeleBot(token=os.environ.get("TOKEN"))


@bot.message_handler(commands=["start"])
def main(message):
    user_name = f"{message.from_user.last_name} {message.from_user.first_name}"

    conn = sqlite3.connect("data.sql")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, name varchar(50))")

    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    flag = 1
    for user in users:
        flag *= user_name != user[1]
    if flag:
        cur.execute("INSERT INTO users(name) VALUES('%s')" % user_name)

    conn.commit()
    cur.close()
    conn.close()

    markup = types.InlineKeyboardMarkup()
    btn_schedule = types.InlineKeyboardButton("Расписание", callback_data="schedule")
    btn_homework = types.InlineKeyboardButton("Д/з", callback_data="homework")
    markup.row(btn_schedule, btn_homework)
    if user_name == config.ADMIN_NAME:
        markup.add(types.InlineKeyboardButton("Список пользователей", callback_data="users"))

    bot.send_message(message.chat.id,
                     f"Привет {user_name}", reply_markup=markup)


@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data == "schedule":
        try:
            html = requests.get(config.SCHEDULE_URL).text
            root = BeautifulSoup(html, "lxml")

            schedule_link = root.find(name="a", string="201–220, 241-242").get("href")

            open("files/cmc.pdf", "wb").write(requests.get(schedule_link, allow_redirects=True).content)
            schedule = open("files/cmc.pdf", "rb")

            bot.send_document(callback.message.chat.id, schedule)

            schedule.close()
        except Exception as e:
            bot.send_message(callback.message.chat.id, f"{e}")
    elif callback.data == "homework":
        bot.send_message(callback.message.chat.id, "Домашки нет")
    elif callback.data == "users":
        conn = sqlite3.connect("data.sql")
        cur = conn.cursor()

        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        users_list = ""
        for user in users:
            users_list += f"{user[1]}\n"

        bot.send_message(callback.message.chat.id, users_list)

        cur.close()
        conn.close()


@bot.message_handler()
def info(message):
    if message.text.lower() == "id":
        bot.reply_to(message, f"ID: {message.from_user.id}")


bot.polling(none_stop=True)
