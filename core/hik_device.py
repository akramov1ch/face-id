import requests
from requests.auth import HTTPDigestAuth
import json
import logging
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
import urllib3  

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class HikDeviceClient:
    def __init__(self, ip, username, password):
        self.base_url = f"https://{ip}"  
        self.auth = HTTPDigestAuth(username, password)
        self.timeout = 10 

    def set_access_group(self, user_id: str):
        group_url = f"{self.base_url}/ISAPI/AccessControl/AccessGroup/Record?format=json"
        group_payload = {
            "AccessGroup": {
                "id": 1,
                "name": "AdminGroup",
                "enabled": True,
                "Attribute": {
                    "templateNo": 1, 
                    "doorNo": 1      
                }
            }
        }
        try:
            requests.post(group_url, data=json.dumps(group_payload), auth=self.auth, timeout=self.timeout, verify=False)
        except:
            pass

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
            resp = requests.post(member_url, data=json.dumps(member_payload), auth=self.auth, timeout=self.timeout, verify=False)
            if resp.status_code == 200 or resp.status_code == 201:
                return True
            return False
        except:
            return False

    def upload_face(self, user_id: str, image_bytes: bytes) -> Tuple[bool, str]:
        start_time = "2020-01-01T00:00:00"
        end_time = "2035-01-01T00:00:00"

        user_url = f"{self.base_url}/ISAPI/AccessControl/UserInfo/Record?format=json"
        
        user_payload = {
            "UserInfo": {
                "employeeNo": user_id,
                "userType": "normal",
                "doorRight": "1",
                "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}],
                "Valid": {"enable": True, "beginTime": start_time, "endTime": end_time}
            }
        }

        try:
            try:
                del_url = f"{self.base_url}/ISAPI/AccessControl/UserInfo/Delete?format=json"
                del_payload = {"UserInfoDetail": {"mode": "byEmployeeNo", "EmployeeNoList": [{"employeeNo": user_id}]}}
                requests.put(del_url, data=json.dumps(del_payload), auth=self.auth, timeout=3, verify=False)
            except:
                pass

            resp = requests.post(user_url, data=json.dumps(user_payload), auth=self.auth, timeout=self.timeout, verify=False)
            
            if resp.status_code != 200:
                 modify_url = f"{self.base_url}/ISAPI/AccessControl/UserInfo/Modify?format=json"
                 requests.put(modify_url, data=json.dumps(user_payload), auth=self.auth, timeout=self.timeout, verify=False)

        except Exception as e:
            return False, f"Ulanish xatosi (User): {str(e)}"

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
            resp = requests.post(face_url, files=files, auth=self.auth, timeout=15, verify=False)
            
            self.set_access_group(user_id)

            try:
                data = resp.json()
                if data.get('statusCode') == 1 or resp.status_code == 200:
                    return True, "OK"
                return False, f"Rasm xatosi: {data.get('statusString', resp.text)}"
            except:
                return False, f"Rasm javobi xato: {resp.text}"

        except Exception as e:
            return False, f"Ulanish xatosi (Face): {str(e)}"

def _upload_single_device_task(dev_info: dict, user_id: str, image_bytes: bytes):
    ip = dev_info['ip']
    user = dev_info['user']
    password = dev_info['pass']
    try:
        client = HikDeviceClient(ip, user, password)
        success, msg = client.upload_face(user_id, image_bytes)
        return {"ip": ip, "success": success, "msg": msg}
    except Exception as e:
        return {"ip": ip, "success": False, "msg": f"System Error: {str(e)}"}

def upload_to_branch_devices(devices: List[dict], user_id: str, image_bytes: bytes):
    results = []
    max_threads = 10
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(_upload_single_device_task, dev, user_id, image_bytes) for dev in devices]
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                logger.error(f"Thread execution failed: {e}")
    return results
