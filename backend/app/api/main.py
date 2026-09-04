from fastapi import APIRouter

from app.api.routes import login, private, users, utils, projects, documents, insights, search, chat
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(projects.router)
api_router.include_router(documents.router)
api_router.include_router(insights.router)
api_router.include_router(search.router)
api_router.include_router(chat.router)

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
