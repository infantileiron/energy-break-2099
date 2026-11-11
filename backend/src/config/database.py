from sqlalchemy import create_engine,text
from sqlalchemy.orm import DeclarativeBase,sessionmaker
from .settings import DATABASE_URL
class Base(DeclarativeBase): pass
engine=create_engine(DATABASE_URL,pool_pre_ping=True)
Session=sessionmaker(bind=engine,expire_on_commit=False)
def get_db():
 with Session() as db: yield db
def initialize():
 from .. import models
 Base.metadata.create_all(engine)
 # Additive upgrade for databases created before run claims were recorded.
 # Existing runs keep their ids, results, reviews and report snapshots; legacy
 # "running" rows have no claim time and become recoverable immediately.
 if engine.dialect.name=="postgresql":
  with engine.begin() as connection:
   for statement in (
    'ALTER TABLE runs ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0',
    'ALTER TABLE runs ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP NULL',
    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS claimed_by VARCHAR(100) NOT NULL DEFAULT ''",
    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS claim_token VARCHAR(36) NOT NULL DEFAULT ''",
   ):connection.execute(text(statement))
