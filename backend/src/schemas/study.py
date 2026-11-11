from pydantic import BaseModel,Field
class StudyCreate(BaseModel):
 name:str=Field(min_length=2,max_length=180)
 dataset_id:str
 window_id:str
 penalty:float=Field(default=6.,ge=.01,le=100000,allow_inf_nan=False)
 min_segment:int=Field(default=24,ge=3,le=240)
 anomaly_threshold:float=Field(default=3.5,ge=1,le=20,allow_inf_nan=False)
 noise_floor:float=Field(default=.02,ge=.001,le=1,allow_inf_nan=False)
