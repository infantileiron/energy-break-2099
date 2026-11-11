import os,sys,copy
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from pathlib import Path

# Tests use an isolated SQLite database and an in-memory queue double.
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"backend"))
os.environ["DATABASE_URL"]="sqlite:////tmp/qingyu-run-recovery-tests.db"
if os.path.exists("/tmp/qingyu-run-recovery-tests.db"):os.remove("/tmp/qingyu-run-recovery-tests.db")

import pytest
from sqlalchemy import func,select,update
from src.config.database import Base,engine,Session
from src.models import ChangeRun,MeterDataset,OperatingWindow,ChangeStudy,IncidentReview,Report
from src.models.common import now,serialize
from src.schemas.review import ReviewCreate
from src.schemas.report import ReportCreate
from src.services import run_service,review_service,report_service
import src.utils.queue as queue_module
import src.worker as worker_module

COUNT=60

class FakeRedis:
 def __init__(self):self.lists={}
 def rpush(self,key,*values):self.lists.setdefault(key,[]).extend(values);return len(self.lists[key])
 def blpop(self,key,timeout=0):
  values=self.lists.get(key) or []
  return (key,values.pop(0)) if values else None
 def ping(self):return True

def _readings():
 start=datetime(2026,10,1,tzinfo=timezone.utc)
 rows=[]
 for i in range(COUNT):
  output=200.
  rows.append({"timestamp":(start+timedelta(hours=i)).isoformat(),
               "kwh":output*2.0,"output_kg":output,"status":"running"})
 return start,rows

def _seed_study(db,config=None):
 start,readings=_readings()
 db.add(MeterDataset(id="ds",name="测试批次",readings=readings,description=""))
 db.add(OperatingWindow(id="win",name="测试窗口",start_at=start.isoformat(),
                        end_at=(start+timedelta(hours=COUNT-1)).isoformat(),note=""))
 db.add(ChangeStudy(id="study",name="测试研究",dataset_id="ds",window_id="win",
                    config=config or {"penalty":6.,"min_segment":24,
                                      "anomaly_threshold":3.5,"noise_floor":.02}))
 db.commit()

def _create_run(db):
 _seed_study(db)
 return run_service.create(db,SimpleNamespace(study_id="study"))

def _row(db,run_id):
 db.expire_all()
 return db.get(ChangeRun,run_id)

def _expire(db,run_id,seconds=10):
 db.execute(update(ChangeRun).where(ChangeRun.id==run_id)
            .values(claimed_at=now()-timedelta(seconds=seconds)))
 db.commit()

@pytest.fixture(autouse=True)
def isolated(monkeypatch):
 Base.metadata.drop_all(engine)
 Base.metadata.create_all(engine)
 fake=FakeRedis()
 monkeypatch.setattr(queue_module,"client",lambda:fake)
 monkeypatch.setattr(worker_module,"client",lambda:fake)
 return fake

def test_interrupted_after_claim_resumes_same_record():
 with Session() as db:
  run=_create_run(db);run_id=run.id
  assert run_service.claim(db,run_id,"worker-a",stale_after=60)
  assert _row(db,run_id).status=="running"
  assert _row(db,run_id).attempts==1
 # Worker "crashes" here: the row stays running and nothing is published.
 with Session() as db:
  _expire(db,run_id)
  completed=run_service.recover(db,"worker-b",stale_after=5)
  row=_row(db,run_id)
  assert completed==[run_id]
  assert row.id==run_id and row.status=="completed"
  assert row.attempts==2
  assert row.result["valid_count"]==COUNT
  assert db.scalar(select(func.count()).select_from(ChangeRun))==1

def test_duplicate_delivery_leaves_completed_result_untouched():
 with Session() as db:
  run=_create_run(db);run_id=run.id
  assert run_service.process(db,run_id,"worker-a")
  original=copy.deepcopy(_row(db,run_id).result)
  attempts=_row(db,run_id).attempts
  # Same queue entry delivered again, or a second copy of it.
  assert run_service.process(db,run_id,"worker-b") is False
  row=_row(db,run_id)
  assert row.status=="completed" and row.attempts==attempts
  assert row.result==original

def test_concurrent_claims_have_one_winner():
 with Session() as db:
  run=_create_run(db);run_id=run.id
  with Session() as first,Session() as second:
   token_a=run_service.claim(first,run_id,"worker-a",stale_after=60)
   token_b=run_service.claim(second,run_id,"worker-b",stale_after=60)
  assert token_a and token_b is None
  row=_row(db,run_id)
  assert row.status=="running" and row.attempts==1 and row.claimed_by=="worker-a"

def test_stale_late_result_cannot_overwrite_newer_result():
 with Session() as db:
  run=_create_run(db);run_id=run.id
  old_token=run_service.claim(db,run_id,"worker-a",stale_after=60)
  _expire(db,run_id)
  new_token=run_service.claim(db,run_id,"worker-b",stale_after=5)
  assert old_token!=new_token
  # The replacement worker publishes first.
  assert run_service.publish_result(db,run_id,new_token,{"marker":"new"})
  # The old, expired computation arrives late and must be discarded.
  assert run_service.publish_result(db,run_id,old_token,{"marker":"old"}) is False
  assert _row(db,run_id).result=={"marker":"new"}

def test_failure_reason_is_visible_and_not_retried_automatically():
 with Session() as db:
  _seed_study(db,{"penalty":0.,"min_segment":24,
                  "anomaly_threshold":3.5,"noise_floor":.02})
  run=run_service.create(db,SimpleNamespace(study_id="study"));run_id=run.id
  assert run_service.process(db,run_id,"worker-a") is False
  row=_row(db,run_id)
  assert row.status=="failed"
  assert "分段参数" in row.error
  assert row.attempts==1
  assert serialize(row)["error"]==row.error
  # A duplicate delivery must not erase the recorded reason or retry blindly.
  assert run_service.process(db,run_id,"worker-b") is False
  assert _row(db,run_id).status=="failed"
  assert _row(db,run_id).error==row.error

def test_existing_review_and_archived_report_keep_original_result():
 with Session() as db:
  run=_create_run(db);run_id=run.id
  assert run_service.process(db,run_id,"worker-a")
  original=copy.deepcopy(_row(db,run_id).result)
  review=review_service.create(db,ReviewCreate(run_id=run_id,
   action="核对换料与计量日志，暂不认定为设备故障。"))
  review_service.approve(db,review,SimpleNamespace(email="admin@energy.demo"))
  report=report_service.create(db,ReportCreate(review_id=review.id,title="归档底稿"))
  snapshot=copy.deepcopy(report.snapshot)
  # Duplicate delivery after archival must not recompute the completed run.
  assert run_service.process(db,run_id,"worker-b") is False
  assert _row(db,run_id).result==original
  assert _row(db,run_id).status=="completed"
  assert db.get(IncidentReview,review.id).run_id==run_id
  assert db.get(Report,report.id).snapshot==snapshot
  assert db.scalar(select(func.count()).select_from(ChangeRun))==1

def test_lost_queue_notification_is_recovered_by_worker_sweep():
 fake=queue_module.client()
 with Session() as db:
  run=_create_run(db);run_id=run.id
  # Simulate BLPOP taking the entry and the process dying before the claim.
  fake.blpop(queue_module.QUEUE,timeout=0)
  assert run_service.recoverable_ids(db)==[run_id]
  worker_module.run_once(db)
  row=_row(db,run_id)
  assert row.status=="completed"
  assert row.attempts==1

def test_repeated_interruptions_end_in_visible_failure(monkeypatch):
 monkeypatch.setattr(run_service,"MAX_ATTEMPTS",2)
 with Session() as db:
  run=_create_run(db);run_id=run.id
  assert run_service.claim(db,run_id,"worker-a",stale_after=60)
  _expire(db,run_id)
  assert run_service.claim(db,run_id,"worker-b",stale_after=5)
  _expire(db,run_id)
  assert run_service.claim(db,run_id,"worker-c",stale_after=5) is None
  row=_row(db,run_id)
  assert row.status=="failed"
  assert row.error==run_service.EXHAUSTED_ERROR
  assert row.attempts==2
