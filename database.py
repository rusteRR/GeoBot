from data.user import User
from data import db_session
import datetime


db_session.global_init('users.sqlite')


def add_users(user_id, nickname, prompt, last_update):
    user = User()
    user.user_id = user_id
    user.nickname = nickname
    user.prompt = prompt
    user.last_update = last_update
    user.cor_answ = 0
    user.all_questions = 0
    session = db_session.create_session()
    session.add(user)
    session.commit()


def check_id(user_id):
    session = db_session.create_session()
    query = session.query(User)
    f = (User.user_id == user_id)
    reg = False
    for user in query.filter(f).all():
        reg = True

    return reg


def use_prompt(user_id):
    session = db_session.create_session()
    query = session.query(User)
    f = (User.user_id == user_id)
    for user in query.filter(f).all():
        if user.prompt > 0:
            user.prompt = user.prompt - 1
            result = user.prompt
        else:
            result = -1
    session.commit()
    return result


def check_update(user_id):
    session = db_session.create_session()
    query = session.query(User)
    f = (User.user_id == user_id)
    for user in query.filter(f).all():
        past_days = (datetime.datetime.now().timestamp()
                     - user.last_update) // 86400
    new_prompts = past_days * 5
    if past_days > 0:
        user.last_update = user.last_update + past_days * 86400
        if user.prompt + new_prompts > 20:
            user.prompt = 20
        else:
            user.prompt = user.prompt + new_prompts
    session.commit()


def add_answers(user_id, answers):
    session = db_session.create_session()
    query = session.query(User)
    f = (User.user_id == user_id)
    for user in query.filter(f).all():
        user.cor_answ = user.cor_answ + answers
    session.commit()


def add_questions(user_id):
    session = db_session.create_session()
    query = session.query(User)
    f = (User.user_id == user_id)
    for user in query.filter(f).all():
        user.all_questions = user.all_questions + 1
    session.commit()


def get_best_players():
    best = []
    session = db_session.create_session()
    query = session.query(User)
    f = (User.all_questions > 0)
    for user in query.filter(f).all():
        best.append((
            int((user.cor_answ / user.all_questions) * 100), user.nickname))
    best.sort()
    return best[:10]


def stats(user_id):
    session = db_session.create_session()
    query = session.query(User)
    f = (User.all_questions > 0)
    for user in query.filter(f).all():
        perc = (user.cor_answ / user.all_questions) * 100
        cor = user.cor_answ
        all_quest = user.all_questions
    return perc, cor, all_quest
