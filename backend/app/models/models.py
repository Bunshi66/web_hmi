from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    event_type = Column(String)
    message = Column(String)

class Defect(Base):
    __tablename__ = "defects"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    defect_type = Column(String)
    confidence = Column(Float)
    bbox_data = Column(JSON)
    image_path = Column(String)

class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    level = Column(String, default="INFO")
    ip_address = Column(String)
    message = Column(String)

class ConnectionSettings(Base):
    __tablename__ = "connection_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    target_ip = Column(String, default="192.168.1.64")
    auto_reconnect = Column(Integer, default=1) # 1 for True, 0 for False (SQLite boolean compat)
    reconnect_interval = Column(Integer, default=5)