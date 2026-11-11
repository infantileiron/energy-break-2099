import csv,io,math
from datetime import datetime,timezone

def parse_time(value):
 try:
  t=datetime.fromisoformat(str(value).replace("Z","+00:00"))
  if t.tzinfo is None:raise ValueError()
  return t.astimezone(timezone.utc)
 except Exception:raise ValueError("时间须为带时区的ISO8601格式")

def parse_csv(text):
 rows=list(csv.DictReader(io.StringIO(text)))
 required={"timestamp","kwh","output_kg","status"}
 if not rows or len(rows)>5000 or not required.issubset(rows[0]):raise ValueError("CSV需1至5000行，并含timestamp,kwh,output_kg,status")
 result=[];seen=set()
 for index,row in enumerate(rows,2):
  timestamp=parse_time(row.get("timestamp")).isoformat()
  if timestamp in seen:raise ValueError(f"第{index}行时间重复（已统一UTC）")
  seen.add(timestamp)
  status=(row.get("status") or "").strip()
  if status not in ["running","stopped"]:raise ValueError(f"第{index}行状态应为running/stopped")
  values={}
  for key in ["kwh","output_kg"]:
   raw=row.get(key)
   if raw is None or raw.strip()=="":values[key]=None;continue
   try:value=float(raw)
   except Exception:raise ValueError(f"第{index}行{key}必须为数值或空值")
   if not math.isfinite(value) or value<0:raise ValueError(f"第{index}行{key}必须非负且有限")
   values[key]=value
  result.append({"timestamp":timestamp,"status":status,**values})
 return sorted(result,key=lambda r:r["timestamp"])

def normalize(readings,start_at,end_at):
 start=parse_time(start_at);end=parse_time(end_at);valid=[];excluded=[]
 for row in sorted(readings,key=lambda r:r["timestamp"]):
  if not start<=parse_time(row["timestamp"])<=end:continue
  reason="stopped" if row["status"]=="stopped" else "missing_measurement" if row["kwh"] is None or row["output_kg"] is None else "zero_output" if row["output_kg"]==0 else ""
  if reason:excluded.append({"timestamp":row["timestamp"],"reason":reason});continue
  intensity=row["kwh"]/row["output_kg"]
  if not math.isfinite(intensity):raise ValueError("归一能耗非有限，检查极小产量")
  valid.append({**row,"intensity":intensity})
 if len(valid)<8:raise ValueError("窗口内至少需要8条有效运行观测；停机、零产量与缺测已隔离")
 return valid,excluded
