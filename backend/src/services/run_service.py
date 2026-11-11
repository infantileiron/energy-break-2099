import logging
from datetime import timedelta
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import or_,and_,select,update
from ..models.run import ChangeRun
from ..models.study import ChangeStudy
from ..models.dataset import MeterDataset
from ..models.window import OperatingWindow
from ..models.common import now
from ..config.settings import RUN_LEASE_SECONDS,RUN_MAX_ATTEMPTS
from ..utils.queue import enqueue
from .readings import normalize
from .change_points import detect
from .robust_scores import score

log=logging.getLogger(__name__)
LEASE_SECONDS=RUN_LEASE_SECONDS
MAX_ATTEMPTS=max(1,RUN_MAX_ATTEMPTS)
EXHAUSTED_ERROR="计算多次中断且未能完成，已停止自动恢复；请查看运行记录或重新创建运行"

def _cutoff(stale_after):
 age=LEASE_SECONDS if stale_after is None else stale_after
 return now()-timedelta(seconds=max(0,age))

def _reclaimable(cutoff,max_attempts):
 # A queued row may have lost its Redis notification (worker crashed after
 # BLPOP); every sweep can claim it directly. A running row is recoverable
 # only after its lease expires, including legacy rows with no claim time.
 return and_(
  ChangeRun.attempts<max_attempts,
  or_(
   ChangeRun.status=="queued",
   and_(ChangeRun.status=="running",
        or_(ChangeRun.claimed_at.is_(None),ChangeRun.claimed_at<cutoff))))

def claim(db,run_id,worker_id,stale_after=None,max_attempts=None):
 """Atomically claim a queued or abandoned run. Returns the fencing token.

 The conditional UPDATE is the arbitration point: duplicate queue deliveries
 and concurrent workers race here, but only the first matching update wins.
 The returned token must be presented when publishing a result.
 """
 max_a=MAX_ATTEMPTS if max_attempts is None else max_attempts
 cutoff=_cutoff(stale_after);token=str(uuid4())
 result=db.execute(update(ChangeRun).where(
  ChangeRun.id==run_id,
  _reclaimable(cutoff,max_a)
 ).values(status="running",claimed_by=worker_id,claim_token=token,
          claimed_at=now(),attempts=ChangeRun.attempts+1,error="")
 .execution_options(synchronize_session=False))
 db.commit()
 if result.rowcount==1:return token
 # An abandoned run that has used up its recovery budget must not hang forever.
 if max_a>0:
  exhausted=db.execute(update(ChangeRun).where(
   ChangeRun.id==run_id,
   ChangeRun.status=="running",
   ChangeRun.attempts>=max_a,
   or_(ChangeRun.claimed_at.is_(None),ChangeRun.claimed_at<cutoff)
  ).values(status="failed",error=EXHAUSTED_ERROR,claimed_at=now(),claim_token="")
   .execution_options(synchronize_session=False))
  db.commit()
  if exhausted.rowcount==1:log.warning("run %s exhausted %s attempts",run_id,max_a)
 return None

def recoverable_ids(db,stale_after=None,max_attempts=None):
 max_a=MAX_ATTEMPTS if max_attempts is None else max_attempts
 return list(db.scalars(select(ChangeRun.id).where(
  _reclaimable(_cutoff(stale_after),max_a))).all())

def _build_result(db,run_id):
 row=db.get(ChangeRun,run_id)
 if row is None:raise ValueError("运行记录不存在")
 study=db.get(ChangeStudy,row.study_id)
 if study is None:raise ValueError("研究不存在，无法计算")
 dataset=db.get(MeterDataset,study.dataset_id)
 window=db.get(OperatingWindow,study.window_id)
 if dataset is None or window is None:raise ValueError("观测批次或工况窗口不存在，无法计算")
 observations,excluded=normalize(dataset.readings,window.start_at,window.end_at)
 values=[r["intensity"] for r in observations];config=study.config
 changes=detect(values,config["penalty"],config["min_segment"])
 robust=score(values,changes["segments"],config["anomaly_threshold"],config["noise_floor"])
 for segment in changes["segments"]:
  segment["start_at"]=observations[segment["start_index"]]["timestamp"]
  segment["end_at"]=observations[segment["end_index"]-1]["timestamp"]
 for index,obs in enumerate(observations):
  obs.update(score=robust["scores"][index],baseline=robust["baselines"][index],
             anomaly=index in robust["anomaly_indices"])
 return {"observations":observations,"excluded":excluded,"changes":changes,
         "robust":robust,"valid_count":len(observations),
         "excluded_count":len(excluded),
         "anomaly_count":len(robust["anomaly_indices"]),
         "dataset_name":dataset.name,"window_name":window.name,"config":config}

def publish_result(db,run_id,token,result):
 """Publish only if this worker still owns the current claim.

 A late result from an expired claim loses the token comparison and is
 discarded, so it can never overwrite a newer result.
 """
 published=db.execute(update(ChangeRun).where(
  ChangeRun.id==run_id,
  ChangeRun.status=="running",
  ChangeRun.claim_token==token
 ).values(status="completed",result=result,error="")
 .execution_options(synchronize_session=False))
 db.commit()
 if published.rowcount!=1:log.warning("discarded stale result for run %s",run_id)
 return published.rowcount==1

def publish_failure(db,run_id,token,error):
 failed=db.execute(update(ChangeRun).where(
  ChangeRun.id==run_id,
  ChangeRun.status=="running",
  ChangeRun.claim_token==token
 ).values(status="failed",error=str(error)[:1000])
 .execution_options(synchronize_session=False))
 db.commit()
 return failed.rowcount==1

def process(db,run_id,worker_id="worker",stale_after=None,max_attempts=None):
 """Claim, calculate and publish one run, reusing the existing run row."""
 token=claim(db,run_id,worker_id,stale_after,max_attempts)
 if token is None:return False
 try:result=_build_result(db,run_id)
 except Exception as error:
  publish_failure(db,run_id,token,error)
  return False
 return publish_result(db,run_id,token,result)

def recover(db,worker_id="worker",stale_after=None,max_attempts=None):
 """Resume queued or abandoned runs, including lost queue notifications."""
 completed=[]
 for run_id in recoverable_ids(db,stale_after,max_attempts):
  if process(db,run_id,worker_id,stale_after,max_attempts):completed.append(run_id)
 return completed

def create(db,body):
 if not db.get(ChangeStudy,body.study_id):raise HTTPException(422,"研究不存在")
 row=ChangeRun(id=str(uuid4()),study_id=body.study_id,status="queued",result={},error="",
               attempts=0,claimed_at=None,claimed_by="",claim_token="")
 db.add(row);db.commit()
 try:enqueue(row.id)
 except Exception:
  row.status="failed";row.error="Redis队列不可用，请稍后重试";db.commit();raise HTTPException(503,row.error)
 return row

def compute(db,run_id):
 """Backward-compatible inline entry point used by the demo seed."""
 return process(db,run_id,"inline")
