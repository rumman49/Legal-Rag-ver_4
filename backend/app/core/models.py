"""SQLAlchemy ORM Models for Chat Sessions and Messages."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class SessionModel(Base):
    """Stores user chat sessions."""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="New Legal Query")
    model = Column(String(100), nullable=False, default="gemini")
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan")


class MessageModel(Base):
    """Stores turn-by-turn chat messages with citations."""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    sources_json = Column(Text, nullable=True)  # JSON string of retrieved citations
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("SessionModel", back_populates="messages")
