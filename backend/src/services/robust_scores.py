import math
import numpy as np

def score(values,segments,threshold=3.5,noise_floor=.02):
 if not math.isfinite(noise_floor) or noise_floor<=0:raise ValueError("噪声下限必须正且有限")
 x=np.asarray(values,dtype=float);scores=np.zeros(len(x));baselines=np.zeros(len(x));details=[]
 for segment in segments:
  a,b=segment["start_index"],segment["end_index"];residual=x[a:b]-segment["mean"]
  median_res=float(np.median(residual));mad=float(np.median(np.abs(residual-median_res)))
  scale=max(1.4826*mad,noise_floor);scores[a:b]=np.abs(residual-median_res)/scale;baselines[a:b]=segment["mean"]+median_res
  details.append({"start_index":a,"end_index":b,"median":float(baselines[a]),"mad":mad,"scale_used":scale,"floor_used":1.4826*mad<noise_floor})
 return {"scores":scores.tolist(),"baselines":baselines.tolist(),"anomaly_indices":[int(i) for i in np.where(scores>threshold)[0]],"threshold":threshold,"noise_floor":noise_floor,"segments":details,"formula":"abs(residual - segment median residual) / max(1.4826 × MAD, noise_floor)"}
