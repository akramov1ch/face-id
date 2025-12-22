from fastapi import FastAPI, Request, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import json
import logging
import requests
from datetime import datetime, timedelta, timezone

from .database import get_db
from .models import Device, Employee, Branch, DeviceType
from .sheets import GoogleSheetManager
from .config import settings
from .cache import cache  

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
sheet_manager = GoogleSheetManager()

def send_telegram_alert(chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Telegram alert error: {e}")

def process_attendance_task(sheet_id: str, emp_name: str, emp_id: str, action: str, notif_chat_id: int, branch_name: str):
    try:
        sheet_manager.log_attendance(
            sheet_id=sheet_id,
            employee_name=emp_name,
            employee_id=emp_id,
            action=action
        )

        if notif_chat_id:
            emoji = "✅" if action == "KIRISH" else "❌" if action == "CHIQISH" else "⚠️"
            uz_tz = timezone(timedelta(hours=5))
            current_time = datetime.now(uz_tz).strftime('%H:%M:%S')
            
            alert_text = (
                f"{emoji} **DAVOMAT BILDIRISHNOMASI**\n\n"
                f"👤 **Xodim:** {emp_name}\n"
                f"🏢 **Filial:** {branch_name}\n"
                f"🔄 **Holat:** {action}\n"
                f"⏰ **Vaqt:** {current_time}"
            )
            send_telegram_alert(notif_chat_id, alert_text)
            
    except Exception as e:
        logger.error(f"Background task error: {e}")

@app.post("/api/hikvision/event")
async def receive_event(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        content_type = request.headers.get('content-type', '')
        data = None

        if "application/json" in content_type:
            data = await request.json()
        elif "multipart/form-data" in content_type:
            form = await request.form()
            for key, value in form.items():
                if isinstance(value, str) and "eventType" in value:
                    try:
                        data = json.loads(value)
                        break
                    except:
                        continue
        
        if not data:
            return {"status": "failed", "msg": "No data found"}

        event_type = data.get('eventType')
        
        if event_type == 'AccessControllerEvent':
            details = data.get('AccessControllerEvent')
            
            device_ip = data.get('ipAddress')
            employee_id = details.get('employeeNoString')
            sub_event_type = details.get('subEventType')
            
            if not device_ip or not employee_id:
                return {"status": "ignored", "msg": "Missing IP or ID"}

            device_info = cache.get_device_info(device_ip)
            
            if not device_info:
                device = db.query(Device).filter(Device.ip_address == device_ip).first()
                if not device:
                    logger.warning(f"Noma'lum qurilmadan signal: {device_ip}")
                    return {"status": "ignored", "msg": "Unknown Device"}

                branch = db.query(Branch).filter(Branch.id == device.branch_id).first()
                if not branch:
                    return {"status": "error", "msg": "Branch not found"}
                
                cache.set_device_info(device, branch)
                
                device_type_val = device.device_type.value
                branch_name = branch.name
                sheet_id = branch.attendance_sheet_id
            else:
                device_type_val = device_info['device_type']
                branch_name = device_info['branch_name']
                sheet_id = device_info['sheet_id']

            emp_info = cache.get_employee_info(employee_id)
            
            if not emp_info:
                employee = db.query(Employee).filter(Employee.account_id == employee_id).first()
                
                if employee:
                    emp_name = employee.full_name.title()
                    notif_chat_id = employee.notification_chat_id
                    cache.set_employee_info(employee)
                else:
                    emp_name = "Noma'lum Xodim"
                    notif_chat_id = None
            else:
                emp_name = emp_info['full_name'].title()
                notif_chat_id = emp_info['chat_id']

            action = "Noma'lum"
            
            if device_type_val == "entry":
                action = "KIRISH"
            elif device_type_val == "exit":
                action = "CHIQISH"
            else:
                if sub_event_type in [21, 75]: 
                    action = "KIRISH"
                elif sub_event_type in [22, 104]: 
                    action = "CHIQISH"
                else: 
                    action = f"O'TISH ({sub_event_type})"

            if action in ["KIRISH", "CHIQISH"]:
                should_log = cache.check_action_state(employee_id, action)
                
                if not should_log:
                    logger.info(f"⏭ SKIPPED (Duplicate State): {emp_name} allaqachon {action} holatida.")
                    return {"status": "ignored", "msg": "Duplicate action skipped"}

                logger.info(f"SIGNAL: {branch_name} | {emp_name} | {action}")
                
                background_tasks.add_task(
                    process_attendance_task,
                    sheet_id,
                    emp_name,
                    employee_id,
                    action,
                    notif_chat_id,
                    branch_name
                )

        return {"status": "success", "msg": "Processed in background"}

    except Exception as e:
        logger.error(f"Server xatosi: {e}")
        return {"status": "error", "msg": str(e)}