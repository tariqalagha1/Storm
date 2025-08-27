from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.database import get_db, engine
from app.models import Base
from app.routers import auth, users, subscriptions, dashboard, ai_analytics
# from app.routers import ai_analytics_v2  # Temporarily disabled due to TensorFlow dependency
from app.routers import external_integration, audit, external_service_keys
from app.config import settings
from app.middleware import APIAccessControlMiddleware

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Storm SaaS Platform",
    description="A modern SaaS application built with FastAPI",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Access Control middleware
app.add_middleware(APIAccessControlMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(ai_analytics.router, prefix="/api/ai", tags=["ai-analytics"])
# app.include_router(ai_analytics_v2.router, prefix="/api/ai/v2", tags=["ai-analytics-v2"])  # Temporarily disabled
app.include_router(external_integration.router, tags=["external-integration"])
app.include_router(external_service_keys.router, prefix="/api/external-service-keys", tags=["external-service-keys"])
app.include_router(audit.router, tags=["audit"])

# Serve static files
if os.path.exists("frontend/build"):
    app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse("frontend/build/index.html")
    
    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        return FileResponse("frontend/build/index.html")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Storm SaaS Platform is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False
    )