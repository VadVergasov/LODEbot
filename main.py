# -*- coding: utf-8 -*-
"""
Main program
Copyright (C) 2021 Vadim Vergasov

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import json
import re
import time

import requests
import telebot
import telebot.types as types
from lxml import etree, html

order = {}

with open("CONFIG.json", "r") as f:
    CONFIG = json.load(f)

bot = telebot.TeleBot(CONFIG["token"])

# check contact holder
def checkContact(message):
    if message.contact == None:
        return False
    if message.contact.user_id == message.from_user.id and re.search(
        r"^\+*(375){1}[0-9]{9}", message.contact.phone_number
    ):
        return True
    return False


def update_info(message):
    order[message.chat.id] = dict()
    order[message.chat.id]["session"] = requests.Session()
    cities = list()
    doctors = dict()
    request = order[message.chat.id]["session"].get(
        "https://www.lode.by/local/include/ajax/modals/order.php"
    )
    tree = html.fromstring(request.text)
    for city in tree.xpath(
        "/html/body/div/div[2]/div/div[2]/div[2]/form/div[1]/div/div"
    ):
        cities.append(city.xpath("div/text()")[0])
    for doctor in tree.xpath(
        "/html/body/div/div[2]/div/div[2]/div[2]/form/div[2]/div/div/div"
    ):
        doctors[doctor.xpath("text()")[0]] = doctor.xpath("@data-value")[0]
    with open("CONFIG.json", "w") as f:
        CONFIG["doctors"] = doctors
        CONFIG["cities"] = cities
        json.dump(CONFIG, f)


# sending request to site
def send(message):
    payload = {
        "FIELD[BACTIVE]": "Y",
        "bxajaxid": "ef5c9efae1eb3ead24f337ae0159d28f",
        "PROPERTY_VALUES[CITY]": "minsk",
        "PROPERTY_VALUES[SPECIALITY]": CONFIG["doctors"][
            order[message.chat.id]["doctor"]
        ],
        "PROPERTY_VALUES[NAME]": order[message.chat.id]["name"],
        "PROPERTY_VALUES[PHONE]": "+375 ("
        + order[message.chat.id]["phone"][:2]
        + ") "
        + order[message.chat.id]["phone"][2:5]
        + "-"
        + order[message.chat.id]["phone"][5:7]
        + "-"
        + order[message.chat.id]["phone"][7:9],
    }
    request = order[message.chat.id]["session"].post(
        "https://www.lode.by/local/include/ajax/modals/order.php",
        data=payload,
        headers={
            "cookie": "PHPSESSID=1c0hqnk30tf2gngndc73ke3112; BITRIX_SM_GUEST_ID=4759080; BX_USER_ID=ffbe270d39cef7f3f0ff4baff8dcda4b; tmr_lvid=176412c1040d142b81fec60793f613e1; tmr_lvidTS=1611601365855; _ga=GA1.2.242664909.1611601366; _gid=GA1.2.854671214.1611601366; _gat=1; _gat_gtag_UA_12321089_43=1; BITRIX_CONVERSION_CONTEXT_s1=%7B%22ID%22%3A2%2C%22EXPIRE%22%3A1611608340%2C%22UNIQUE%22%3A%5B%22conversion_visit_day%22%5D%7D; _ym_uid=1611601366569007027; _ym_d=1611601366; _ym_isad=2; _ym_visorc_31429678=w; _fbp=fb.1.1611601366592.1667600775; tmr_detect=0%7C1611601368238; BITRIX_SM_LAST_VISIT=25.01.2021+22%3A02%3A51; tmr_reqNum=4",
        },
    )
    tree = html.fromstring(request.text)
    if len(tree.xpath("//div[@class='text-success']")):
        bot.reply_to(message, "Заявка отправлена успешно!")
    else:
        bot.reply_to(message, "Повторите попытку позже.")


# Checking if this is a name
def addInfo(message):
    if message.text == None:
        return False
    if message.text != "Отправить" and re.search("^[А-Я]+[а-я]+$", message.text):
        return True
    return False


# Adding user to prevent error
def addUser(message):
    if message.chat.id not in order.keys():
        order[message.chat.id] = {}


# Checking if message is from button
def check(message):
    if message.text in CONFIG["cities"] or message.text in CONFIG["doctors"]:
        return True
    return False


@bot.message_handler(commands=["test"])
def test(message):
    print(
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name,
    )


# On start command sending hello message to user
@bot.message_handler(commands=["start"])
def start(message):
    addUser(message)
    bot.send_message(
        message.chat.id,
        "Вас приветсвует бот, который будет отправлять запрос в медицинскый центр ЛОДЭ, и Вам не придется заходить на сайт для записи. Для начала напишите /new",
    )


# On cancel command
@bot.message_handler(commands=["cancel"])
def Cancel(message):
    order[message.chat.id] = {}
    bot.send_message(
        message.chat.id, "Ваша информация сброшена. Для записи нажмите на /new"
    )


# On new sending starting dialog
@bot.message_handler(commands=["new"])
def addButton(message):
    update_info(message)
    addUser(message)
    keyboard = types.ReplyKeyboardMarkup(
        row_width=3, resize_keyboard=True, one_time_keyboard=True
    )
    for city in CONFIG["cities"]:
        button = types.KeyboardButton(text=city)
        keyboard.add(button)
    bot.send_message(
        message.chat.id,
        "Выберете свой город из предложеных вариантов",
        reply_markup=keyboard,
    )


# If sended info command
@bot.message_handler(commands=["info"])
def info(message):
    addUser(message)
    ans = "Город: "
    if "city" in order[message.chat.id].keys():
        ans += order[message.chat.id]["city"]
    else:
        ans += "Нет инфорации"
    ans += ". Врач: "
    if "doctor" in order[message.chat.id].keys():
        ans += order[message.chat.id]["doctor"]
    else:
        ans += "Нет инфорации"
    ans += ". Имя: "
    if "name" in order[message.chat.id].keys():
        ans += order[message.chat.id]["name"]
    else:
        ans += "Нет инфорации"
    ans += ". Телефон: "
    if "phone" in order[message.chat.id].keys():
        ans += order[message.chat.id]["phone"]
    else:
        ans += "Нет инфорации"
    ans += "."
    bot.send_message(message.chat.id, ans)


# If sended some info
@bot.message_handler(func=check)
def Answer(message):
    addUser(message)
    if message.text in CONFIG["cities"]:
        order[message.chat.id]["city"] = message.text
        keyboard = types.ReplyKeyboardMarkup(
            row_width=2, one_time_keyboard=True, resize_keyboard=True
        )
        for doctor in CONFIG["doctors"].keys():
            button = types.KeyboardButton(text=doctor)
            keyboard.add(button)
        bot.send_message(message.chat.id, "Выберите врача", reply_markup=keyboard)
    elif message.text in CONFIG["doctors"]:
        order[message.chat.id]["doctor"] = message.text
        keyboard = types.ReplyKeyboardMarkup(
            row_width=1, one_time_keyboard=True, resize_keyboard=True
        )
        button = types.KeyboardButton(
            text="Отправить свой номер телефона в Telegram", request_contact=True
        )
        keyboard.add(button)
        bot.send_message(
            message.chat.id,
            "Напишите свой телефон (последние 9 цифр)",
            reply_markup=keyboard,
        )


# If sended phone number
@bot.message_handler(regexp="^[0-9]{9}$")
def Phone(message):
    addUser(message)
    order[message.chat.id]["phone"] = message.text
    bot.send_message(message.chat.id, "Пришлите свое имя")


# If sended name
@bot.message_handler(func=addInfo)
def Name(message):
    addUser(message)
    order[message.chat.id]["name"] = message.text
    bot.send_message(message.chat.id, "Имя изменено.")
    for key in CONFIG["allkeys"]:
        if key not in order[message.chat.id].keys():
            bot.send_message(
                message.chat.id,
                "Приносим извенения, но, видимо, в системе произошел сбой пока вы регистрировались, пожайлста напишите /new для прохождения регистрации заново. Спасибо за понимание.",
            )
            return 0
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton(text="Отправить")
    keyboard.add(button)
    bot.send_message(
        message.chat.id,
        "Проверьте информацию ниже и нажмите кнопку отправить.",
        reply_markup=keyboard,
    )
    info(message)


@bot.message_handler(content_types=["contact"], func=checkContact)
def addPhone(message):
    addUser(message)
    if message.contact.phone_number[0] == "+":
        order[message.chat.id]["phone"] = message.contact.phone_number[6:]
    else:
        order[message.chat.id]["phone"] = message.contact.phone_number[5:]
    keyboard = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Отправьте свое имя", reply_markup=keyboard)


# Author message
@bot.message_handler(commands=["author"])
def author(message):
    bot.send_message(
        message.chat.id,
        "@VadVergasov разрабработал данный бот. Вы можете ему также писать о любых неисправностях данного бота.",
    )


# All other messages
@bot.message_handler()
def Ans(message):
    if message.text != "Отправить":
        print(message.text)
        return 0
    for i in range(len(CONFIG["allkeys"])):
        if CONFIG["allkeys"][i] not in order[message.chat.id].keys():
            bot.send_message(
                message.chat.id,
                "Приносим извенения, но, видимо, в системе произошел сбой пока вы регистрировались, пожайлста напишите /new для прохождения регистрации заново. Спасибо за понимание.",
            )
            return 0
    keyboard = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Запрос отправляется", reply_markup=keyboard)
    values = {
        "doctor": order[message.chat.id]["doctor"],
        "name": order[message.chat.id]["name"],
        "tel": order[message.chat.id]["phone"],
        "city": order[message.chat.id]["city"],
    }
    send(message)


@bot.message_handler(content_types=["contact"])
def log(message):
    print(message.contact)


if __name__ == "__main__":
    bot.polling(none_stop=True, timeout=120)
