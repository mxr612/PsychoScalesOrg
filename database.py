from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, UTC
import json

SQLALCHEMY_DATABASE_URL = "sqlite:///./public/psychoscales.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ScaleResult(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True, index=True)
    scale_id = Column(String, index=True)
    user_agent = Column(String)
    ip_address = Column(String)
    location = Column(JSON)
    raw_response = Column(JSON)
    sum_response = Column(JSON)
    avg_response = Column(JSON)
    created_at = Column(DateTime, default=datetime.now(UTC))

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 