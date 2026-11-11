from uuid import uuid4
from fastapi import HTTPException
from ..models.run import ChangeRun
from ..models.study import ChangeStudy
from ..models.dataset import MeterDataset
from ..models.window import OperatingWindow
from ..utils.queue import enqueue
from .readings import normalize
from .change_points import detect
from .robust_scores import score

def create(db,body):
 if not db.get(ChangeStudy,body.study_id):raise HTTPException(422,"研究不存在")
 row=ChangeRun(id=str(uuid4()),study_id=body.study_id,status="queued",result={},error="");db.add(row);db.commit()
 try:enqueue(row.id)
 except Exception:
  row.status="failed";row.error="Redis队列不可用，请稍后重试";db.commit();raise HTTPException(503,row.error)
 return row

def compute(db,run_id):
 row=db.get(ChangeRun,run_id)
 if row is None or row.status not in ["queued","running"]:return
 row.status="running";db.commit()
 try:
  study=db.get(ChangeStudy,row.study_id);dataset=db.get(MeterDataset,study.dataset_id);window=db.get(OperatingWindow,study.window_id)
  observations,excluded=normalize(dataset.readings,window.start_at,window.end_at);values=[r["intensity"] for r in observations];config=study.config
  changes=detect(values,config["penalty"],config["min_segment"]);robust=score(values,changes["segments"],config["anomaly_threshold"],config["noise_floor"])
  for segment in changes["segments"]:
   segment["start_at"]=observations[segment["start_index"]]["timestamp"];segment["end_at"]=observations[segment["end_index"]-1]["timestamp"]
  for index,obs in enumerate(observations):obs.update(score=robust["scores"][index],baseline=robust["baselines"][index],anomaly=index in robust["anomaly_indices"])
  row.result={"observations":observations,"excluded":excluded,"changes":changes,"robust":robust,"valid_count":len(observations),"excluded_count":len(excluded),"anomaly_count":len(robust["anomaly_indices"]),"dataset_name":dataset.name,"window_name":window.name,"config":config};row.status="completed"
 except Exception as e:row.status="failed";row.error=str(e)[:1000]
 db.commit()
