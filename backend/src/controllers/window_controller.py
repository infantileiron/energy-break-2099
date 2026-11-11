from ..services import window_service
from ..models.window import OperatingWindow
from ..models.common import serialize
from .common import listing,require
def list_all(db):return listing(db,OperatingWindow)
def detail(db,ident):return serialize(require(db,OperatingWindow,ident))
def create(db,body):return serialize(window_service.create(db,body))
