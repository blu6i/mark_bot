from aiogram.types import BotCommand

from bots.tg_bot.config_bot import dp, bot
from bots.tg_bot.handlers.register_routers import register_router
from bots.tg_bot.handlers.teachers.start_mark import send_message_info_marks

from core.logic.teachers.started_mark import restore_tasks_from_redis
from core.utils.loggers import log

ACTION_MAP = {
    "send_message_info_marks": send_message_info_marks
}

async def on_startup():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="kb", description="Клавиатура")
    ])
    try:
        await restore_tasks_from_redis(send_message_info_marks)
        log.info("Загружены задачи из редиса")
    except Exception as e:
        log.error(f"Проблема при восстановлении задач из редис: {e}")
    log.info("Bot start")

async def on_shutdown():
    log.info("Bot finish")
    await bot.session.close()

async def start_bot():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.include_router(register_router())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)