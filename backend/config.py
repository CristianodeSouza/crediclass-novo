import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Configurações da aplicação"""

    # Google Sheets
    GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "")
    GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "")

    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Validação
    @classmethod
    def validate(cls):
        """Validar configurações críticas"""
        if not cls.GOOGLE_SHEETS_ID:
            print("⚠️  GOOGLE_SHEETS_ID não configurado em .env")
        if not cls.GOOGLE_SERVICE_ACCOUNT_JSON:
            print("⚠️  GOOGLE_SERVICE_ACCOUNT_JSON não configurado em .env")
        if not cls.GOOGLE_SHEET_NAME:
            print("⚠️  GOOGLE_SHEET_NAME não configurado em .env")

settings = Settings()
