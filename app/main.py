from fastapi import FastAPI

from app.api.errors import register_error_handlers

app = FastAPI(title="Web-based Library API")
register_error_handlers(app)
