from core.enums import StatusNewUser
from core.logic.auth_user import check_auth_user

import dotenv, os
dotenv.load_dotenv()

ADMINS = list(map(int, (os.getenv("ADMINS").split(","))))

async def get_keyboard_commands(user_tg_id: int) -> dict | None:
    status, _ = await check_auth_user(user_tg_id)
    if status == StatusNewUser.OLD_USER_TEACHER:
        keyboards = {
            "type": "reply",
            "buttons": [
                {
                    "text": "Запустить отметку",
                    "callback_data": "start_mark"
                },
                {
                    "text": "Список отметившихся",
                    "callback_data": "show_marks"
                }
            ]
        }
    elif status == StatusNewUser.OLD_USER_STUDENT:
        keyboards = {
            "type": "reply",
            "buttons": [
                {
                    "text": "Отметиться",
                    "callback_data": "press_mark"
                }
            ]
        }
    else:
        keyboards = {
            "type": "reply",
            "buttons": []
        }
    if user_tg_id in ADMINS:
        keyboards["buttons"].append({
            "text": "Пригласить преподавателя",
            "callback_data": "create_invitation_link_teacher"
        })
        keyboards["buttons"].append({
            "text": "Запустить парсинг расписания",
            "callback_data": "run_parsing_schedule"
        })
    return keyboards
