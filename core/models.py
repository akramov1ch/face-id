from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, BigInteger, DateTime, func
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()

# Qurilma turlari (Kirish, Chiqish yoki Universal)
class DeviceType(enum.Enum):
    ENTRY = "entry"
    EXIT = "exit"
    UNIVERSAL = "universal"

class Admin(Base):
    __tablename__ = 'admins'
    user_id = Column(BigInteger, primary_key=True) # Telegram ID

class Branch(Base):
    __tablename__ = 'branches'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False) # Filial nomi
    attendance_sheet_id = Column(String, nullable=True) # Shu filial uchun Sheet ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Bog'lanishlar (Relations)
    devices = relationship("Device", back_populates="branch", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="branch")

class Device(Base):
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey('branches.id'))
    
    ip_address = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    
    # Qurilma turi (Kirish/Chiqish)
    device_type = Column(Enum(DeviceType), default=DeviceType.UNIVERSAL)

    branch = relationship("Branch", back_populates="devices")

class Employee(Base):
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String, unique=True, index=True, nullable=False) # ID (101)
    full_name = Column(String, nullable=False)
    branch_id = Column(Integer, ForeignKey('branches.id'))
    
    photo_status = Column(Boolean, default=False) # Rasm yuklanganmi?

    # --- YANGI QO'SHILGAN USTUN ---
    # Xodim kelib-ketganda xabar boradigan Telegram ID
    notification_chat_id = Column(BigInteger, nullable=True) 

    branch = relationship("Branch", back_populates="employees")