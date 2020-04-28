import vk_api
import requests
import os
from make_board import create_board
import json
from database import check_id, add_users, use_prompt
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import random
from io import BytesIO
from screenshot import Map
from PIL import Image
import datetime

vk_session = vk_api.VkApi(
    token=TOKEN)
longpoll = VkBotLongPoll(vk_session, 194275944)
vk = vk_session.get_api()

COUNTER = 0
CORRECT = 0


def get_image():
    with open('cities.txt') as fi:
        cities = fi.read().split('\n')
    city = random.sample(cities, 1)
    while city in used_cities:
        city = random.sample(cities, 1)
    print(city)
    used_cities.append(city)
    n = Map()
    return n.draw_map(city)


def check_register(user_id):
    result = check_id(user_id)
    print(result)
    if result:
        res = True
    else:
        res = False
    return res


def photo(peer_id, user_id):
    global COUNTER, CORRECT
    COUNTER += 1
    if COUNTER > 15:
        text = f'Правильных ответов: {CORRECT} из 15'
        vk.messages.send(user_ids=user_id, message=text,
                         random_id=0, keyboard=json.dumps(keyboard_in_game))
        return
    photo = get_image()
    res = vk.photos.getMessagesUploadServer()
    Image.open(photo).save('result.jpg')
    create_board('result.jpg')
    b = requests.post(res["upload_url"], files={
                      "photo": open('result.jpg', 'rb')}).json()
    c = vk.photos.saveMessagesPhoto(
        photo=b["photo"], server=b["server"], hash=b["hash"])[0]
    res_photo = "photo{}_{}".format(c["owner_id"], c["id"])
    vk.messages.send(user_ids=user_id, peer_id=peer_id, message=f'Вопрос №{COUNTER} из {15}',
                     attachment=res_photo, random_id=0, keyboard=json.dumps(keyboard_in_game))
    os.remove('result.jpg')


def main():
    global COUNTER, CORRECT
    TOWN = False
    RIVER = False
    LEVEL = '-'
    ANSWER = 15
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            response = vk.users.get(user_ids=event.obj.message['from_id'],
                                    fields='city')
            text = event.obj.message['text'].lower()

            '''Проверка регистрации пользователя, в случае, если id пользователя
            отсутствует в базе данных - в БД добаляется id, имя, количество подсказок и время последнего обновления'''

            if check_register(event.obj.message['from_id']):
                pass
            else:
                nickname = response[0]['first_name'] + ' ' + \
                    response[0]['last_name'][0] + '.'
                time = datetime.datetime.now().timestamp()
                add_users(event.obj.message['from_id'], nickname, 5, int(time))
                vk.messages.send(user_id=event.obj.message['from_id'],
                                 message='Вы успешно зарегистрированы!',
                                 random_id=random.randint(0, 2 ** 64), keyboard=json.dumps(keyboard_main_menu))

            '''Обработка запросов пользователя'''

            if text.split()[0] == 'отменить':
                LEVEL = '-'
                TOWN = False
                RIVER = False
                COUNTER = 0
                CORRECT = 0
                used_cities.clear()
                vk.messages.send(user_id=event.obj.message['from_id'],
                                 message='Вы успешно вышли из игры!',
                                 random_id=random.randint(0, 2 ** 64), keyboard=json.dumps(keyboard_main_menu))
            elif text == 'города':
                vk.messages.send(user_id=event.obj.message['from_id'],
                                 message='Выберите сложность: ',
                                 random_id=random.randint(0, 2 ** 64), keyboard=json.dumps(keyboard_level))
                TOWN = True
            elif TOWN and LEVEL == '-':
                LEVEL = text
                photo(event.object.peer_id, event.obj.message['from_id'])
            elif text.split()[0] == 'подсказка':
                print(used_cities[-1][0])
                length = len(used_cities[-1][0])
                string = length * '_ '
                ok = use_prompt(event.obj.message['from_id'])
                if ok == -1:
                    messag = 'У вас больше нет подсказок'
                    vk.messages.send(user_id=event.obj.message['from_id'],
                                     message=messag,
                                     random_id=random.randint(0, 2 ** 64), keyboard=json.dumps(keyboard_in_game))
                else:
                    messag = f'У вас осталось {ok} подсказок'
                    vk.messages.send(user_id=event.obj.message['from_id'],
                                     message=f'Подсказка &#128161;: {string}\n{messag}',
                                     random_id=random.randint(0, 2 ** 64), keyboard=json.dumps(keyboard_in_game))
            elif text == 'пропустить':
                photo(event.object.peer_id, event.obj.message['from_id'])
            elif TOWN and (LEVEL == 'лёгкий' or LEVEL == 'сложный'):
                if text == used_cities[-1][0].lower():
                    vk.messages.send(user_id=event.obj.message['from_id'],
                                     message=f'Верно!',
                                     random_id=random.randint(0, 2 ** 64), keyboard=json.dumps(keyboard_in_game))
                    CORRECT = CORRECT + 1
                    photo(event.object.peer_id, event.obj.message['from_id'])
                else:
                    vk.messages.send(user_id=event.obj.message['from_id'],
                                     message=f'Неправильно! Вы можете воспользоваться подсказкой или пропустить вопрос.',
                                     random_id=random.randint(0, 2 ** 64), keyboard=json.dumps(keyboard_in_game))


'''
Клавиатура, которая активируется при выборе уровня сложности
'''
keyboard_level = {
    "one_time": True,
    "buttons": [
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"1\"}",
                "label": "Лёгкий"
            },
            "color": "positive"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"2\"}",
                "label": "Сложный"
            },
            "color": "negative"
        }
        ]
    ]
}


'''
Клавиатура, которая активируется во время прохождения уровня
'''
keyboard_in_game = {
    "one_time": False,
    "buttons": [
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"1\"}",
                "label": "Подсказка &#128161;"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"2\"}",
                "label": "Пропустить"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"3\"}",
                "label": "Отменить &#9940;"
            },
            "color": "primary"
        }
        ]
    ]
}

'''Клавиатура, которая активируется в главном меню.'''
keyboard_main_menu = {
    "one_time": False,
    "buttons": [
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"1\"}",
                "label": "Города"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"2\"}",
                "label": "Википедия"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"3\"}",
                "label": "Режимы"
            },
            "color": "primary"
        }
        ]
    ]
}

used_cities = []

if __name__ == '__main__':
    main()
