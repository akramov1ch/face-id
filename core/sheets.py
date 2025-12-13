import gspread
from gspread.utils import rowcol_to_a1  # <--- YANGI IMPORT
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
        # ... (Bu funksiya o'zgarishsiz qoladi) ...
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
                logger.info(f"--- O'qilmoqda: {worksheet.title} ---")

                for i, row in enumerate(rows):
                    real_row_num = i + START_ROW 
                    
                    acc_id = self._safe_get(row, SHEET_COLUMNS['account_id'])
                    full_name = self._safe_get(row, SHEET_COLUMNS['full_name'])
                    branch_name = self._safe_get(row, SHEET_COLUMNS['branch_name'])
                    phone = self._safe_get(row, SHEET_COLUMNS['phone'])
                    
                    if not full_name:
                        continue

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

    # --- YANGI OPTIMALLASHTIRILGAN FUNKSIYA ---
    def batch_update_ids(self, worksheet, updates):
        """
        Bir nechta ID larni bitta so'rov bilan yozadi.
        updates = [ (row_num, new_id), (row_num, new_id), ... ]
        """
        if not updates:
            return True

        try:
            # Configdagi ustun raqami (0 dan boshlanadi, gspreadga 1 dan kerak)
            col_num = SHEET_COLUMNS['account_id'] + 1
            
            batch_data = []
            for row_num, new_id in updates:
                # Katak manzilini aniqlash (Masalan: P4, P10)
                cell_address = rowcol_to_a1(row_num, col_num)
                batch_data.append({
                    'range': cell_address,
                    'values': [[str(new_id)]]
                })

            # Bitta so'rov bilan hammasini yuborish
            worksheet.batch_update(batch_data)
            logger.info(f"✅ Batch update: {len(updates)} ta ID yozildi ({worksheet.title})")
            return True
        except Exception as e:
            logger.error(f"❌ Batch update xatosi: {e}")
            return False

    def log_attendance(self, sheet_id: str, employee_name: str, employee_id: str, action: str, device_ip: str):
        # ... (Bu funksiya o'zgarishsiz qoladi) ...
        try:
            if not sheet_id: return
            try:
                sheet = self.client.open_by_key(sheet_id).sheet1
            except:
                return
            
            uz_tz = timezone(timedelta(hours=5))
            now = datetime.now(uz_tz)
            
            row = [
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S"),
                employee_name,
                employee_id,
                action,
                device_ip
            ]
            sheet.append_row(row)
        except Exception as e:
            logger.error(f"Log error: {e}")