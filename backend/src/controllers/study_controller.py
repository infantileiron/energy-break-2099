from ..services import study_service
from ..models.study import ChangeStudy
from ..models.common import serialize
from .common import listing,require
def list_all(db):return listing(db,ChangeStudy)
def detail(db,ident):return serialize(require(db,ChangeStudy,ident))
def create(db,body):return serialize(study_service.create(db,body))
