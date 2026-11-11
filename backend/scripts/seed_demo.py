import json,random,math
from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func
from src.config.database import initialize,Session
from src.models import MeterDataset,OperatingWindow,ChangeStudy,ChangeRun,IncidentReview,Report,User
from src.utils.security import hash_password
from src.services.run_service import compute

def make_readings():
 rng=random.Random(20261112);rows=[]
 for i in range(720):
  output=160+rng.uniform(-15,15);level=2.4 if i<240 else 3.25 if i<480 else 2.7
  intensity=level+.025*math.sin(i/7)+rng.gauss(0,.018)
  if i in [110,390,610]:intensity+=1.2
  row={"timestamp":(datetime(2026,10,1,tzinfo=timezone.utc)+timedelta(hours=i)).isoformat(),"kwh":round(output*intensity,4),"output_kg":round(output,4),"status":"running"}
  if i in [55,56,300,301]:row.update(status="stopped",kwh=8.,output_kg=0.)
  if i==420:row["output_kg"]=0.
  if i==500:row["kwh"]=None
  rows.append(row)
 return rows

def seed():
 initialize()
 with Session() as db:
  for role in ["admin","analyst","viewer"]:
   email=role+"@energy.demo"
   if not db.scalar(select(User).where(User.email==email)):db.add(User(id="user-"+role,email=email,role=role,password_hash=hash_password("KilnDemo2026!")))
  if not db.get(MeterDataset,"demo-dataset"):db.add(MeterDataset(id="demo-dataset",name="青屿一号窑 2026年10月",readings=make_readings(),description="720条小时电量/产量，包含停机、零产量和缺测样例"))
  if not db.get(OperatingWindow,"demo-window"):db.add(OperatingWindow(id="demo-window",name="十月全月工况",start_at="2026-10-01T00:00:00+00:00",end_at="2026-10-30T23:00:00+00:00",note="含停机观测，计算时单独隔离；最小段长以有效观测数计"))
  db.commit()
  if not db.get(ChangeStudy,"demo-study"):db.add(ChangeStudy(id="demo-study",name="一号窑换料工况复核",dataset_id="demo-dataset",window_id="demo-window",config={"penalty":6.,"min_segment":24,"anomaly_threshold":3.5,"noise_floor":.02}))
  db.commit()
  if not db.get(ChangeRun,"demo-run"):db.add(ChangeRun(id="demo-run",study_id="demo-study",status="queued",result={},error=""));db.commit();compute(db,"demo-run")
  if not db.get(IncidentReview,"demo-review"):db.add(IncidentReview(id="demo-review",run_id="demo-run",action="核对10月11日与21日换料记录，单独复查三个尖峰时段的计量和批次，暂不认定为设备故障。",state="approved",reviewer="admin@energy.demo"))
  db.commit()
  if not db.get(Report,"demo-report"):db.add(Report(id="demo-report",review_id="demo-review",title="一号窑十月能耗复核底稿",snapshot={"result":db.get(ChangeRun,"demo-run").result,"action":db.get(IncidentReview,"demo-review").action,"reviewer":"admin@energy.demo"}))
  db.commit()
  return {cls.__tablename__:db.scalar(select(func.count()).select_from(cls)) for cls in [User,MeterDataset,OperatingWindow,ChangeStudy,ChangeRun,IncidentReview,Report]}
if __name__=="__main__":print(json.dumps(seed(),ensure_ascii=False))
