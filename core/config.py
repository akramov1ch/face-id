from pydantic_settings import BaseSettings
from typing import List

SHEET_COLUMNS = {
    "branch_name": 1,     
    "full_name": 2,        
    "phone": 8,           
    "account_id": 15,      
}

START_ROW = 3

class Settings(BaseSettings):
    BOT_TOKEN: str
    SUPER_ADMIN_ID: int

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    SERVER_PORT: int

    GOOGLE_SPREADSHEET_ID: str
    GOOGLE_CREDS_FILE: str = "google_creds.json"
    GOOGLE_WORKSHEET_NAMES: str = "" 

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    @property
    def google_worksheet_name_list(self) -> List[str]:
        """Agar nomlar yozilgan bo'lsa ro'yxat qiladi, bo'lmasa bo'sh ro'yxat qaytaradi"""
        if not self.GOOGLE_WORKSHEET_NAMES:
            return []
        return [name.strip() for name in self.GOOGLE_WORKSHEET_NAMES.split(',') if name.strip()]

    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()