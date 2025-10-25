import asyncio
import json
from logging import captureWarnings

from core.enums import StatusRunMark
from core.requests import lessons, teachers, group, students
from core.redis_config import redis_instance
from core.logic.students.mark import add_attendance_redis
from core.requests.group import get_group_name
from core.requests.lessons import get_subject_name
from core.requests.teachers import get_lesson_types_teacher, get_name_subjects_teacher, get_groups_teacher


def _construct_info_msg(lesson_data: list[dict]) -> str:
    """
    Формирует сообщение с информацией о паре для подтверждения запуска отметок
    :param lesson_data:
    :return:
    """
    if not lesson_data:
        raise ValueError("Нет данных о текущих парах для формирования сообщения.")
    groups = []
    for l in lesson_data:
        groups.append(l.get("group_name", "Неизвестная группа"))
    groups_str = "\n".join(groups)
    subject_name = lesson_data[0].get("subject_name", "Неизвестный предмет")
    lesson_type = lesson_data[0].get("lesson_type", "Неизвестный тип")
    date = lesson_data[0].get("date", "Неизвестная дата")
    time = lesson_data[0].get("time", "Неизвестное время")
    info_msg = (f"Предмет: {subject_name}\n"
                f"Тип пары: {lesson_type}\n"
                f"Дата: {date}\n"
                f"Время: {time}\n"
                f"Группы:\n{groups_str}\n\n"
                f"Верно?")
    return info_msg


async def prestart_mark(user_tg_id: int) -> tuple[StatusRunMark, str | None, dict | None, list[dict] | None]:
    """
    Автоматическое создание отметки
    :param user_tg_id: id телеграм преподавателя
    :return: Статус ответ, текст (Опционально) и данные для кнопки (Опционально)
    """
    status, mark_data = await lessons.get_actual_lesson_teacher(user_tg_id)
    if status == StatusRunMark.IS_NO_TEACHER:
        text = """
        Вы не преподаватель.
        """
        return StatusRunMark.IS_NO_TEACHER, text, None, None
    if status == StatusRunMark.NO_PAIR_TEACHER:
        text = """
        Не удалось найти ваши текущие пары.\n
        Хотите создать отметку самостоятельно?
        """
        keyboards_data = {
            "type": "inline",
            "buttons": [
                {
                    "text": "Создать",
                    "callback_data": "create_custom_mark"
                }
            ]
        }
        return StatusRunMark.NO_PAIR_TEACHER, text, keyboards_data, None
    text = _construct_info_msg(mark_data)
    keyboards_data = {
        "type": "inline",
        "buttons": [
            {
                "text": "Да",
                "callback_data": "start_mark"
            },
            {
                "text": "Нет",
                "callback_data": "create_custom_mark"
            }
        ]
    }
    return StatusRunMark.OK, text, keyboards_data, mark_data


async def _delay_action(func_send_msg, lesson_instances_ids: list[int], chat_id, ttl: int = 180):
    """
    Удаляет временные отметки у групп:
    1) Если у группы есть еще какие-то отметки, то удаляет только нужную (Переданную)
    2) Если у группы больше нет отметок, то удаляет ключ
    :param lesson_instances_ids: Список отметок
    :param chat_id: ИД чата, куда высылать информацию об отметке
    :param ttl: Задержка для удаления записей
    """
    await asyncio.sleep(ttl)
    result = "Отметка окончена. Посещаемость:"
    sum_count_student = 0
    for lesson_instance_id in set(lesson_instances_ids):
        groups_data = await group.get_groups_id_by_instance_id(lesson_instance_id)
        for group_id, group_name in groups_data:
            key = str(group_id)
            data_json = redis_instance.get(key)
            if data_json:
                data = json.loads(data_json)
                data.pop(str(lesson_instance_id), None)
                if data:
                    redis_instance.set(key, json.dumps(data), ex=600)
                else:
                    redis_instance.delete(key)
            count_student = await students.get_count_students_instance(lesson_instance_id, group_id)
            sum_count_student += count_student
            result += f"\n{group_name} : {count_student}"
    result += (f"\n"
               f"\n"
               f"Всего: {sum_count_student}\n")
    keyboards_data = {
        "type": "inline",
        "buttons": [
            {
                "text": "Удалить случайно",
                "callback_data": "random_remove"
            }
        ]
    }
    await func_send_msg(chat_id=chat_id, text=result, keyboards_data=keyboards_data)
    add_attendance_redis(chat_id, lesson_instances_ids)


async def started_mark(mark_data: list[dict], user_tg_id: int, func_answer):
    """
    Создание отметок для групп + запись в redis
    :param func_answer: функция для отправки сообщения преподавателю
    :param mark_data: данные для отметок
    :param user_tg_id: телеграм ид преподавателя
    """
    lesson_instance_ids = await lessons.insert_lesson_instance(mark_data)
    for item, lesson_instance_id in zip(mark_data, lesson_instance_ids):
        group_id = str(item["group_id"])
        data_json = redis_instance.get(group_id)
        if data_json:
            data = json.loads(data_json)
        else:
            data = {}
        data[str(lesson_instance_id)] = 'pair'
        redis_instance.set(key=group_id, value=json.dumps(data), ex=600)
    asyncio.create_task(_delay_action(func_answer, lesson_instance_ids, user_tg_id, 30))


# --==[Регистрация новой пары]==--

async def get_type_lesson(user_tg_id: int):
    type_lessons = await get_lesson_types_teacher(user_tg_id)
    buttons_data = []
    for type_lesson in type_lessons:
        buttons_data.append({
            'text': type_lesson,
            'callback_data': f"type_{type_lesson.replace(' ', '-')}"
        })
    text = "Выберите тип пары:"
    keyboards_data = {
        "type": "inline",
        "buttons": buttons_data
    }
    return text, keyboards_data

async def get_name_lesson(user_tg_id: int, lesson_type: str):
    name_lessons = await get_name_subjects_teacher(lesson_type, user_tg_id)
    buttons_data = []
    for id_, name_lesson in name_lessons:
        buttons_data.append({
            "text": name_lesson,
            "callback_data": f"subject_{id_}"
        })
    buttons_data.append({
        "text": "Назад",
        "callback_data": "back_type_lessons"
    })
    text = "Выберите название предмета"
    keyboards_data = {
        "type": "inline",
        "buttons": buttons_data
    }
    return text, keyboards_data

async def get_groups_teachers(subject_id: int, tg_user_id: int, lesson_type: str, selected: set[int]):
    groups = await get_groups_teacher(subject_id, tg_user_id, lesson_type)
    buttons_data = []

    for idx, name in groups:
        label = f"✅ {name}" if idx in selected else name
        buttons_data.append({
            "text": label,
            "callback_data": f"group_{idx}"
        })

    buttons_data.append({
        "text": "Назад",
        "callback_data": "back_name_lessons"
    })
    buttons_data.append({
        "text": "Готово",
        "callback_data": "confirm_choice_group"
    })
    text = "Выберите группы"
    keyboards_data = {
        "type": "inline",
        "buttons": buttons_data
    }
    return text, keyboards_data


async def get_custom_mark_info(lesson_type: str, subject_id: int, groups: list[int], user_tg_id: int):
    groups_name = ''
    for group_id in groups:
        group_name = await get_group_name(group_id)
        groups_name += f"{group_name}\n"
    subject_name = await get_subject_name(subject_id)
    text = (f"Предмет: {subject_name}\n"
            f"Тип пары: {lesson_type}\n"
            f"Группы:\n"
            f"{groups_name}\n"
            f"\n"
            f"Запустить?")
    buttons_data = [
        {
            "text": "Да",
            "callback_data": "start_custom_mark"
        },
        {
            "text": "Назад",
            "callback_data": "back_group"
        }
    ]
    keyboards_data = {
        "type": "inline",
        "buttons": buttons_data
    }
    return text, keyboards_data


async def start_custom_mark(lesson_type: str, subject_id: int, groups: list[int], user_tg_id: int, func_answer):
    data_custom_lesson = await lessons.insert_custom_lesson(lesson_type, subject_id, groups, user_tg_id)
    await started_mark(data_custom_lesson, user_tg_id, func_answer)
    text = "Отметка запущена"
    return text