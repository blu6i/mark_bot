import asyncio

from core.database_config import db_async


async def get_group_name(group_id: int) -> str:
    """
    Получает название группы
    :param group_id: id группы
    :return: название группы
    """
    sql = """
        SELECT name 
        FROM mark_bot.groups 
        WHERE id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[group_id],
        fetchone=True
    )
    return result[0] if result else None


async def get_group_id_by_instance_id(lesson_instance_id: int) -> str | None:
    """
    Получает название группы по id занятия
    :param lesson_instance_id: id занятия
    :return: название группы
    """
    sql = """
        SELECT group_id 
        FROM mark_bot.lesson_instance_groups
        WHERE lesson_instance_id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[lesson_instance_id],
        fetchone=True
    )
    group_id = int(result[0])
    group_name = await get_group_name(group_id)
    return group_name


async def get_groups_id_by_instance_id(lesson_instance_id: int) -> list[tuple[int, str]]:
    """
    Получает id групп по id занятия
    :param lesson_instance_id: id занятия
    :return: id группы + название
    """
    sql = """
        SELECT g.id, g.name
        FROM mark_bot.lesson_instance_groups lig
        JOIN mark_bot.groups g ON g.id = lig.group_id
        WHERE lesson_instance_id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[lesson_instance_id],
        fetchone=False
    )
    return result


async def get_group_course(course: int) -> tuple[int]:
    """
    Получает группы по курсу
    :param course: номер курса
    :return: ид групп
    """
    sql = """
        SELECT id, name
        FROM mark_bot.groups 
        WHERE course = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[course],
        fetchone=False
    )
    return result

async def get_courses() -> list[int]:
    """
    Получаем курсы
    :return: список курсов
    """
    sql = """
    SELECT DISTINCT course
    FROM mark_bot.groups
    ORDER BY course
    """
    result = await db_async.select(
        sql=sql,
        fetchone=False
    )
    return [r['course'] for r in result] if result else []


async def get_group_student(student_id):
    sql = """
        SELECT g.id, g.name
        FROM mark_bot.groups g
        JOIN mark_bot.group_students gs ON gs.group_id = g.id
        JOIN mark_bot.students s ON s.id = gs.student_id
        WHERE s.first_name = $1
        AND s.last_name = $2
        AND s.middle_name IS NOT DISTINCT FROM $3
    """
    result = await db_async.select(
        sql=sql,
        params=[student_id],
        fetchone=True
    )
    return result


async def get_group_students(group_id):
    sql = """
        SELECT id, last_name, first_name, middle_name
        FROM mark_bot.students
        WHERE group_id = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[group_id],
        fetchone=False
    )
    return result


async def main():
    r = await get_group_course(2)
    for i, name in r:
        print(f'{i} {name}')


if __name__ == "__main__":
    asyncio.run(main())


