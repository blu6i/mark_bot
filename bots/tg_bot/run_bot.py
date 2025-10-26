from aiogram.types import BotCommand

from bots.tg_bot.config_bot import dp, bot
from bots.tg_bot.handlers.register_routers import register_router


async def on_startup():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="kb", description="Клавиатура")
    ])
    print("Bot start")

async def on_shutdown():
    print("Bot finish")
    await bot.session.close()

async def start_bot():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.include_router(register_router())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)