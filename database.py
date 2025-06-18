from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import json
from datetime import datetime, UTC

SQLALCHEMY_DATABASE_URL = "sqlite:///./psychoscales.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False)
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime)
    last_seen = Column(DateTime)
    responses = relationship("ScaleResult", back_populates="user")

class ScaleResult(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    scale_id = Column(String, index=True)
    user_agent = Column(String)
    ip_address = Column(String)
    location = Column(JSON)
    raw_response = Column(JSON)
    sum_response = Column(JSON)
    avg_response = Column(JSON)
    created_at = Column(DateTime)
    user = relationship("User", back_populates="responses")

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def new_user() -> int:
    db = SessionLocal()
    try:
        with db.begin():
            user = User()
            user.last_seen = user.created_at = datetime.now(UTC)
            db.add(user)
            db.flush()
            return user.id
    finally:
        db.close()

