import math
import numpy as np

def detect(values,penalty=6.,min_segment=24):
 x=np.asarray(values,dtype=float);n=len(x)
 if n<min_segment or min_segment<3 or not np.isfinite(x).all() or not math.isfinite(penalty) or penalty<=0:raise ValueError("分段参数或观测数量无效")
 # Center first to reduce cancellation in the prefix-sum SSE calculation.
 y=x-float(x.mean())
 if not np.isfinite(y).all() or float(np.max(np.abs(y)))>1e140:raise ValueError("观测量级过大，无法可靠计算平方误差")
 s=np.concatenate(([0.],np.cumsum(y)));ss=np.concatenate(([0.],np.cumsum(y*y)))
 dp=np.full(n+1,np.inf);back=np.full(n+1,-1,dtype=int);dp[0]=-penalty
 for end in range(min_segment,n+1):
  starts=np.arange(0,end-min_segment+1)
  candidates=(starts==0)|(starts>=min_segment);starts=starts[candidates]
  cost=np.maximum(0.,ss[end]-ss[starts]-(s[end]-s[starts])**2/(end-starts))
  objective=dp[starts]+cost+penalty
  j=int(np.argmin(objective));dp[end]=objective[j];back[end]=starts[j]
 if back[n]<0:raise ValueError("无法满足最小段长")
 bounds=[n];end=n
 while end>0:end=int(back[end]);bounds.append(end)
 bounds=sorted(bounds);segments=[]
 for a,b in zip(bounds,bounds[1:]):
  segment=x[a:b];segments.append({"start_index":a,"end_index":b,"count":b-a,"mean":float(segment.mean()),"sse":float(((segment-segment.mean())**2).sum())})
 return {"change_indices":bounds[1:-1],"segments":segments,"objective":float(dp[n]),"penalty":penalty,"min_segment":min_segment,"total_sse":sum(s["sse"] for s in segments),"criterion":"sum(within-segment SSE) + penalty × number of change points"}
