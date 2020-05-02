import sqlalchemy
from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'

    user_id = sqlalchemy.Column(sqlalchemy.Integer,
                                primary_key=True, autoincrement=True)
    nickname = sqlalchemy.Column(
        sqlalchemy.String, nullable=False, unique=True)
    prompt = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    last_update = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    cor_answ = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    all_questions = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
