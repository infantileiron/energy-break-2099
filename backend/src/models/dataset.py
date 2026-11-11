from sqlalchemy import String,Text,JSON,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from .common import RecordMixin
from ..config.database import Base
class MeterDataset(RecordMixin,Base):
 __tablename__="datasets"
 name:Mapped[str]=mapped_column(String(180),unique=True)
 readings:Mapped[list]=mapped_column(JSON)
 description:Mapped[str]=mapped_column(Text,default="")
