# coding: utf-8
from pony import orm

db = orm.Database()


class User(db.Entity):
    id = orm.PrimaryKey(int)
    first_name = orm.Required(str)
    chat_id = orm.Optional(int)
    key = orm.Optional(str)
    orm.composite_index(chat_id, key)
