import datetime
from sqlalchemy import Column, ForeignKey, Index, Integer, String, DateTime, Float, JSON
from sqlalchemy.orm import relationship

from api.database.core import Base
from api.enums import SessionStatus, SessionPhase, NodeStatus, SessionStateMachine


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
    __table_args__ = (
        Index("ix_sessions_user_status", "user_id", "status"),
    )

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    topic = Column(String, index=True)
    status = Column(String, default=SessionStatus.INITIALIZING.value)
    error_message = Column(String, nullable=True)
    current_phase = Column(String, default=SessionPhase.ROOT.value)
    course_mode = Column(String, default="detailed")
    langgraph_thread_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="sessions")
    nodes = relationship("NodeState", back_populates="session")

    @property
    def parsed_status(self) -> SessionStatus | None:
        try:
            return SessionStatus(self.status) if self.status else None
        except ValueError:
            return None

    def can_transition_to(self, new_status: str | SessionStatus) -> bool:
        return SessionStateMachine.can_transition(self.status, new_status)


class NodeState(Base):
    __tablename__ = "nodes"
    __table_args__ = (
        Index("ix_nodes_session_node", "session_id", "node_id"),
        Index("ix_nodes_score", "score"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    node_id = Column(String)
    node_type = Column(String)
    status = Column(String, default=NodeStatus.UNLOCKED.value)
    content = Column(JSON, nullable=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    session = relationship("Session", back_populates="nodes")

    @property
    def parsed_status(self) -> NodeStatus | None:
        try:
            return NodeStatus(self.status) if self.status else None
        except ValueError:
            return None
