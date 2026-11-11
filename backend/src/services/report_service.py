import csv,io
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from ..models.review import IncidentReview
from ..models.run import ChangeRun
from ..models.report import Report

def create(db,body):
 review=db.get(IncidentReview,body.review_id)
 if review is None or review.state!="approved":raise HTTPException(409,"报告必须关联已批准的复核")
 existing=db.scalar(select(Report).where(Report.review_id==body.review_id))
 if existing:return existing
 run=db.get(ChangeRun,review.run_id);row=Report(id=str(uuid4()),review_id=review.id,title=body.title,snapshot={"result":run.result,"action":review.action,"reviewer":review.reviewer});db.add(row);db.commit();return row

def export(row):
 out=io.StringIO();writer=csv.writer(out);writer.writerow(["timestamp","kwh","output_kg","intensity_kwh_per_kg","segment_median","robust_score","anomaly"])
 for obs in row.snapshot["result"]["observations"]:writer.writerow([obs[k] for k in ["timestamp","kwh","output_kg","intensity","baseline","score","anomaly"]])
 return "\ufeff"+out.getvalue()
