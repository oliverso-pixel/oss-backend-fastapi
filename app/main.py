# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router as v1_router
from app.core.config import settings
# from app.core.database import engine
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

# app.add_middleware(logging_middleware.LoggingMiddleware)
# app.add_middleware(auth_middleware.AuthMiddleware)

# 掛載 v1 路由
app.include_router(v1_router, prefix=f"{settings.API_V1_STR}")

@app.on_event("startup")
async def startup_event():
    # 初始化資料庫連接、Redis 等
    pass

@app.on_event("shutdown")
async def shutdown_event():
    # 清理資源
    pass

# 根端點示例
@app.get("/")
def root():
    return {"message": "歡迎使用寵物社交平台 API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get(f"{settings.API_V1_STR}")
def root():
    return {"message": "歡迎使用寵物社交平台 API"}