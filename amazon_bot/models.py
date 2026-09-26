from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.sql import func
from amazon_bot.database import Base

class Conversation(Base):
    __tablename__ = "conversations"

    session_id = Column(String, primary_key=True, index=True)
    history = Column(JSON, default=list)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class HumanTicket(Base):
    __tablename__ = "human_tickets"

    ticket_id = Column(String, primary_key=True, index=True)
    status = Column(String, default="queued")
    payload = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    claimed_at = Column(DateTime(timezone=True), nullable=True)
