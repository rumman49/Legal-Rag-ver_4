"""Database CRUD Service for Sessions and Messages with Auto-DB Creation."""
import json
import logging
import pymysql
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import engine, Base
from app.core.models import SessionModel, MessageModel

logger = logging.getLogger("db_service")


def ensure_mysql_database_exists():
    """Auto-creates MySQL database if it does not exist yet."""
    try:
        conn = pymysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            autocommit=True
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.MYSQL_DATABASE}` CHARACTER SET utf8mb4;")
        conn.close()
        logger.info(f"MySQL Database '{settings.MYSQL_DATABASE}' is ready.")
    except Exception as e:
        logger.warning(f"Could not auto-create MySQL database: {e}")


def init_db():
    """Creates database and tables."""
    ensure_mysql_database_exists()
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("MySQL Database tables initialized successfully!")
    except Exception as e:
        logger.warning(f"MySQL connection unavailable: {e}. Session history running in fallback mode.")


def create_session(
    db: Session,
    title: str = "New Legal Query",
    model: str = "groq",
    session_id: Optional[str] = None
) -> SessionModel:
    """Creates and returns a new session (or returns existing if ID matches)."""
    if session_id:
        existing = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if existing:
            if title and title != "New Legal Query" and existing.title == "New Legal Query":
                existing.title = title
                db.commit()
                db.refresh(existing)
            return existing
        session = SessionModel(id=session_id, title=title, model=model)
    else:
        session = SessionModel(title=title, model=model)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_all_sessions(db: Session) -> List[SessionModel]:
    """Retrieves all sessions sorted by creation time."""
    return db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()


def get_session_by_id(db: Session, session_id: str) -> Optional[SessionModel]:
    """Retrieves single session by ID."""
    return db.query(SessionModel).filter(SessionModel.id == session_id).first()


def delete_session(db: Session, session_id: str) -> bool:
    """Deletes a session and cascades deletion of its messages."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        return False
    db.delete(session)
    db.commit()
    return True


def delete_all_sessions(db: Session) -> int:
    """Deletes all sessions and their messages."""
    sessions = db.query(SessionModel).all()
    count = len(sessions)
    for s in sessions:
        db.delete(s)
    db.commit()
    return count


def clear_session_messages(db: Session, session_id: str) -> bool:
    """Removes all messages for a session and resets its title."""
    db.query(MessageModel).filter(MessageModel.session_id == session_id).delete()
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session:
        session.title = "New Legal Query"
    db.commit()
    return True


def get_session_messages(db: Session, session_id: str) -> List[MessageModel]:
    """Retrieves messages for a given session."""
    return db.query(MessageModel).filter(MessageModel.session_id == session_id).order_by(MessageModel.created_at.asc()).all()


def save_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
    citations: Optional[List[Dict[str, Any]]] = None
) -> MessageModel:
    """Saves a user or assistant message to database with auto-session fallback."""
    # Ensure session exists to avoid foreign key errors
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        session = SessionModel(id=session_id, title="New Legal Query")
        db.add(session)
        db.commit()
        db.refresh(session)

    # Auto-update session title on first user query
    if role == "user" and session.title in ("New Legal Query", "New Conversation"):
        clean_title = content.strip().replace("\n", " ")[:45]
        if clean_title:
            session.title = clean_title
            db.commit()

    sources = json.dumps(citations, ensure_ascii=False) if citations else None
    msg = MessageModel(
        session_id=session_id,
        role=role,
        content=content,
        sources_json=sources
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

