import asyncio

from core.database_config import db_async

async def is_auth_teacher(user_tg_id) -> bool:
    """
    Проверяет, авторизован ли пользователь как преподаватель в базе данных
    :param user_tg_id: id пользователя в телеграме
    :return: True если пользователь зарегистрирован, False если нет
    """
    sql = """
        SELECT 1 
        FROM mark_bot.teachers 
        WHERE tg_id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[user_tg_id],
        fetchone=True
    )
    return result is not None


async def set_teacher_tg_id(user_id: int, user_tg_id: int | None):
    """
    Устанавливает id телеграма для преподавателя
    :param user_id: id преподавателя в базе данных
    :param user_tg_id: id преподавателя в телеграме
    """
    sql = """
        UPDATE mark_bot.teachers 
        SET tg_id = $1 
        WHERE id = $2
    """
    await db_async.update(
        sql=sql,
        params=[user_tg_id, user_id]
    )


async def get_teacher_id_by_tg_id(user_tg_id: int) -> int | None:
    """
    Получает id телеграма для преподавателя
    :param user_tg_id: id телеграм преподавателя
    :return: id преподавателя в базе данных
    """
    sql = """
        SELECT id 
        FROM mark_bot.teachers 
        WHERE tg_id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[user_tg_id],
        fetchone=True
    )
    return result[0] if result else None


async def get_teacher_id_by_fullname(fullname: dict) -> int | None:
    """
    Получает id преподавателя по ФИО
    :param fullname: ФИО преподавателя
    :return: id преподавателя в базе данных
    """
    sql = """
        SELECT id FROM mark_bot.teachers
        WHERE first_name = $1
        AND last_name = $2
        AND middle_name IS NOT DISTINCT FROM $3
    """
    result = await db_async.select(
        sql=sql,
        params=[fullname["first_name"], fullname["last_name"], fullname["middle_name"]],
        fetchone=True
    )
    return result[0] if result else None


async def get_teacher_fullname(teacher_id: int) -> dict | None:
    """
    Получает ФИО преподавателя по его id
    :param teacher_id: id преподавателя в базе данных
    :return: ФИО преподавателя
    """
    sql = """
        SELECT first_name, last_name, middle_name 
        FROM mark_bot.teachers
        WHERE id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[teacher_id],
        fetchone=True
    )
    if result:
        return {
            "last_name": result[1],
            "first_name": result[0],
            "middle_name": result[2],
        }
    return None


async def get_lesson_types_teacher(user_tg_id: int) -> list[str]:
    """
    Получает типы занятий, которые может проводить преподаватель
    :param user_tg_id: id телеграма преподавателя
    :return: список типов занятий
    """
    teacher_id = get_teacher_id_by_tg_id(user_tg_id)
    sql = """
        SELECT DISTINCT lesson_type
        FROM mark_bot.teacher_subjects
        WHERE teacher_id = $1
        ORDER BY lesson_type
    """
    results = await db_async.select(
        sql=sql,
        params=[teacher_id],
        fetchone=False
    )
    return [result[0] for result in results]


async def get_subjects_type_teacher(lesson_type: str, user_tg_id: int) -> list:
    """
    Получает типы занятий, которые проводит преподаватель
    :param lesson_type: тип занятия
    :param user_tg_id: id телеграма преподавателя
    :return: список типов занятий
    """
    teacher_id = get_teacher_id_by_tg_id(user_tg_id)
    sql = """
        SELECT DISTINCT s.id, s.name
        FROM mark_bot.teacher_subjects ts
        JOIN mark_bot.subjects s ON s.id = ts.subject_id
        WHERE ts.teacher_id = $1 AND ts.lesson_type = $2
        ORDER BY s.name
    """
    results = await db_async.select(
        sql=sql,
        params=[teacher_id, lesson_type],
        fetchone=False
    )
    return results


async def get_groups_teacher(subject_id: int, user_tg_id: int, lesson_type: str) -> list:
    """
    Полуает группы, в которых преподаватель ведёт занятия
    :param subject_id: id предмета
    :param user_tg_id: id телеграм преподавателя
    :param lesson_type: тип занятия
    :return: список групп
    """
    teacher_id = get_teacher_id_by_tg_id(user_tg_id)
    sql = """
        SELECT DISTINCT g.id, g.name
        FROM mark_bot.teacher_subjects ts
        JOIN mark_bot.groups g ON g.id = ts.group_id
        JOIN mark_bot.group_subjects gs ON gs.group_id = g.id
        WHERE gs.subject_id = $1 AND ts.teacher_id = $2 AND ts.lesson_type = $3
        ORDER BY g.name
    """
    results = await db_async.select(
        sql=sql,
        params=[subject_id, teacher_id, lesson_type],
        fetchone=False
    )
    return results

async def main():
    pass


if __name__ == "__main__":
    asyncio.run(main())