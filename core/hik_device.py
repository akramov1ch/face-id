import requests
from requests.auth import HTTPDigestAuth
import json
import logging
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor  # <--- YANGI: Parallel ishlash uchun

# Loglarni sozlash
logger = logging.getLogger(__name__)

class HikDeviceClient:
    def __init__(self, ip, username, password):
        self.base_url = f"http://{ip}"
        self.auth = HTTPDigestAuth(username, password)
        # Timeoutni biroz oshiramiz, parallel ishlaganda barqarorlik uchun
        self.timeout = 10 

    def set_access_group(self, user_id: str):
        """
        Foydalanuvchini majburan 1-raqamli Ruxsat Guruhiga qo'shish.
        Bu "Qizil yozuv" (No permission) xatosini yo'qotadi.
        """
        # 1. Guruh borligini ta'minlash (Create Group)
        group_url = f"{self.base_url}/ISAPI/AccessControl/AccessGroup/Record?format=json"
        group_payload = {
            "AccessGroup": {
                "id": 1,
                "name": "AdminGroup",
                "enabled": True,
                "Attribute": {
                    "templateNo": 1,  # 1 = All Day (24 soat)
                    "doorNo": 1       # 1-eshik
                }
            }
        }
        try:
            requests.post(group_url, data=json.dumps(group_payload), auth=self.auth, timeout=self.timeout)
        except:
            pass

        # 2. Foydalanuvchini shu guruhga a'zo qilish (Add Member)
        member_url = f"{self.base_url}/ISAPI/AccessControl/AccessGroup/Member/Record?format=json"
        member_payload = {
            "AccessGroupMemberList": [
                {
                    "accessGroupID": 1,
                    "UserList": [
                        {"employeeNo": user_id}
                    ]
                }
            ]
        }
        
        try:
            resp = requests.post(member_url, data=json.dumps(member_payload), auth=self.auth, timeout=self.timeout)
            if resp.status_code == 200 or resp.status_code == 201:
                return True
            return False
        except:
            return False

    def upload_face(self, user_id: str, image_bytes: bytes) -> Tuple[bool, str]:
        # Ruxsat vaqti: 2020 dan 2035 gacha
        start_time = "2020-01-01T00:00:00"
        end_time = "2035-01-01T00:00:00"

        # 1. USER YARATISH
        user_url = f"{self.base_url}/ISAPI/AccessControl/UserInfo/Record?format=json"
        
        user_payload = {
            "UserInfo": {
                "employeeNo": user_id,
                "userType": "normal",
                "doorRight": "1",
                "RightPlan": [
                    {
                        "doorNo": 1,
                        "planTemplateNo": "1"
                    }
                ],
                "Valid": {
                    "enable": True,
                    "beginTime": start_time,
                    "endTime": end_time
                }
            }
        }

        try:
            # Avval tozalaymiz (xatolik bo'lmasligi uchun)
            try:
                del_url = f"{self.base_url}/ISAPI/AccessControl/UserInfo/Delete?format=json"
                del_payload = {"UserInfoDetail": {"mode": "byEmployeeNo", "EmployeeNoList": [{"employeeNo": user_id}]}}
                requests.put(del_url, data=json.dumps(del_payload), auth=self.auth, timeout=3)
            except:
                pass

            # Yaratamiz
            resp = requests.post(user_url, data=json.dumps(user_payload), auth=self.auth, timeout=self.timeout)
            
            if resp.status_code != 200:
                 # Agar o'chirish o'xshamagan bo'lsa, Modify qilamiz
                 modify_url = f"{self.base_url}/ISAPI/AccessControl/UserInfo/Modify?format=json"
                 requests.put(modify_url, data=json.dumps(user_payload), auth=self.auth, timeout=self.timeout)

        except Exception as e:
            return False, f"Ulanish xatosi (User): {str(e)}"

        # 2. RASM YUKLASH
        face_url = f"{self.base_url}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json"
        face_data = {
            "faceLibType": "blackFD",
            "FDID": "1",
            "FPID": user_id
        }

        try:
            files = {
                'FaceDataRecord': (None, json.dumps(face_data), 'application/json'),
                'img': ('face.jpg', image_bytes, 'image/jpeg')
            }
            resp = requests.post(face_url, files=files, auth=self.auth, timeout=15)
            
            # --- GURUHGA QO'SHISH ---
            self.set_access_group(user_id)
            # ------------------------

            try:
                data = resp.json()
                if data.get('statusCode') == 1 or resp.status_code == 200:
                    return True, "OK"
                return False, f"Rasm xatosi: {data.get('statusString', resp.text)}"
            except:
                return False, f"Rasm javobi xato: {resp.text}"

        except Exception as e:
            return False, f"Ulanish xatosi (Face): {str(e)}"

# --- YANGI PARALLEL FUNKSIYA ---

def _upload_single_device_task(dev_info: dict, user_id: str, image_bytes: bytes):
    """
    Bitta qurilma uchun ishlaydigan yordamchi funksiya.
    Bu funksiya alohida Thread ichida ishlaydi.
    """
    ip = dev_info['ip']
    user = dev_info['user']
    password = dev_info['pass']
    
    try:
        # Har bir thread o'zining Client obyektini yaratadi (Thread-safe)
        client = HikDeviceClient(ip, user, password)
        success, msg = client.upload_face(user_id, image_bytes)
        return {
            "ip": ip,
            "success": success,
            "msg": msg
        }
    except Exception as e:
        return {
            "ip": ip,
            "success": False,
            "msg": f"System Error: {str(e)}"
        }

def upload_to_branch_devices(devices: List[dict], user_id: str, image_bytes: bytes):
    """
    Barcha qurilmalarga PARALLEL ravishda rasm yuklaydi.
    """
    results = []
    
    # Maksimal 10 ta parallel oqim (agar qurilmalar ko'p bo'lsa, 10 tadan bo'lib ishlaydi)
    # Bu serverni ortiqcha yuklamaslik uchun kerak.
    max_threads = 10
    
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        # Vazifalarni yaratamiz
        futures = [
            executor.submit(_upload_single_device_task, dev, user_id, image_bytes) 
            for dev in devices
        ]
        
        # Natijalarni yig'ib olamiz (qaysi biri tugasa, o'shani oladi)
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                # Favqulodda holatda
                logger.error(f"Thread execution failed: {e}")
                
    return results