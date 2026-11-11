from ..services import review_service
from ..models.review import IncidentReview
from ..models.common import serialize
from .common import listing,require
def list_all(db):return listing(db,IncidentReview)
def detail(db,ident):return serialize(require(db,IncidentReview,ident))
def create(db,body):return serialize(review_service.create(db,body))
