import os,socket,time,logging
from uuid import uuid4
from pathlib import Path
from .config.database import Session
from .utils.queue import client,QUEUE
from .services.run_service import process,recoverable_ids
heartbeat=Path("/artifacts/worker-heartbeat")
worker_id=os.getenv("WORKER_ID") or f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
log=logging.getLogger("worker")

def run_once(db):
 # The queue entry is only a wake-up hint. Recovery also scans the database,
 # so an entry lost after BLPOP (or a run abandoned mid-flight) is not lost.
 run_ids=set()
 item=client().blpop(QUEUE,timeout=2)
 if item:run_ids.add(item[1])
 run_ids.update(recoverable_ids(db))
 for run_id in run_ids:
  try:process(db,run_id,worker_id)
  except Exception:
   log.exception("Worker process error for run %s",run_id)
   db.rollback()

def main():
 while True:
  try:
   heartbeat.touch()
   with Session() as db:run_once(db)
  except Exception:log.exception("Worker loop error");time.sleep(2)

if __name__=="__main__":main()
