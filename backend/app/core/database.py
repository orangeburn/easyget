from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = "sqlite:///./easyget.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ConstraintModel(Base):
    __tablename__ = "constraints"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True)
    core_business = Column(JSON)
    qualifications = Column(JSON)
    geography_limits = Column(JSON)
    financial_thresholds = Column(JSON)
    other_constraints = Column(JSON)
    scan_frequency = Column(Integer, default=30) # Default 30 minutes
    custom_urls = Column(JSON, default=[])
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ClueModel(Base):
    __tablename__ = "clues"

    id = Column(String, primary_key=True, index=True) # Unique Hash
    title = Column(String, index=True)
    source = Column(String)
    url = Column(Text)
    snippet = Column(Text)
    publish_time = Column(DateTime, nullable=True)
    match_score = Column(Integer, nullable=True)
    veto_reason = Column(String, nullable=True)
    extracted_metadata = Column(JSON)
    full_text = Column(Text, nullable=True)
    user_feedback = Column(Integer, default=0) # 1: useful, -1: useless, 0: none
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 记录原始指纹用于去重
    fingerprint = Column(String, index=True)

# 自动创建表
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
