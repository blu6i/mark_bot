import uuid

from core.enums import StatusInviteLink
from core.requests.teachers import get_teacher_id_by_fullname
from core.redis_config import redis_link_teacher

def _split_fullname_to_dict(fullname: str) -> dict:
    fullname_split = fullname.split()
    return {
        "first_name": fullname_split[1],
        "last_name": fullname_split[0],
        "middle_name": fullname_split[2] if len(fullname_split) > 2 else None
    }


async def create_invite_link_teacher(fullname: str) -> tuple[StatusInviteLink, str, dict | None]:
    fullname_split = _split_fullname_to_dict(fullname)
    teacher_data = await get_teacher_id_by_fullname(fullname_split)
    if not teacher_data:
        text = "Данные о преподавателе не найдены"
        return StatusInviteLink.NOT_FOUND, text, None
    id_, tg_id = teacher_data
    if tg_id:
        text = (f"{fullname} уже зарегистрирован в боте\n"
                f"Перепривязать?")
        buttons_data = {
            "type": "inline",
            "buttons": [
                {
                    "text": "Да",
                    "callback_data": f"yes_rebind_{id_}"
                },
                {
                    "text": "Нет",
                    "callback_data": "no_rebind"
                }
            ]
        }
        return StatusInviteLink.ALREADY_TG, text, buttons_data
    else:
        invite_link = create_invite_link(id_)
        text = (f"Ссылка для приглашения:\n"
                f"{invite_link}\n"
                f"\n"
                f"Активна в течении 5 минут")
        return StatusInviteLink.OK, text, None


def create_invite_link(user_id: int) -> str:
    key = str(uuid.uuid4())
    redis_link_teacher.set(key, user_id)
    url = f"https://t.me/airi_guild_bot?start={key}"
    # url = f"https://t.me/mark_ivt_bot?start={key}"
    return url