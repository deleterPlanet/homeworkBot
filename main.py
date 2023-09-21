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


@bot.message_handler(commands=["start", "menu"])
def main(message):
    user_name = f"{message.from_user.last_name} {message.from_user.first_name}"
    answer_text = "empty message"

    if message.text == "/start":
        answer_text = f"Привет {user_name}"

        conn = sqlite3.connect("data.sql")
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS users(id int auto_increment primary key, name varchar(50))")
        cur.execute("CREATE TABLE IF NOT EXISTS homeworks(id int auto_increment primary key,"
                    "class varchar(30), homework_text varchar(100), file_name varchar(50))")

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
    elif message.text == "/menu":
        answer_text = "Меню"

    markup = types.InlineKeyboardMarkup()
    btn_schedule = types.InlineKeyboardButton("Расписание", callback_data="schedule")
    btn_homework = types.InlineKeyboardButton("Д/з", callback_data="homework")
    markup.row(btn_schedule, btn_homework)
    if user_name == config.ADMIN_NAME:
        markup.add(types.InlineKeyboardButton("Список пользователей", callback_data="users"))

    bot.send_message(message.chat.id, answer_text, reply_markup=markup)


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
        markup = types.InlineKeyboardMarkup()

        conn = sqlite3.connect("data.sql")
        cur = conn.cursor()
        cur.execute("SELECT * FROM homeworks")
        homeworks = cur.fetchall()

        classes = [""]*len(homeworks)

        for i in range(len(homeworks)):
            classes[i] = homeworks[i][1]
        classes.sort()

        cur.close()
        conn.close()

        i = 0
        while i < len(classes):
            btn1 = types.InlineKeyboardButton(classes[i], callback_data=classes[i])
            while i+1 < len(classes) and classes[i] == classes[i+1]:
                i += 1
            if i+1 >= len(classes):
                markup.add(btn1)
                break
            btn2 = types.InlineKeyboardButton(classes[i+1], callback_data=classes[i+1])
            markup.row(btn1, btn2)
            i += 1
            while i+1 < len(classes) and classes[i] == classes[i+1]:
                i += 1
            if i == len(classes) - 1 and classes[i] == classes[i-1]:
                break

        bot.edit_message_reply_markup(callback.message.chat.id, callback.message.message_id, reply_markup=markup)
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
    elif callback.data.split('+')[0] == "delete_homework":
        homework_text = callback.data.split('+')[1]
        conn = sqlite3.connect("data.sql")
        cur = conn.cursor()
        cur.execute(f"DELETE FROM homeworks WHERE homework_text='%s'" % homework_text)

        conn.commit()
        cur.close()
        conn.close()
    else:
        conn = sqlite3.connect("data.sql")
        cur = conn.cursor()

        cur.execute("SELECT * FROM homeworks")
        homeworks = cur.fetchall()

        for homework in homeworks:
            if homework[1] == callback.data:
                bot.send_message(callback.message.chat.id, homework[2])
                file = open(f"files/{homework[3]}", "rb")
                bot.send_document(callback.message.chat.id, file)
                del_markup = types.InlineKeyboardMarkup()
                del_markup.add(types.InlineKeyboardButton("Удалить", callback_data=f"delete_homework+{homework[2]}"))
                bot.send_message(callback.message.chat.id, "-"*20, reply_markup=del_markup)
        cur.close()
        conn.close()


@bot.message_handler()
def info(message):
    if message.text.lower() == "id":
        bot.reply_to(message, f"ID: {message.from_user.id}")
    else:
        class_name = message.text.split('\n')[0].split()[0]
        file_name = message.text.split('\n')[0].split()[1]
        homework_text = message.text.split('\n')[1]
        homework_text = homework_text.lower()
        file_name = f"{file_name.lower()}.pdf"

        conn = sqlite3.connect("data.sql")
        cur = conn.cursor()
        cur.execute("INSERT INTO homeworks(class, homework_text, file_name) VALUES('%s', '%s', '%s')"
                    % (class_name, homework_text, file_name))
        conn.commit()
        cur.close()
        conn.close()

        bot.send_message(message.chat.id, "Сохранено")


if __name__ == "__main__":
    bot.polling(none_stop=True)
