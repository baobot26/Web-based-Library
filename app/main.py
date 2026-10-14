from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.books import router as books_router
from app.api.errors import register_error_handlers

app = FastAPI(title="Web-based Library API")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(books_router, prefix="/api/v1")
register_error_handlers(app)
