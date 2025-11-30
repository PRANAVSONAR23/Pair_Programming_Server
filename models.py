from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from database import Base

class Room(Base):
    __tablename__ = "rooms"

    room_id = Column(String(255), primary_key=True, index=True)
    code = Column(Text, default="")
    language = Column(String(50), default="python")
    active_users = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def __repr__(self):
        return f"<Room(room_id={self.room_id}, language={self.language})>"