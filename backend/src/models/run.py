from datetime import datetime
from sqlalchemy import String,Text,JSON,Integer,DateTime,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from .common import RecordMixin
from ..config.database import Base
class ChangeRun(RecordMixin,Base):
 __tablename__="runs"
 study_id:Mapped[str]=mapped_column(ForeignKey("studies.id"))
 status:Mapped[str]=mapped_column(String(20),default="queued")
 result:Mapped[dict]=mapped_column(JSON,default=dict)
 error:Mapped[str]=mapped_column(Text,default="")
 # Delivery/claim bookkeeping. A queue delivery is only a notification: the
 # database row is the single source of truth for who may publish a result.
 attempts:Mapped[int]=mapped_column(Integer,default=0)
 claimed_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
 claimed_by:Mapped[str]=mapped_column(String(100),default="")
 claim_token:Mapped[str]=mapped_column(String(36),default="")
