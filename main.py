# -*- coding: utf-8 -*-

from selenium import webdriver
import http.client as http
import telebot.types as types
import config, urllib, re, time, telebot

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
    "Host": "www.lode.by",
    "Connection": "keep-alive",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "*/*",
    "Origin": "https://www.lode.by",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://www.lode.by/"}

order = {}

bot = telebot.TeleBot(config.token)

def checkContact(message):
    if message.contact == None:
        return False
    if message.contact.user_id == message.from_user.id and re.search("^\+*(375){1}[0-9]{9}", message.contact.phone_number):
        return True
    return False

#sending request to site
def send(value, message):
    driver = webdriver.Chrome()
    driver.get("https://www.lode.by/")

    town = driver.find_element_by_id("form-app-city")
    town.send_keys(value['city'])

    doctor = driver.find_element_by_id("form-app-doctor")
    doctor.send_keys(value['doctor'])

    name = driver.find_element_by_id("form-app-name")
    name.send_keys(value['name'])

    tel_code = driver.find_element_by_id("form-app-code")
    tel_code.send_keys(value['tel-code'])

    tel = driver.find_element_by_id("form-app-tel")
    tel.send_keys(value['tel'])

    submit = driver.find_element_by_class_name("btn-send")
    submit.click()

    time.sleep(3)

    response = driver.find_element_by_class_name("form-note-response")
    if response.text == "Ваша заявка принята. В течение часа с Вами свяжется оператор.":
        bot.send_message(message.chat.id, response.text)
    else:
        bot.send_message(message.chat.id, "Возникла ошибка. Повторите попытку /new")
    
    driver.close()

#Checking if this is a name
def addInfo(message):
    if message.text == None:
        return False
    if message.text != "Отправить" and re.search("^[А-Я]+[а-я]+$", message.text):
        return True
    return False

#Adding user to prevent error
def addUser(message):
    if message.chat.id not in order.keys():
        order[message.chat.id]={}

#Checking if message is from button
def check(message):
    if message.text in config.phones or message.text in config.towns or message.text in config.doctors:
        return True
    return False

#On start command sending hello message to user
@bot.message_handler(commands = ['start'])
def start(message):
    addUser(message)
    bot.send_message(message.chat.id, "Вас приветсвует бот, который будет отправлять запрос в медицинскый центр ЛОДЭ, и Вам не придется заходить на сайт для записи. Для начала напишите /new")

#On new sending starting dialog
@bot.message_handler(commands = ['new'])
def addButton(message):
    addUser(message)
    keyboard = types.ReplyKeyboardMarkup(row_width = 3, resize_keyboard = True, one_time_keyboard = True)
    Minsk = types.KeyboardButton(text = "Минск")
    Brest = types.KeyboardButton(text = "Брест")
    Grodno = types.KeyboardButton(text = "Гродно")
    keyboard.add(Minsk, Brest, Grodno)
    bot.send_message(message.chat.id, "Выберете свой город из предложеных вариантов", reply_markup = keyboard)

#If sended info command
@bot.message_handler(commands=['info'])
def info(message):
    addUser(message)
    ans = "Город: "
    if 'town' in order[message.chat.id].keys():
        ans+=order[message.chat.id]['town']
    else:
        ans+="Нет инфорации"
    ans+=". Врач: "
    if 'doctor' in order[message.chat.id].keys():
        ans+=order[message.chat.id]['doctor']
    else:
        ans+="Нет инфорации"
    ans+=". Имя: "
    if 'name' in order[message.chat.id].keys():
        ans+=order[message.chat.id]['name']
    else:
        ans+="Нет инфорации"
    ans+=". Код оператора: "
    if 'phone_code' in order[message.chat.id].keys():
        ans+=order[message.chat.id]['phone_code']
    else:
        ans+="Нет инфорации"
    ans+=". Телефон: "
    if 'phone' in order[message.chat.id].keys():
        ans+=order[message.chat.id]['phone']
    else:
        ans+="Нет инфорации"
    ans+="."
    bot.send_message(message.chat.id, ans)

#If sended some info
@bot.message_handler(func = check)
def Answer(message):
    addUser(message)
    if message.text in config.towns:
        order[message.chat.id]['town'] = message.text
        keyboard = types.ReplyKeyboardMarkup(row_width = 2, one_time_keyboard = True, resize_keyboard = True)
        for i in range(len(config.doctors)):
            button = types.KeyboardButton(text = config.doctors[i])
            keyboard.add(button)
        bot.send_message(message.chat.id, "Выберите врача", reply_markup = keyboard)
    elif message.text in config.phones:
        order[message.chat.id]['phone_code'] = message.text
        keyboard = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Напишите свой телефон (последние 7 цифр)", reply_markup=keyboard)
    elif message.text in config.doctors:
        order[message.chat.id]['doctor'] = message.text
        keyboard = types.ReplyKeyboardMarkup(row_width = len(config.phones), one_time_keyboard = True, resize_keyboard = True)
        button = types.KeyboardButton(text="Отправить свой номер телефона в Telegram", request_contact=True)
        keyboard.add(button)
        for i in range(len(config.phones)):
            button = types.KeyboardButton(text = config.phones[i])
            keyboard.add(button)
        bot.send_message(message.chat.id, "Выберите код оператора вашего телефона", reply_markup = keyboard)

#If sended phone number
@bot.message_handler(regexp="^[0-9]{7}$")
def Phone(message):
    addUser(message)
    order[message.chat.id]['phone'] = message.text
    bot.send_message(message.chat.id, "Пришлите свое имя")

#If sended name
@bot.message_handler(func = addInfo)
def Name(message):
    addUser(message)
    order[message.chat.id]['name'] = message.text
    bot.send_message(message.chat.id, "Имя изменено.")
    for i in range(len(config.allkeys)):
        if config.allkeys[i] not in order[message.chat.id].keys():
            bot.send_message(message.chat.id, "Приносим извенения, но, видимо, в системе произошел сбой пока вы регистрировались, пожайлста напишите /new для прохождения регистрации заново. Спасибо за понимание.")
            return 0
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard = True)
    button = types.KeyboardButton(text = "Отправить")
    keyboard.add(button)
    bot.send_message(message.chat.id, "Проверьте информацию ниже и нажмите кнопку отправить.", reply_markup=keyboard)
    info(message)

@bot.message_handler(content_types = ['contact'], func = checkContact)
def addPhone(message):
    addUser(message)
    if message.contact.phone_number[0] == '+':
        order[message.chat.id]['phone_code'] = "0" + message.contact.phone_number[4:6]
        order[message.chat.id]['phone'] = message.contact.phone_number[6:]
    else:
        order[message.chat.id]['phone_code'] = "0" + message.contact.phone_number[3:5]
        order[message.chat.id]['phone'] = message.contact.phone_number[5:]
    keyboard = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Отправьте свое имя", reply_markup=keyboard)

#Author message
@bot.message_handler(commands=['author'])
def author(message):
    bot.send_message(message.chat.id, "@VadVergasov разрабработал данный бот. Вы можете ему также писать о любых неисправностях данного бота.")

#All other messages
@bot.message_handler()
def Ans(message):
    if message.text != "Отправить":
        print(message.text)
        return 0
    for i in range(len(config.allkeys)):
        if config.allkeys[i] not in order[message.chat.id].keys():
            bot.send_message(message.chat.id, "Приносим извенения, но, видимо, в системе произошел сбой пока вы регистрировались, пожайлста напишите /new для прохождения регистрации заново. Спасибо за понимание.")
            return 0
    keyboard = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Запрос отправляется", reply_markup=keyboard)
    values = {"doctor": order[message.chat.id]['doctor'],
        "name": order[message.chat.id]['name'],
        "tel-code": order[message.chat.id]['phone_code'],
        "tel": order[message.chat.id]['phone'],
        "city": order[message.chat.id]['town']}
    send(values, message)

@bot.message_handler(content_types=['contact'])
def log(message):
    print(message.contact)

if __name__ == '__main__':
    bot.polling(none_stop = True, timeout = 5)