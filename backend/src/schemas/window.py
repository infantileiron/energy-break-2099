from datetime import datetime
from pydantic import BaseModel,Field,model_validator
class WindowCreate(BaseModel):
 name:str=Field(min_length=2,max_length=100)
 start_at:str
 end_at:str
 note:str=Field(default="",max_length=1000)
 @model_validator(mode="after")
 def dates(self):
  try:
   a=datetime.fromisoformat(self.start_at.replace("Z","+00:00"));b=datetime.fromisoformat(self.end_at.replace("Z","+00:00"))
   if a.tzinfo is None or b.tzinfo is None or b<=a:raise ValueError()
  except Exception:raise ValueError("窗口须含时区，结束时间必须晚于开始时间")
  return self
