from sqlalchemy import create_engine, Column, String, Integer, DateTime, JSON, Boolean, Text, text, inspect, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.core.paths import get_db_path

# Make DB path stable in both source and packaged desktop app modes.
DATABASE_URL = f"sqlite:///{get_db_path().as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_connection, _connection_record):
    """Reduce read/write blocking under concurrent desktop usage."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout = 30000")
    cursor.close()

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
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

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
    created_at = Column(DateTime, default=datetime.now)
    
    # 记录原始指纹用于去重
    fingerprint = Column(String, index=True)

class SystemSettingsModel(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    model_api_enabled = Column(Boolean, default=False)
    model_api_key = Column(Text, nullable=True)
    model_base_url = Column(Text, nullable=True)
    model_name = Column(Text, nullable=True)
    serper_api_enabled = Column(Boolean, default=False)
    serper_api_key = Column(Text, nullable=True)
    tavily_api_enabled = Column(Boolean, default=False)
    tavily_api_key = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

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
_ensure_column("system_settings", "model_api_enabled", "model_api_enabled BOOLEAN DEFAULT 0")
_ensure_column("system_settings", "model_api_key", "model_api_key TEXT")
_ensure_column("system_settings", "model_base_url", "model_base_url TEXT")
_ensure_column("system_settings", "model_name", "model_name TEXT")
_ensure_column("system_settings", "serper_api_enabled", "serper_api_enabled BOOLEAN DEFAULT 0")
_ensure_column("system_settings", "serper_api_key", "serper_api_key TEXT")
_ensure_column("system_settings", "tavily_api_enabled", "tavily_api_enabled BOOLEAN DEFAULT 0")
_ensure_column("system_settings", "tavily_api_key", "tavily_api_key TEXT")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
