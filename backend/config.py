import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    app_name: str = "Crediclass Dashboard V3"
    version: str = "4.0.0"
    environment: str = "development"
    debug: bool = False
    google_sheets_id: str = ""
    google_service_account_json: str = ""
    google_sheet_name: str = "Tabela de Grupos 3.0"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        version=os.getenv("APP_VERSION", "4.0.0"),
        environment=os.getenv("ENVIRONMENT", "development"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        google_sheets_id=os.getenv("GOOGLE_SHEETS_ID", ""),
        google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", ""),
        google_sheet_name=os.getenv("GOOGLE_SHEET_NAME", "Tabela de Grupos 3.0"),
    )
