import requests
import json
import sys
import os
import time
from datetime import datetime

# Loyiha modullarini ulash uchun
sys.path.append(os.getcwd())

from core.database import SessionLocal
from core.models import Branch, Device, Employee, DeviceType

# --- SOZLAMALAR (SIZNING MA'LUMOTLARINGIZ) ---
SERVER_URL = "http://localhost:8000/api/hikvision/event"

# Siz yuborgan ma'lumotlar:
TEST_BRANCH_NAME = "Toshkent (SD)"
# URL dan ajratib olingan ID:
REAL_SHEET_ID = "10jJhyRABnjWPCVwHWYFSH6YY4za0AM_loOlgv0614Y4" 

TEST_DEVICE_IP = "192.168.1.777"
TEST_DEVICE_USER = "admin"
TEST_DEVICE_PASS = "admin123"
TEST_EMP_NAME = "Kassa"
TEST_EMP_ID = "571022" # Yoki o'zingiz xohlagan ID

def setup_db_data():
    """
    Test ishlashi uchun bazaga kerakli ma'lumotlarni yozadi va YANGILAYDI.
    """
    print("🛠  1. BAZA MA'LUMOTLARINI TAYYORLASH...")
    db = SessionLocal()
    try:
        # 1. Filial
        branch = db.query(Branch).filter(Branch.name == TEST_BRANCH_NAME).first()
        if not branch:
            branch = Branch(name=TEST_BRANCH_NAME, attendance_sheet_id=REAL_SHEET_ID)
            db.add(branch)
            db.commit()
            print(f"   ✅ Filial yaratildi: {TEST_BRANCH_NAME}")
        else:
            # MUHIM: Agar filial bor bo'lsa, Sheet ID ni yangilaymiz!
            if branch.attendance_sheet_id != REAL_SHEET_ID:
                branch.attendance_sheet_id = REAL_SHEET_ID
                db.commit()
                print(f"   UPDATED: Filial Sheet ID yangilandi!")
            print(f"   ℹ️  Filial mavjud: {TEST_BRANCH_NAME}")

        # 2. Qurilma (Kamera)
        device = db.query(Device).filter(Device.ip_address == TEST_DEVICE_IP).first()
        if not device:
            device = Device(
                branch_id=branch.id,
                ip_address=TEST_DEVICE_IP,
                username=TEST_DEVICE_USER,
                password=TEST_DEVICE_PASS,
                device_type=DeviceType.UNIVERSAL
            )
            db.add(device)
            db.commit()
            print(f"   ✅ Qurilma qo'shildi: IP {TEST_DEVICE_IP}")
        else:
            print(f"   ℹ️  Qurilma mavjud: IP {TEST_DEVICE_IP}")

        # 3. Xodim
        emp = db.query(Employee).filter(Employee.account_id == TEST_EMP_ID).first()
        if not emp:
            emp = Employee(
                account_id=TEST_EMP_ID,
                full_name=TEST_EMP_NAME,
                branch_id=branch.id
            )
            db.add(emp)
            db.commit()
            print(f"   ✅ Xodim qo'shildi: {TEST_EMP_NAME} (ID: {TEST_EMP_ID})")
        else:
            # Xodimni filialga bog'lashni tekshirish
            if emp.branch_id != branch.id:
                emp.branch_id = branch.id
                db.commit()
                print("   UPDATED: Xodim filiali to'g'rilandi.")
            print(f"   ℹ️  Xodim mavjud: {TEST_EMP_NAME}")
            
        return branch.attendance_sheet_id

    except Exception as e:
        print(f"❌ Bazaga yozishda xatolik: {e}")
        return None
    finally:
        db.close()

def simulate_camera_event(event_type="entry"):
    print(f"\n📸  2. KAMERA SIGNALINI SIMULYATSIYA QILISH ({event_type.upper()})...")
    
    sub_event = 21 if event_type == "entry" else 22
    
    payload = {
        "ipAddress": TEST_DEVICE_IP,
        "portNo": 80,
        "protocol": "HTTP",
        "macAddress": "XX:XX:XX:XX:XX:XX",
        "channelID": 1,
        "dateTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:00"),
        "activePostCount": 1,
        "eventType": "AccessControllerEvent",
        "eventState": "active",
        "eventDescription": "Access Control Event",
        "AccessControllerEvent": {
            "deviceName": "Test Camera",
            "majorEventType": 5,
            "subEventType": sub_event, 
            "employeeNoString": TEST_EMP_ID,
            "name": TEST_EMP_NAME,
            "userType": "normal",
        }
    }

    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(SERVER_URL, data=json.dumps(payload), headers=headers)
        
        print(f"   📡 So'rov yuborildi: {SERVER_URL}")
        print(f"   Status Code: {response.status_code}")
        print(f"   Javob: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ SERVER SIGNALNI QABUL QILDI!")
        else:
            print("   ❌ SERVERDA XATOLIK!")

    except Exception as e:
        print(f"   ❌ Ulanish xatosi: {e}")

if __name__ == "__main__":
    print("🚀 TO'LIQ TIZIM TESTI BOSHLANDI\n")
    
    # 1. Bazani tayyorlash
    sheet_id = setup_db_data()
    
    if not sheet_id or "SHEET_ID" in sheet_id:
        print("\n⚠️ DIQQAT: Sheet ID hali ham noto'g'ri!")
    else:
        print(f"\n✅ Sheet ID sozlandi: {sheet_id}")
    
    # 2. Kirishni test qilish
    input("\nENTER bosing -> KIRISH (Entry) signalini yuborish uchun...")
    simulate_camera_event("entry")
    
    # 3. Chiqishni test qilish
    input("\nENTER bosing -> CHIQISH (Exit) signalini yuborish uchun...")
    simulate_camera_event("exit")
    
    print("\n" + "="*50)
    print("🏁  TEKSHIRISH UCHUN:")
    print("="*50)
    print("1. Google Sheetga kiring.")
    print(f"2. '{TEST_BRANCH_NAME}' ga tegishli Sheetda eng pastki qatorlarni tekshiring.")
    print(f"3. Sana, Vaqt, {TEST_EMP_NAME}, {TEST_EMP_ID}, KIRISH/CHIQISH yozuvlari paydo bo'lishi kerak.")
    print("="*50)