from sqlalchemy import String,Text,JSON,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from .common import RecordMixin
from ..config.database import Base
class OperatingWindow(RecordMixin,Base):
 __tablename__="operating_windows"
 name:Mapped[str]=mapped_column(String(100),unique=True)
 start_at:Mapped[str]=mapped_column(String(40))
 end_at:Mapped[str]=mapped_column(String(40))
 note:Mapped[str]=mapped_column(Text,default="")
