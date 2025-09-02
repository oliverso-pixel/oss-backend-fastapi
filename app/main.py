# app/main.py
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.database import engine, Base
from fastapi.middleware.cors import CORSMiddleware
import json
# from app.middleware import auth_middleware, logging_middleware

app = FastAPI(
    title="寵物社交平台 API", 
    version=settings.PROJECT_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自定義異常處理器
# @app.exception_handler(StarletteHTTPException)
# async def http_exception_handler(request: Request, exc: StarletteHTTPException):
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={"detail": exc.detail},
#         headers=getattr(exc, "headers", None)
#     )

# @app.exception_handler(RequestValidationError)
# async def validation_exception_handler(request: Request, exc: RequestValidationError):
#     return JSONResponse(
#         status_code=422,
#         content={"detail": exc.errors()}
#     )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """處理請求驗證錯誤"""
    errors = []
    for error in exc.errors():
        # 處理錯誤訊息，確保可以序列化
        error_detail = {
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        }
        
        # 如果有輸入值，添加它（但要確保它可以被序列化）
        if "input" in error:
            try:
                json.dumps(error["input"])  # 測試是否可序列化
                error_detail["input"] = error["input"]
            except:
                error_detail["input"] = str(error["input"])
        
        errors.append(error_detail)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """處理 HTTP 異常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# 全局異常處理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 記錄錯誤
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # 返回通用錯誤響應
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# app.add_middleware(logging_middleware.LoggingMiddleware)
# app.add_middleware(auth_middleware.AuthMiddleware)

# 掛載 v1 路由
app.include_router(v1_router, prefix=f"{settings.API_V1_STR}")

# 根端點示例
@app.get("/")
def root():
    return {"message": "Pet Social API", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get(f"{settings.API_V1_STR}")
def root():
    return {"message": "歡迎使用寵物社交平台 API"}

@app.on_event("startup")
async def startup_event():
    # 初始化資料庫連接、Redis 等
    pass

@app.on_event("shutdown")
async def shutdown_event():
    # 清理資源
    pass

