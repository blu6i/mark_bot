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
    :return: id групп
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
        SELECT id 
        FROM mark_bot.groups 
        WHERE course = $1
    """
    result = await db_async.select(
        sql=sql,
        params=[course],
        fetchone=False
    )
    return result

async def main():
    r = await get_groups_id_by_instance_id(1)
    for i in r:
        id_, name =  i
        print(f'{id_} {name}')


if __name__ == "__main__":
    asyncio.run(main())
