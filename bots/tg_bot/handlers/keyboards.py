from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup


def construct_keyboards(keyboards_data: dict):
    keyboards_type = keyboards_data.get("type")
    if not keyboards_type:
        return None
    keyboard_items = keyboards_data.get("buttons")
    if not keyboard_items:
        return None
    keyboards = []
    if keyboards_type == "reply":
        for keyboard_item in keyboard_items:
            text = keyboard_item.get("text")
            keyboards.append([KeyboardButton(text=text)])
        return ReplyKeyboardMarkup(keyboard=keyboards,
                                   resize_keyboard=True)
    else:
        for keyboard_item in keyboard_items:
            text = keyboard_item.get("text")
            callback_data = keyboard_item.get("callback_data")
            keyboards.append([InlineKeyboardButton(text=text,
                                                   callback_data=callback_data)])
        return InlineKeyboardMarkup(inline_keyboard=keyboards)