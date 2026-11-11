import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
class ErrorMiddleware(BaseHTTPMiddleware):
 async def dispatch(self,request,call_next):
  try:return await call_next(request)
  except Exception:
   logging.exception("Request failed")
   return JSONResponse({"detail":"服务暂时无法完成请求，请重试"},status_code=500)
