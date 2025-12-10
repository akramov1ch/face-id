from pydantic_settings import BaseSettings
from typing import List

# Google Sheets ustunlari (A=0, B=1, C=2...)
SHEET_COLUMNS = {
    "branch_name": 1,      # A ustun: Filial nomi
    "full_name": 2,        # B ustun: F.I.Sh
    "phone": 3,            # C ustun: Telefon
    "account_id": 4,       # D ustun: ID
}

START_ROW = 2

class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str
    SUPER_ADMIN_ID: int

    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    # Server
    SERVER_PORT: int

    # --- GOOGLE SHEETS ---
    GOOGLE_SPREADSHEET_ID: str
    GOOGLE_CREDS_FILE: str = "google_creds.json"
    
    # O'ZGARTIRILDI: Default qiymatni bo'sh qoldiramiz
    GOOGLE_WORKSHEET_NAMES: str = "" 

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