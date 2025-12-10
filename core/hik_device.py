import requests
from requests.auth import HTTPDigestAuth
import json
import logging
from typing import List, Tuple

# Loglarni sozlash
logger = logging.getLogger(__name__)

class HikDeviceClient:
    def __init__(self, ip, username, password):
        self.base_url = f"http://{ip}"
        self.auth = HTTPDigestAuth(username, password)
        self.timeout = 5  # 5 soniya kutish vaqti

    def upload_face(self, user_id: str, image_bytes: bytes) -> Tuple[bool, str]:
        """
        Bitta qurilmaga rasm yuklash.
        Qaytaradi: (Muvaffaqiyatli?, Xabar)
        """
        # 1. USER YARATISH (UserInfo)
        user_url = f"{self.base_url}/ISAPI/AccessControl/UserInfo/Record?format=json"
        user_payload = {
            "UserInfo": {
                "employeeNo": user_id,
                "userType": "normal",
                "Valid": {
                    "enable": True,
                    "beginTime": "2024-01-01T00:00:00",
                    "endTime": "2035-01-01T00:00:00"
                }
            }
        }

        try:
            resp = requests.post(user_url, data=json.dumps(user_payload), auth=self.auth, timeout=self.timeout)
            # Agar user allaqachon bor bo'lsa (status != 200), baribir davom etamiz
            if resp.status_code != 200 and "employeeNoAlreadyExist" not in resp.text:
                return False, f"User xatosi: {resp.status_code}"
        except Exception as e:
            return False, f"Ulanish xatosi (User): {str(e)}"

        # 2. RASM YUKLASH (FaceDataRecord)
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
            resp = requests.post(face_url, files=files, auth=self.auth, timeout=10)
            
            try:
                data = resp.json()
                if data.get('statusCode') == 1 or resp.status_code == 200:
                    return True, "OK"
                return False, f"Rasm xatosi: {data.get('statusString', resp.text)}"
            except:
                return False, f"Rasm javobi xato: {resp.text}"

        except Exception as e:
            return False, f"Ulanish xatosi (Face): {str(e)}"

def upload_to_branch_devices(devices: List[dict], user_id: str, image_bytes: bytes):
    """
    Filialdagi barcha qurilmalarga yuklaydi.
    devices: [{'ip': '...', 'user': '...', 'pass': '...'}, ...]
    """
    results = []
    for dev in devices:
        client = HikDeviceClient(dev['ip'], dev['user'], dev['pass'])
        success, msg = client.upload_face(user_id, image_bytes)
        results.append({
            "ip": dev['ip'],
            "success": success,
            "msg": msg
        })
    return results