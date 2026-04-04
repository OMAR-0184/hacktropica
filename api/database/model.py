import datetime
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Float, JSON
from sqlalchemy.orm import relationship

from api.database.core import Base


def utc_now():
    """Return a timezone-naive UTC datetime compatible with TIMESTAMP WITHOUT TIME ZONE"""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=utc_now)

    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)  
    user_id = Column(Integer, ForeignKey("users.id"))
    topic = Column(String, index=True)
    status = Column(String, default="initializing")  
    error_message = Column(String, nullable=True)
    current_phase = Column(String, default="root")  
    course_mode = Column(String, default="detailed") 
    langgraph_thread_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="sessions")
    nodes = relationship("NodeState", back_populates="session")


class NodeState(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    node_id = Column(String)  
    node_type = Column(String)  
    status = Column(String)  
    content = Column(JSON, nullable=True)  
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    session = relationship("Session", back_populates="nodes")
