import datetime
import re

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

URL = "https://www.vyatsu.ru/studentu-1/spravochnaya-informatsiya/raspisanie-zanyatiy-dlya-studentov.html"


def get_html(url: str) -> str | None:
    """
    Отправляет GET запрос к сайту и возвращает HTML страницы
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
        return response.text
    except requests.HTTPError as e:
        print(f"HTTP ошибка при запросе к {url}: {e} (код: {response.status_code})")
        return None
    except requests.Timeout:
        print(f"Таймаут при запросе к {url}")
        return None
    except requests.RequestException as e:
        print(f"Ошибка запроса к {url}: {e}")
        return None


def is_actual_schedule(name: str) -> bool:
    """
    Проверка на актуальность расписания
    :param name: имя ссылки ПДФ файла
    :return: true, если актуально, иначе false
    """
    try:
        # Удаление расширения + деление на части
        parts = name.rsplit('.', 1)[0].split('_')

        # Извлекаем даты начала и конца
        start_date_str = parts[-2]
        end_date_str = parts[-1]

        start_date = ''
        end_date = ''

        # Проверка формата даты
        date_pattern = r'^(\d{2})(\d{2})(\d{4})$'
        for date_str in (start_date_str, end_date_str):
            if not re.match(date_pattern, date_str):
                print(f"Некорректный формат даты в {name}")
                return False

            # Извлечение день, месяц, год
            match = re.match(date_pattern, date_str)
            day, month, year = match.groups()
            formatted_date = f"{day}-{month}-{year}"  # Например, 01-09-2024

            # Парсим дату
            try:
                parsed_date = datetime.datetime.strptime(formatted_date, '%d-%m-%Y').date()
            except ValueError as e:
                print(f"Инвалид дата {formatted_date} в {name}: {e}")
                return False

            # Сохраняем даты
            if start_date == '':
                start_date = parsed_date
            else:
                end_date = parsed_date

        # Проверка на попадание в диапазон
        current_date = datetime.date.today() + datetime.timedelta(days=1)
        is_actual = start_date <= current_date <= end_date
        return is_actual

    except Exception as e:
        print(f"Ошибка при проверке диапазона даты {name}: {e}")
        return False


def parser_url(url: str) -> list | None:
    html_url = get_html(url)
    if html_url is None:
        raise ValueError(f'Не удалось получить HTML {url}')
    soup = BeautifulSoup(html_url, 'html.parser')
    schedules = soup.find_all('div', class_='grpPeriod')
    result = []
    for schedule in schedules:
        if 'ИВТ' in schedule.get_text().strip():
            id_ = schedule.get('data-grp_period_id')
            id_list_period = f'listPeriod_{id_}'
            block_list_period = soup.find('div',
                                          attrs={'class': 'listPeriod',
                                                 'id': id_list_period})
            links_schedule = block_list_period.find_all('a')
            for link in links_schedule:
                if is_actual_schedule(link.get('href')):
                    tmp = {
                        "group": schedule.get_text().strip(),
                        "url": f"https://www.vyatsu.ru{link.get("href")}"
                    }
                    result.append(tmp)
                    break
    return result


def main():
    url = parser_url(URL)
    for group, link in url.items():
        print(f"{group} : {link}")

if __name__ == '__main__':
    main()
