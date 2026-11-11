from uuid import uuid4
from sqlalchemy import select
from fastapi import HTTPException
from ..models.window import OperatingWindow

def create(db,body):
 if db.scalar(select(OperatingWindow).where(OperatingWindow.name==body.name)):raise HTTPException(409,"工况窗口名称已存在")
 row=OperatingWindow(id=str(uuid4()),**body.model_dump());db.add(row);db.commit();return row
