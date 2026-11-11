from uuid import uuid4
from sqlalchemy import select
from fastapi import HTTPException
from ..models.study import ChangeStudy
from ..models.dataset import MeterDataset
from ..models.window import OperatingWindow

def create(db,body):
 if not db.get(MeterDataset,body.dataset_id) or not db.get(OperatingWindow,body.window_id):raise HTTPException(422,"观测批次或工况窗口不存在")
 if db.scalar(select(ChangeStudy).where(ChangeStudy.name==body.name)):raise HTTPException(409,"研究名称已存在")
 row=ChangeStudy(id=str(uuid4()),name=body.name,dataset_id=body.dataset_id,window_id=body.window_id,config={k:getattr(body,k) for k in ["penalty","min_segment","anomaly_threshold","noise_floor"]});db.add(row);db.commit();return row
