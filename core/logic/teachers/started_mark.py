import asyncio
import json

from core.enums import StatusRunMark
from core.requests import lessons, teachers, group, students
from core.redis_config import redis_instance
from core.logic.students.mark import add_attendance_redis

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


async def prestart_mark(user_tg_id: int) -> tuple[StatusRunMark, str | None, dict | None]:
    """
    Автоматическое создание отметки
    :param user_tg_id: id телеграм преподавателя
    :return: Статус ответ, текст (Опционально) и данные для кнопки (Опционально)
    """
    teacher_id = await teachers.get_teacher_id_by_tg_id(user_tg_id)
    if not teacher_id:
        text = """
        Вы не преподаватель.
        """
        return StatusRunMark.IS_NO_TEACHER, text, None
    status, mark_data = await lessons.get_actual_lesson_teacher(teacher_id)
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
                    "callback_data": "start_mark"
                }
            ]
        }
        return StatusRunMark.NO_PAIR_TEACHER, text, keyboards_data
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
    return StatusRunMark.OK, text, keyboards_data


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
    await func_send_msg(chat_id=chat_id, text=result)
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