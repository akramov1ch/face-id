import json
import redis
import logging
from core.config import settings
from core.models import Device, Employee, Branch

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self):
        try:
            self.redis = redis.Redis(
                host=settings.REDIS_HOST, 
                port=settings.REDIS_PORT, 
                db=0, 
                decode_responses=True, 
                socket_timeout=2
            )
            self.redis.ping()
            logger.info(f"✅ Redis ulandi: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.error(f"❌ Redisga ulanishda xatolik: {e}")
            self.redis = None

        self.TTL = 3600  

    def get_device_info(self, ip: str):
        if not self.redis: return None
        try:
            key = f"device:{ip}"
            data = self.redis.get(key)
            if data: return json.loads(data)
        except Exception as e:
            logger.error(f"Redis get_device error: {e}")
        return None

    def set_device_info(self, device: Device, branch: Branch):
        if not self.redis: return
        try:
            key = f"device:{device.ip_address}"
            data = {
                "device_type": device.device_type.value,
                "branch_id": branch.id,
                "branch_name": branch.name,
                "sheet_id": branch.attendance_sheet_id
            }
            self.redis.set(key, json.dumps(data), ex=self.TTL)
        except Exception as e:
            logger.error(f"Redis set_device error: {e}")

    def get_employee_info(self, emp_id: str):
        if not self.redis: return None
        try:
            key = f"emp:{emp_id}"
            data = self.redis.get(key)
            if data: return json.loads(data)
        except Exception as e:
            logger.error(f"Redis get_employee error: {e}")
        return None

    def set_employee_info(self, employee: Employee):
        if not self.redis: return
        try:
            key = f"emp:{employee.account_id}"
            data = {
                "full_name": employee.full_name,
                "chat_id": employee.notification_chat_id
            }
            self.redis.set(key, json.dumps(data), ex=self.TTL)
        except Exception as e:
            logger.error(f"Redis set_employee error: {e}")
    def check_action_state(self, emp_id: str, new_action: str) -> bool:

        if not self.redis: return True 

        try:
            key = f"state:{emp_id}" 
            
            last_action = self.redis.get(key) 

            if last_action == new_action:
                return False

            self.redis.set(key, new_action, ex=64800)
            
            return True
        except Exception as e:
            logger.error(f"Redis state check error: {e}")
            return True 

cache = CacheManager()