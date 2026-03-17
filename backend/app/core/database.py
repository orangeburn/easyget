from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Boolean, Text, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Make DB path stable regardless of current working directory
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DB_PATH = os.path.join(_BASE_DIR, "easyget.db").replace("\\", "/")
DATABASE_URL = f"sqlite:///{_DB_PATH}"

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
    wechat_accounts = Column(JSON, default=[])
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ClueModel(Base):
    __tablename__ = "clues"

    id = Column(String, primary_key=True, index=True) # Unique Hash
    title = Column(String, index=True)
    source = Column(String)
    url = Column(Text)
    snippet = Column(Text)
    publish_time = Column(DateTime, nullable=True)
    semantic_score = Column(Integer, nullable=True)
    veto_reason = Column(String, nullable=True)
    extracted_metadata = Column(JSON)
    full_text = Column(Text, nullable=True)
    markdown_text = Column(Text, nullable=True)
    user_feedback = Column(Integer, default=0) # 1: useful, -1: useless, 0: none
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 记录原始指纹用于去重
    fingerprint = Column(String, index=True)

# 自动创建表
Base.metadata.create_all(bind=engine)

# 轻量级迁移：确保新增字段存在（SQLite 支持 ADD COLUMN）
def _ensure_column(table_name: str, column_name: str, column_def: str) -> None:
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    if column_name in columns:
        return
    with engine.connect() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_def}"))

_ensure_column("clues", "semantic_score", "semantic_score INTEGER")
_ensure_column("clues", "markdown_text", "markdown_text TEXT")
_ensure_column("constraints", "wechat_accounts", "wechat_accounts JSON")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
