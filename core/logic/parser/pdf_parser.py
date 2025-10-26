import asyncio
import re

import fitz
import requests
from fake_useragent import UserAgent
from pandas import DataFrame
from datetime import datetime

from core.logic.parser.web_parser import parser_url
from core.database_config import db_async


KEYWORDS = ['Практическое занятие', 'Лекция', 'Лабораторная работа', 'Консультация', 'Экзамен', 'Зачет', 'Защита ВКР']
TIME_PATTERN = re.compile(r'^\d{2}:\d{2}-\d{2}:\d{2}$')
GROUP_PATTERN = re.compile(
    r'\b[А-ЯЁа-яё]{1,6}'
    r'[а-яё]-'
    r'\d{4}-'
    r'\d{2}-\d{2}\b'
)
# Формат аудитории
CLASS_PATTERN = re.compile(r'\b\d{1,2}\s*-\s*\d{3}(?:[а-яёa-z]?_?)?\b')
# Формат цифр в скобах
NUM_PATTERN = re.compile(r'\(\d+ \d+\)')
# Формат для ФИО преподавателя
TEACHER_PATTERN = re.compile(r'\b[А-ЯЁ][а-яё]+ (?:(?:[А-ЯЁ]\.)|(?:\.)|)(?:[А-ЯЁ]\.)')


def get_format_date(cell: str) -> str | None:
    """
    Форматирует дату из ПДФ файла расписания
    !!! Изменить логику для вытаскивания даты!!!
    -- Сделать вытаскивание через паттерн
    :param cell: ячейка с датой
    :return: отформатированная дата
    """
    try:
        date = cell.split()[-1].strip().split('.')
        format_date = f"20{date[2]}-{date[1]}-{date[0]}"
        return format_date
    except Exception as e:
        print(f'Ошибка при форматировании даты ({cell}): {e}')


def get_classroom(cell: str) -> str:
    match = CLASS_PATTERN.search(cell)
    if match:
        return match.group(0)
    else:
        print(cell)

        return "Не определенно"
    #return match.group(0) if match else "Не определенно"


def get_number_subgroup(cell: str) -> str:
    """
    Определяет, разделена ли группа на паре на подгруппы. Возвращает номер погруппы, которая присутствует на паре.
    !!! Изменить логику, если вдруг какая-то группа делится на больше чем 2 подгруппы !!!
    :param cell: ячейка с расписанием
    :return: номер подгруппы или обе
    """
    if '01 подгруппа' in cell and '02 подгруппа' in cell:
        return 'all'
    elif '01 подгруппа' in cell:
        return '01'
    elif '02 подгруппа' in cell:
        return '02'
    else:
        return 'all'


def get_type_class(cell: str) -> str:
    """
    Возвращает тип пары
    :param cell: строка с расписанием
    :return: типа пары или указание, что тип не определен
    """
    for word in KEYWORDS:
        if word.lower() in cell.lower():
            return word
    return 'Собрание'


def get_class_name(study: str) -> str:
    """
    Форматирует строку с названием занятия:
    1. Удаляет название группы, если оно есть
    2. Удаляет номера аудиторий
    3. Обрезает до первого типа занятия
    :param study: Исходная строка с названием занятия
    :return: Отформатированная строка
    """
    # Удаляем название группы, если оно есть
    cleaned_text = re.sub(GROUP_PATTERN, "", str(study)).rstrip('.').strip()

    # Удаляем номера аудиторий
    cleaned_text = re.sub(CLASS_PATTERN, '', cleaned_text)

    # Удаляем цифры в скобках
    cleaned_text = re.sub(NUM_PATTERN, '', cleaned_text)

    # Проверяем наличие русских заглавных букв
    uppercase_in_text = None
    for s in cleaned_text:
        if s.isupper():
            uppercase_in_text = s
            break

    # Определяем позиции ключевых слов
    positions = None
    for keyword in KEYWORDS:
        pos = cleaned_text.find(keyword)
        if pos != -1:
            positions = pos
            break

    # Если нашли ключевые слова - обрезаем до первого из них
    if positions:
        start = cleaned_text.find(uppercase_in_text)
        return cleaned_text[start:positions].strip()

    # Если ключевых слов нет, возвращаем текст от первой заглавной буквы
    start = cleaned_text.find(uppercase_in_text)
    format_text = cleaned_text.split(',')[0]
    if "Час с куратором" in format_text:
        return "Час с куратором"
    return format_text[start:].strip()


def get_name_teacher(cell: str) -> str:
    """
    Возвращает ФИО преподавателя из расписания
    :param cell: строка с расписанием
    :return: ФИО преподавателя или указание, что в расписании нет его
    """
    match = TEACHER_PATTERN.search(cell)
    return match.group(0) if match else "Не определенно"


def get_content_pdf(url: str) -> bytes | None:
    """
    Открывает PDF файл по ссылке и возвращает данные от туда
    :param url: ссылка на страницу
    :return: HTML страницы
    """
    ua = UserAgent()
    headers = {'User-Agent': ua.random,
               'Accept': 'text/html'}
    try:
        response = requests.get(url=url,
                                headers=headers,
                                timeout=15)
        response.raise_for_status()
        return response.content
    except requests.HTTPError as e:
        print(f"HTTP ошибка при запросе к {url}: {e} (код: {response.status_code})")
        return None
    except requests.Timeout:
        print(f"Таймаут при запросе к {url}")
        return None
    except requests.RequestException as e:
        print(f"Ошибка запроса к {url}: {e}")
        return None


def parser_pdf(group_data: dict) -> DataFrame | None:
    """
    Парсит ПДФ файл, в итоге получается df с информацией:
    0) Группа
    1) Подгруппа
    2) Дата
    3) Время
    4) Тип пары
    5) Название пары
    6) Преподаватель
    7) Аудитория
    :param group_data: словарь с шифром группы и ссылкой на ПДФ файл расписания
    :return: df с вытащенной информацией из ПДФ файла
    """
    content = get_content_pdf(group_data['url'])
    if content is None:
        raise ValueError(f'Не удалось получить контент из пдф {group_data["url"]}')
    all_tables = []
    with fitz.open("pdf", content) as pdf:
        for page in pdf:
            table = page.find_tables()
            if not table.tables:
                continue
            all_tables.append(table[0].extract())
    all_data = []
    current_date = None
    current_time = None
    current_subgroup = None
    current_type_class = None
    current_class = None
    current_teacher = None
    current_classroom = None
    last_data = ()
    for table in all_tables:
        for row in table:
            current_data = ()
            if row[0] == 'День':
                continue
            cells = [str(cell).strip() if cell is not None else "" for cell in row]
            if len(row) == 3:
                cells[2] = cells[2].replace('\n', ' ')
                # Дата
                current_date = get_format_date(cells[0]) if cells[0] else current_date
                # Время !!! Написать логику для вытаскивания времени из ломанных ячеек. Сделать вытаскивания строго по паттерну
                current_time = cells[1] if re.match(TIME_PATTERN, cells[1]) else current_time
                # Подгруппа
                current_subgroup = get_number_subgroup(cells[2]) if cells[2] != "" else ""
                # Тип пары
                current_type_class = get_type_class(cells[2]) if cells[2] != "" else ""
                # Название пары
                current_class = get_class_name(cells[2]) if cells[2] != "" else ""
                # Преподаватель
                current_teacher = get_name_teacher(cells[2]) if cells[2] != "" else ""
                # Аудитория
                current_classroom = get_classroom(cells[2]) if cells[2] != "" else ""
                current_data = (
                    group_data['group'], current_subgroup, current_date, current_time, current_type_class,
                    current_class,
                    current_teacher, current_classroom)
            else:
                continue
            # Замена, если все подгруппы идут на пару
            diff_id = [i for i, (last, current) in enumerate(zip(last_data, current_data)) if last != current]
            if len(diff_id) == 0 or (len(diff_id) == 1 and diff_id[0] == 1):
                if all_data != []:
                    del all_data[len(all_data) - 1]
                current_subgroup = 'all'
                current_data = (
                    group_data['group'], current_subgroup, current_date, current_time, current_type_class,
                    current_class,
                    current_teacher, current_classroom)

            all_data.append(current_data)
            last_data = current_data
    return DataFrame(all_data,
                     columns=['group', 'subgroup', 'date', 'time', 'type_class', 'class', 'teacher', 'classroom'])


async def insert_lessons(df):
    """
    Асинхронно вставляет уроки в lessons и связывает их с группами через lesson_groups.
    DataFrame должен содержать колонки:
    class, teacher, date, time, type_class, group
    """

    for _, row in df.iterrows():
        # 1. Получаем subject_id
        sql = "SELECT id FROM mark_bot.subjects WHERE name = $1"
        subj = await db_async.select(sql, [row["class"]], fetchone=True)
        if not subj:
            # raise ValueError(f"Предмет '{row['class']}' не найден в subjects")
            continue
        subject_id = subj["id"]

        # 2. Разделяем время
        try:
            start_time, end_time = row["time"].split("-")
            start_time, end_time = start_time.strip(), end_time.strip()
        except Exception:
            raise ValueError(f"Некорректный формат времени: {row['time']}")

        date_obj = datetime.strptime(row["date"], "%Y-%m-%d").date()
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(end_time, "%H:%M").time()

        # 3. Вставляем пару
        sql = """
            INSERT INTO mark_bot.lessons 
                (subject_id, date, start_time, end_time, lesson_type)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (subject_id, date, start_time, end_time, lesson_type)
            DO UPDATE SET lesson_type = EXCLUDED.lesson_type
            RETURNING id
        """
        lesson_id = await db_async.insert(
            sql=sql,
            params=[subject_id, date_obj, start_time_obj, end_time_obj, row["type_class"]],
            returning=True
        )

        # 4. Получаем group_id
        sql = "SELECT id FROM mark_bot.groups WHERE name = $1"
        grp = await db_async.select(sql, [row["group"]], fetchone=True)
        if not grp:
            raise ValueError(f"Группа '{row['group']}' не найдена в groups")
        group_id = grp["id"]

        # 5. Вставляем связь
        sql = """
            INSERT INTO mark_bot.lesson_groups (lesson_id, group_id)
            VALUES ($1, $2)
            ON CONFLICT (lesson_id, group_id) DO NOTHING
        """
        await db_async.execute(sql, [lesson_id, group_id])

    print("Lessons и lesson_groups успешно добавлены")


async def start_parse():
    URL = "https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html"
    groups = parser_url(URL)
    for group in groups:
        table = parser_pdf(group)
        await insert_lessons(table)


if __name__ == "__main__":
    asyncio.run(start_parse())