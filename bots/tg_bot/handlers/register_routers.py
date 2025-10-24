from aiogram import Router
from .started_cmd import started_router

def register_router() -> Router:
    main_router = Router()
    main_router.include_router(started_router)

    return main_router