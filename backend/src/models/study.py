from sqlalchemy import String,Text,JSON,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from .common import RecordMixin
from ..config.database import Base
class ChangeStudy(RecordMixin,Base):
 __tablename__="studies"
 name:Mapped[str]=mapped_column(String(180),unique=True)
 dataset_id:Mapped[str]=mapped_column(ForeignKey("datasets.id"))
 window_id:Mapped[str]=mapped_column(ForeignKey("operating_windows.id"))
 config:Mapped[dict]=mapped_column(JSON)
