import gspread
from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone
import logging
from .config import settings, SHEET_COLUMNS, START_ROW

logger = logging.getLogger(__name__)

class GoogleSheetManager:
    def __init__(self):
        self.scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        self.creds = Credentials.from_service_account_file(settings.GOOGLE_CREDS_FILE, scopes=self.scopes)
        self.client = gspread.authorize(self.creds)

    def _safe_get(self, row, index):
        try:
            val = row[index]
            return str(val).strip() if val else ""
        except IndexError:
            return ""

    def get_all_employees_raw(self):
        """
        Xodimlarni o'qiydi (Admin Sync uchun).
        """
        results = []
        try:
            spreadsheet = self.client.open_by_key(settings.GOOGLE_SPREADSHEET_ID)
        except Exception as e:
            logger.error(f"Spreadsheetni ochishda xato: {e}")
            return []

        worksheets_to_process = []
        if settings.google_worksheet_name_list:
            for name in settings.google_worksheet_name_list:
                try:
                    worksheets_to_process.append(spreadsheet.worksheet(name))
                except: pass
        else:
            try:
                worksheets_to_process.append(spreadsheet.get_worksheet(0))
            except: pass

        for worksheet in worksheets_to_process:
            try:
                rows = worksheet.get_all_values()[START_ROW-1:]
                for i, row in enumerate(rows):
                    real_row_num = i + START_ROW 
                    acc_id = self._safe_get(row, SHEET_COLUMNS['account_id'])
                    full_name = self._safe_get(row, SHEET_COLUMNS['full_name'])
                    branch_name = self._safe_get(row, SHEET_COLUMNS['branch_name'])
                    phone = self._safe_get(row, SHEET_COLUMNS['phone'])
                    
                    if not full_name: continue

                    data = {
                        "account_id": acc_id,
                        "full_name": full_name,
                        "branch_name": branch_name,
                        "phone": phone
                    }
                    results.append((worksheet, real_row_num, data))

            except Exception as e:
                logger.error(f"Varaq xatosi: {e}")

        return results

    def batch_update_ids(self, worksheet, updates):
        """
        Admin Sync uchun ID larni ommaviy yozish.
        """
        if not updates: return True
        try:
            col_num = SHEET_COLUMNS['account_id'] + 1
            batch_data = []
            for row_num, new_id in updates:
                cell_address = rowcol_to_a1(row_num, col_num)
                batch_data.append({
                    'range': cell_address,
                    'values': [[str(new_id)]]
                })
            worksheet.batch_update(batch_data)
            return True
        except Exception as e:
            logger.error(f"Batch update xatosi: {e}")
            return False


    def _get_or_create_daily_sheet(self, spreadsheet, date_str):
        """
        Berilgan sana (masalan: 13.12.2025) bo'yicha varaqni qidiradi.
        Yo'q bo'lsa yaratadi va chiroyli dizayn beradi.
        """
        try:
            worksheet = spreadsheet.worksheet(date_str)
            return worksheet
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=date_str, rows=1000, cols=5, index=0)
            
            headers = ["F.I.Sh (Xodim)", "ID Raqam", "Holat", "Vaqt"]
            worksheet.append_row(headers)

            try:
                worksheet.format('A1:D1', {
                    "backgroundColor": {
                        "red": 0.15, "green": 0.6, "blue": 0.3  
                    },
                    "textFormat": {
                        "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, 
                        "fontSize": 11,
                        "bold": True
                    },
                    "horizontalAlignment": "CENTER", 
                    "verticalAlignment": "MIDDLE",
                    "borders": {
                        "bottom": {"style": "SOLID", "width": 1, "color": {"red": 0, "green": 0, "blue": 0}}
                    }
                })
                
                worksheet.freeze(rows=1)

                worksheet.set_column_width(0, 250) 
                worksheet.set_column_width(1, 100) 
                worksheet.set_column_width(2, 100) 
                worksheet.set_column_width(3, 100) 
            except Exception as e:
                logger.warning(f"Formatlashda xatolik (lekin ma'lumot yozilaveradi): {e}")

            return worksheet

    def log_attendance(self, sheet_id: str, employee_name: str, employee_id: str, action: str):
        """
        Davomatni yozish. 
        Avtomatik ravishda bugungi sana bilan varaq ochadi.
        """
        try:
            if not sheet_id: return
            
            try:
                spreadsheet = self.client.open_by_key(sheet_id)
            except Exception as e:
                logger.error(f"Sheet ID noto'g'ri yoki ruxsat yo'q: {sheet_id}")
                return
            
            uz_tz = timezone(timedelta(hours=5))
            now = datetime.now(uz_tz)
            date_str = now.strftime("%d.%m.%Y") 
            time_str = now.strftime("%H:%M:%S")

            worksheet = self._get_or_create_daily_sheet(spreadsheet, date_str)
            
            row = [
                employee_name,  
                employee_id,    
                action,         
                time_str        
            ]
            
            worksheet.append_row(row)

        except Exception as e:
            logger.error(f"Log error: {e}")