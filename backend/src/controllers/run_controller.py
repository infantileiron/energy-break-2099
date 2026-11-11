from ..services import run_service
from ..models.run import ChangeRun
from ..models.common import serialize
from .common import listing,require
def list_all(db):return listing(db,ChangeRun)
def detail(db,ident):return serialize(require(db,ChangeRun,ident))
def create(db,body):return serialize(run_service.create(db,body))
