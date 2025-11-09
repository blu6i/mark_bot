from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from dotenv import load_dotenv
from os import getenv

from core.requests.students import is_auth_student
from core.requests.teachers import is_auth_teacher

load_dotenv()


class IsTeacher(BaseFilter):
    async def __call__(self, event: Union[Message, CallbackQuery]):
        user_tg_id = event.from_user.id
        result = await is_auth_teacher(user_tg_id)
        return result


class IsStudent(BaseFilter):
    async def __call__(self, event: Union[Message, CallbackQuery]):
        user_tg_id = event.from_user.id
        result = await is_auth_student(user_tg_id)
        return result


class IsAdmin(BaseFilter):
    ADMINS = list(map(int, (getenv("ADMINS").split(","))))
    async def __call__(self, event: Union[Message, CallbackQuery]):
        user_tg_id = event.from_user.id
        return user_tg_id in self.ADMINS


class BlackListWord(BaseFilter):
    BLACK_LIST_WORD = [
        'отметиться',
        'запустить отметку',
        'список отметившихся',
        'пригласить преподавателя',
        'управление списками'
    ]
    async def __call__(self, msg: Message):
        return msg.text.lower() not in self.BLACK_LIST_WORD


class CorrectWordCommand(BaseFilter):
    def __init__(self, word: list | str):
        if isinstance(word, str):
            self._word = word.lower()
        else: self._word = [w.lower() for w in word]
    async def __call__(self, msg: Message):
        if isinstance(self._word, str):
            return msg.text.lower() == self._word
        return msg.text.lower() in self._word


class IsNotCommand(BaseFilter):
    """
    Фильтр на ввод команды
    """
    async def __call__(self, msg: Message) -> bool:
        text = msg.text
        return text[0] != "/"


