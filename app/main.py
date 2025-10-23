# app/main.py
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.database import engine, Base
from app.core.redis import RedisManager
from app.services.token_blacklist_service import token_blacklist_service
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
    # allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")

@app.on_event("startup")
async def startup_event():
    """應用啟動時的初始化"""
    # 延遲導入以避免循環引用
    from app.core.redis import RedisManager
    from app.services.token_blacklist_service import get_token_blacklist_service
    
    # 測試 Redis 連接
    try:
        redis_client = RedisManager.get_redis()
        redis_client.ping()
        print("✓ Redis connection successful")
    except Exception as e:
        print(f"⚠ Redis not available: {str(e)}")
        print("⚠ Using in-memory fallback for token blacklist")
    
    # 初始化 token 黑名單服務
    try:
        blacklist_service = get_token_blacklist_service()
        stats = blacklist_service.get_blacklist_stats()
        print(f"✓ Token blacklist service initialized: {stats.get('backend_type', 'Unknown')}")
    except Exception as e:
        print(f"✗ Failed to initialize token blacklist service: {str(e)}")

    # print(f"CORS Origins: {settings.BACKEND_CORS_ORIGINS}")
    # pass

@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時的清理"""
    from app.core.redis import RedisManager
    
    try:
        RedisManager.close()
        print("✓ Cleanup completed")
    except Exception as e:
        print(f"⚠ Cleanup error: {str(e)}")
        
    # pass


