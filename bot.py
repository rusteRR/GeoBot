import vk_api
import requests
import os
from wiki import get_summary
from make_board import create_board
import json
from database import check_id, add_users, use_prompt, check_update, get_best_players, add_answers, add_questions
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import random
from io import BytesIO
from screenshot import Map
from PIL import Image
import datetime
from data import db_session


db_session.global_init("users.sqlite")

vk_session = vk_api.VkApi(
    token=TOKEN)
longpoll = VkBotLongPoll(vk_session, 194275944)
vk = vk_session.get_api()

COUNTER = 0  # Счётчик номера вопроса
CORRECT = 0  # Счётчик правильных ответов в игре
WRONG = 0  # Счётчик неверных ответов в игре
LEVEL = '-'
LEARNING = False
SIGHTS = False

EM_NUMBERS = {1: '1&#8419;', 2: '2&#8419;', 3: '3&#8419;', 4: '4&#8419;', 5: '5&#8419;',
              6: '6&#8419;', 7: '7&#8419;', 8: '8&#8419;', 9: '9&#8419;', 10: '&#128287;'}


'''Функция возваращет изображение bytes-like объекта, вызывается в функции photo для отправки
изображения пользователю'''


def get_image(level):
    with open('cities.txt') as fi:
        cities = fi.read().split('.')
    if LEVEL == 'лёгкий':
        cities = cities[0].split('\n')
    else:
        cities = cities[1].split('\n')
    if '' in cities:
        del cities[cities.index('')]
    city = random.sample(cities, 1)
    while city[0] in used_cities:
        city = random.sample(cities, 1)
    print(city[0])
    used_cities.append(city[0])
    n = Map()
    return n.draw_map(city[0])


'''Функция проверяет, есть ли данный пользователь в базе данных, возваращет 
False, если пользователь не зарегистрирован, True, если пользователь есть в ьазе данных'''


def check_register(user_id):
    result = check_id(user_id)
    print(result)
    if result:
        res = True
    else:
        res = False
    return res


def get_learning_image():
    with open('cities.txt') as fi:
        cities = fi.read()
    cities = cities.replace('.', '')
    cities = cities.split('\n')
    city = random.sample(cities, 1)
    while city in used_cities:
        city = random.sample(cities, 1)
    used_cities.append(city)
    n = Map()
    return n.draw_map(city), city


def sights_photo():
    with open('landmarks.txt') as fi:
        sights = fi.read().split('\n')
    sight = random.sample(sights, 1)
    sight_name = sight[0].split(':')[-1]
    adress = sight[0].split(':')[0]
    while sight_name in used_cities:
        sight = random.sample(sights, 1)
        sight_name = sight[0].split(':')[-1]
        adress = sight[0].split(':')[0]
    print(sight_name)
    used_cities.append(sight_name)
    n = Map()
    return n.draw_map(adress)


'''Отправка спутникового изображения пользователю'''


def photo(peer_id, user_id):
    global COUNTER, CORRECT, WRONG, LEVEL, LEARNING, SIGHTS
    if SIGHTS:
        COUNTER += 1
        if COUNTER > 15:
            text = f'Уровень пройден!\nПравильных ответов: {CORRECT} из 15\nВернитесь в главное меню'
            vk.messages.send(user_ids=user_id, message=text,
                             random_id=0, keyboard=json.dumps(keyboard_in_game))
            return
        if COUNTER > 1:
            msg = f'Правильных ответов &#9989;: {CORRECT}\nНеправильных ответов &#10060;: {WRONG}'
            send_message(user_id, msg, keyboard_in_game)
        msg = f'Вопрос №{COUNTER} из {15}'
        kb = keyboard_in_game
        photo = sights_photo()
    elif LEARNING:
        photo, city = get_learning_image()
        msg = city
        kb = keyboard_learning
    else:
        COUNTER += 1
        if COUNTER > 15:
            text = f'Уровень пройден!\nПравильных ответов: {CORRECT} из 15\nВернитесь в главное меню'
            vk.messages.send(user_ids=user_id, message=text,
                             random_id=0, keyboard=json.dumps(keyboard_in_game))
            return
        if COUNTER > 1:
            msg = f'Правильных ответов &#9989;: {CORRECT}\nНеправильных ответов &#10060;: {WRONG}'
            send_message(user_id, msg, keyboard_in_game)
        msg = f'Вопрос №{COUNTER} из {15}'
        kb = keyboard_in_game
        photo = get_image(LEVEL)
    res = vk.photos.getMessagesUploadServer()
    Image.open(photo).save('result.jpg')
    create_board('result.jpg')
    b = requests.post(res["upload_url"], files={
                      "photo": open('result.jpg', 'rb')}).json()
    c = vk.photos.saveMessagesPhoto(
        photo=b["photo"], server=b["server"], hash=b["hash"])[0]
    res_photo = "photo{}_{}".format(c["owner_id"], c["id"])
    vk.messages.send(user_ids=user_id, peer_id=peer_id, message=msg,
                     attachment=res_photo, random_id=0, keyboard=json.dumps(kb))
    add_questions(user_id)
    os.remove('result.jpg')


def send_message(us_id, msg, keyboard):
    vk.messages.send(user_id=us_id, message=msg,
                     random_id=random.randint(0, 2 ** 64), keyboard=json.dumps(keyboard))


def main():
    global COUNTER, CORRECT, WRONG, LEVEL, LEARNING, SIGHTS
    TOWN = False
    RIVER = False
    WIKI = False
    LEARNING = False
    ANSWER = 15
    WRONG = 0
    CURRENT_PROMPT = 0
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            response = vk.users.get(user_ids=event.obj.message['from_id'])
            text = event.obj.message['text'].lower()
            user_id = event.obj.message['from_id']

            '''Проверка регистрации пользователя, в случае, если id пользователя
            отсутствует в базе данных - в БД добаляется id, имя, количество подсказок и время последнего обновления'''

            if not check_register(user_id):
                nickname = response[0]['first_name'] + ' ' + \
                    response[0]['last_name'][0] + '.'
                time = datetime.datetime.now().timestamp()
                add_users(user_id, nickname, 100, int(time))
                send_message(
                    user_id, 'Вы успешно зарегистрированы!', keyboard_main_menu)

            '''Обработка запросов пользователя'''

            if text.rsplit(maxsplit=1)[0] == 'выйти в меню':
                LEVEL = '-'
                TOWN = False
                RIVER = False
                COUNTER = 0
                CORRECT = 0
                LEARNING = False
                WIKI = False
                WRONG = 0
                CURRENT_PROMPT = 0
                used_cities.clear()
                send_message(
                    user_id, 'Вы успешно вышли в главное меню!', keyboard_main_menu)

            elif TOWN and LEVEL == '-':
                if text == 'лёгкий' or text == 'сложный':
                    LEVEL = text
                    photo(event.object.peer_id, user_id)
                else:
                    send_message(user_id, 'Некорректный ввод!', keyboard_level)

            elif LEARNING and text.rsplit(maxsplit=1)[0] == 'далее':
                photo(event.object.peer_id, user_id)

            elif LEARNING and text == 'подробнее':
                send_message(user_id, get_summary(
                    used_cities[-1]), keyboard_learning)

            elif text == 'достропримечательности':
                SIGHTS = True
                photo(event.object.peer_id, user_id)

            elif text.rsplit(maxsplit=1)[0] == 'города':
                send_message(user_id, 'Выберите сложность: ', keyboard_level)
                TOWN = True

            elif text.rsplit(maxsplit=1)[0] == 'википедия':
                WIKI = True
                msg = 'Введите объект и мы расскажем Вам о нём! '
                send_message(user_id, msg, keyboard_wiki)

            elif text.rsplit(maxsplit=1)[0] == 'топ игроков':
                best = get_best_players()
                msg = ''
                i = 0
                for i in range(1, len(best) + 1):
                    msg = msg + f'{EM_NUMBERS[i]} {best[i-1][1]} | Процент правильных ответов: {best[i-1][0]}%\n'
                if i < 10:
                    for j in range(i + 1, 11):
                        msg = msg + f'{EM_NUMBERS[j]} ...\n'
                send_message(user_id, msg, keyboard_main_menu)

            elif WIKI:
                msg = get_summary(text)
                send_message(user_id, msg, keyboard_wiki)

            elif text.rsplit(maxsplit=1)[0] == 'режимы':
                send_message(user_id, 'Выберите режим:', keyboard_modes)

            elif text == 'обучение':
                LEARNING = True
                send_message(
                    user_id, 'Добро пожаловать в режим обучения!', keyboard_learning)
                photo(event.object.peer_id, user_id)

            elif text.split()[0] == 'подсказка':
                length = len(used_cities[-1])
                check_update(user_id)
                possible = len(used_cities[-1].replace('-', '')) // 3
                if COUNTER > 15:
                    send_message(
                        user_id, 'Уровень пройден!\nВернитесь в главное меню', keyboard_in_game)
                elif CURRENT_PROMPT + 1 <= possible:
                    ok = use_prompt(user_id)
                    if ok == -1:
                        messag = '&#9940; У вас больше нет подсказок'
                        send_message(user_id, messag, keyboard_in_game)
                    else:
                        messag = f'&#9888; У вас осталось {ok} подсказок'
                        if CURRENT_PROMPT + 1 <= possible:
                            CURRENT_PROMPT += 1
                        msg = f'&#10004; Использована {CURRENT_PROMPT} подсказка из {possible}'
                        prompt = []
                        for i in range(length):
                            if i <= CURRENT_PROMPT - 2:
                                prompt.append(
                                    used_cities[-1][i].upper() + ' ')
                            elif used_cities[-1][i] == '-':
                                prompt.append(' - ')
                            elif used_cities[-1][i] == ' ':
                                prompt.append('       ')
                            else:
                                prompt.append('&#10134;')
                        prompt = ''.join(prompt)
                        send_message(user_id, f'{msg}\n&#128161; Подсказка: {prompt}\n{messag}',
                                     keyboard_in_game)
                else:
                    prompt = '&#8252; У вас больше нет подсказок для этого вопроса'
                    send_message(user_id, f'{msg}\n{prompt}\n{messag}',
                                 keyboard_in_game)

            elif text.rsplit(maxsplit=1)[0] == 'пропустить':
                WRONG += 1
                CURRENT_PROMPT = 0
                photo(event.object.peer_id, user_id)

            elif (TOWN and (LEVEL == 'лёгкий' or LEVEL == 'сложный')) or SIGHTS:
                print(used_cities[-1])
                if text == used_cities[-1].lower():
                    send_message(user_id, f'Верно &#9989;', keyboard_in_game)
                    CORRECT = CORRECT + 1
                    CURRENT_PROMPT = 0
                    add_answers(user_id, 1)
                    photo(event.object.peer_id, user_id)
                else:
                    WRONG += 1
                    CURRENT_PROMPT = 0
                    send_message(user_id, f'Неправильно :(', keyboard_in_game)
                    photo(event.object.peer_id, user_id)


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
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"2\"}",
                "label": "Сложный"
            },
            "color": "primary"
        }
        ],
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"4\"}",
                "label": "Выйти в меню &#128682;"
            },
            "color": "primary"
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
                "label": "Пропустить &#10145;"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"3\"}",
                "label": "Выйти в меню &#128682;"
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
                "label": "Города &#127972;"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"2\"}",
                "label": "Википедия &#127759;"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"3\"}",
                "label": "Режимы &#128681;"
            },
            "color": "primary"
        }
        ],
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"4\"}",
                "label": "Топ игроков &#128285;"
            },
            "color": "primary"
        }
        ]
    ]
}


keyboard_wiki = {
    "one_time": False,
    "buttons": [
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"1\"}",
                "label": "Подробнее &#128161;"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"3\"}",
                "label": "Выйти в меню &#128682;"
            },
            "color": "primary"
        }
        ]
    ]
}

keyboard_modes = {
    "one_time": False,
    "buttons": [
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"1\"}",
                "label": "Города &#127972;"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"2\"}",
                "label": "Достропримечательности"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"3\"}",
                "label": "Обучение"
            },
            "color": "primary"
        }
        ],
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"4\"}",
                "label": "Выйти в меню &#128682;"
            },
            "color": "primary"
        }
        ]
    ]
}

keyboard_learning = {
    "one_time": False,
    "buttons": [
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"1\"}",
                "label": "Далее &#10145;"
            },
            "color": "primary"
        },
            {
            "action": {
                "type": "text",
                "payload": "{\"button\": \"3\"}",
                "label": "Подробнее"
            },
            "color": "primary"
        }
        ],
        [{
            "action": {
                "type": "text",
                "payload": "{\"button\": \"4\"}",
                "label": "Выйти в меню &#128682;"
            },
            "color": "primary"
        }
        ]
    ]
}

used_cities = []

if __name__ == '__main__':
    main()
