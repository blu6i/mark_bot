import json
import random

from core.enums import StatusMarkStudent, StatusAttendanceMark
from core.redis_config import redis_instance, redis_attendance

from core.requests import students, lessons, group


def add_attendance_redis(chat_id: int, lesson_data: list[int]):
    redis_attendance.set(key=chat_id, value=json.dumps(lesson_data), ex=600)

async def mark_student(user_tg_id: int, lesson_instance_id: int=None) -> tuple[StatusMarkStudent, str | None, dict | None]:
    student_id = await students.get_student_id_by_tg_id(user_tg_id)

    if lesson_instance_id:
        if not students.is_instance_group_student(lesson_instance_id, student_id):
            text = "Не ваша отметка"
            return StatusMarkStudent.NOT_YOUR_MARK, text, None
        status = await students.insert_student_attendance(student_id, lesson_instance_id)
        if status == StatusAttendanceMark.OK:
            text = "Вы отметились"
            return StatusMarkStudent.OK, text, None
        elif status == StatusAttendanceMark.ALREADY:
            text = "Вы уже отметились"
            return StatusMarkStudent.OK, text, None
        else:
            text = "Неизвестная ошибка"
            return StatusMarkStudent.ERROR, text, None

    if not student_id:
        text = ("Вы не авторизованы.\n"
                "Используйте /start для перезапуска бота.")
        return StatusMarkStudent.NO_STUDENT, text, None

    group_id = await students.get_student_group_id(student_id)


    data_json = redis_instance.get(str(group_id))
    if not data_json:
        text = "Для вашей группы нет отметки"
        return StatusMarkStudent.NO_MARK, text, None
    redis_data = json.loads(data_json)
    if not redis_data:
        text = "Для вашей группы нет отметки"
        return StatusMarkStudent.NO_MARK, text, None

    if len(redis_data) == 1:
        lesson_instance_id = int(list(redis_data.keys())[0])
        status = await students.insert_student_attendance(student_id, lesson_instance_id)
        if status == StatusAttendanceMark.OK:
            text = "Вы отметились"
            return StatusMarkStudent.OK, text, None
        elif status == StatusAttendanceMark.ALREADY:
            text = "Вы уже отметились"
            return StatusMarkStudent.OK, text, None
        else:
            text = "Неизвестная ошибка"
            return StatusMarkStudent.ERROR, text, None
    else:
        text = ("У вашей группы запущенно несколько отметок.\n"
                "\n"
                "Выберите нужную:")
        buttons_data = []
        for lesson_instance_id in redis_data.keys():
            name_subject = await lessons.get_subject_name_lesson(int(lesson_instance_id))
            buttons_data.append({
                "text": name_subject,
                "callback_data": f"lesson_{lesson_instance_id}"
            })
        keyboards_data = {
            "type": "inline",
            "buttons": buttons_data
        }
        return StatusMarkStudent.MORE_MARK, text, keyboards_data


async def delete_random_students(count_random: int, chat_id: int) -> str:
    lesson_instances_ids = [int(i) for i in json.loads(redis_attendance.get(chat_id))]
    students_id = set()
    for lesson_instances_id in lesson_instances_ids:
        groups_id = await group.get_groups_id_by_instance_id(lesson_instances_id)
        for group_id, _ in groups_id:
            students_id.update(await students.get_students_id_instance(lesson_instances_id, group_id))
    result = []
    random_students = random.sample(list(students_id), count_random)
    for attendance_id, student_id in random_students:
        await students.delete_attendance_student(attendance_id)
        name = await students.get_student_last_name(student_id)
        result.append(name)
    result.sort()
    text = (f'Удалены студенты:\n'
            f'{', '.join(result)}')
    return text