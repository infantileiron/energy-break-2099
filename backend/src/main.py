import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from .config.database import initialize,Session
from .config.settings import SEED_DEMO
from .utils.queue import client
from .middlewares.audit import AuditMiddleware
from .middlewares.errors import ErrorMiddleware
from .routes import auth,datasets,windows,studies,runs,reviews,reports,audit
@asynccontextmanager
async def lifespan(app):
 initialize()
 if SEED_DEMO:
  try:
   from scripts.seed_demo import seed
   seed()
  except Exception:logging.exception("Demo seed failed; app remains available")
 yield
app=FastAPI(title="青屿陶窑 · 能耗工况变点",lifespan=lifespan)
app.add_middleware(AuditMiddleware);app.add_middleware(ErrorMiddleware)
for module in [auth,datasets,windows,studies,runs,reviews,reports,audit]:app.include_router(module.router)
@app.get("/health")
def health():
 with Session() as db:db.execute(text("SELECT 1"))
 client().ping();return {"status":"ok"}
