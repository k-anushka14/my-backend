import asyncio
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from config import settings
from cache import cache
from model import fake_news_detector
from factcheck import fact_check_service

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# Pydantic models
class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Text to analyze for fake news")
    
    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('Text cannot be empty or whitespace only')
        return v.strip()

class TextAnalysisResponse(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Credibility score (0-100, lower is better)")
    label: str = Field(..., description="Classification: reliable/suspicious/fake")
    reason: str = Field(..., description="Reason for classification")
    model_confidence: Optional[float] = Field(None, ge=0, le=1, description="Model confidence score")
    patterns_detected: int = Field(..., ge=0, description="Number of suspicious patterns detected")
    text_length: int = Field(..., ge=0, description="Length of analyzed text")
    fallback_mode: Optional[bool] = Field(False, description="Whether fallback analysis was used")

class FactCheckRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Query to fact-check")
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()

class ClaimInfo(BaseModel):
    text: str = Field(..., description="Claim text")
    rating: str = Field(..., description="Fact-check rating")
    url: str = Field(..., description="Source URL")
    claimant: Optional[str] = Field(None, description="Who made the claim")
    claimDate: Optional[str] = Field(None, description="When the claim was made")
    reviewDate: Optional[str] = Field(None, description="When it was reviewed")
    reviewer: Optional[str] = Field(None, description="Who reviewed the claim")
    source: str = Field(..., description="Source of the fact-check")

class FactCheckResponse(BaseModel):
    claims: list[ClaimInfo] = Field(..., description="List of fact-checked claims")
    source: str = Field(..., description="Source of fact-checking data")
    total_results: int = Field(..., description="Total number of results found")
    message: Optional[str] = Field(None, description="Additional information")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    services: Dict[str, Any] = Field(..., description="Service health information")

# API key dependency
async def verify_api_key(request: Request):
    """Verify API key from request headers."""
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    return api_key

# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    print("🚀 Starting Fake News Detection Backend...")
    
    # Initialize Redis connection
    await cache.connect()
    
    # Preload the AI model
    print("🔄 Preloading AI model...")
    await fake_news_detector.load_model()
    
    print("✅ Backend started successfully!")
    
    yield
    
    # Shutdown
    print("🔄 Shutting down...")
    
    # Close Redis connection
    await cache.disconnect()
    
    # Close fact-check service
    await fact_check_service.close()
    
    print("✅ Backend shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Fake News Detection API",
    description="AI-powered fake news detection backend for Chrome extension",
    version="1.0.0",
    docs_url="/docs" if settings.API_KEY != "default_api_key" else None,
    redoc_url="/redoc" if settings.API_KEY != "default_api_key" else None,
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure based on your deployment
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unexpected errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.API_KEY == "default_api_key" else "An unexpected error occurred",
            "timestamp": time.time()
        }
    )

# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint to verify service status."""
    try:
        # Check Redis connection
        redis_status = "healthy" if cache.redis_client else "unavailable"
        
        # Check model status
        model_info = fake_news_detector.get_model_info()
        model_status = "healthy" if model_info["model_loaded"] else "unavailable"
        
        # Check fact-check services
        fact_check_status = await fact_check_service.get_service_status()
        
        return HealthResponse(
            status="healthy",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            services={
                "redis": redis_status,
                "ai_model": model_status,
                "fact_check": fact_check_status,
                "model_info": model_info
            }
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            services={
                "error": str(e),
                "redis": "unknown",
                "ai_model": "unknown",
                "fact_check": "unknown"
            }
        )

# Text analysis endpoint
@app.post(
    "/analyze",
    response_model=TextAnalysisResponse,
    tags=["Analysis"],
    dependencies=[Depends(verify_api_key)]
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def analyze_text(
    request: Request,
    analysis_request: TextAnalysisRequest
):
    """
    Analyze text for fake news detection.
    
    Returns a credibility score and classification with reasoning.
    """
    try:
        # Perform analysis
        result = await fake_news_detector.analyze_text(analysis_request.text)
        
        # Check for errors
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return TextAnalysisResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Text analysis failed"
        )

# Fact-check endpoint
@app.get(
    "/fact-check",
    response_model=FactCheckResponse,
    tags=["Fact-Checking"],
    dependencies=[Depends(verify_api_key)]
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def fact_check(
    request: Request,
    query: str = Field(..., description="Query to fact-check")
):
    """
    Perform fact-checking on a query.
    
    Uses Google Fact Check Tools API with Politifact fallback.
    """
    try:
        # Validate query
        if not query or not query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query parameter is required and cannot be empty"
            )
        
        # Perform fact-checking
        result = await fact_check_service.fact_check(query.strip())
        
        # Check for errors
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
        
        return FactCheckResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Fact-check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fact-checking failed"
        )

# Model info endpoint
@app.get("/model/info", tags=["System"], dependencies=[Depends(verify_api_key)])
async def get_model_info():
    """Get information about the loaded AI model."""
    return fake_news_detector.get_model_info()

# Cache status endpoint
@app.get("/cache/status", tags=["System"], dependencies=[Depends(verify_api_key)])
async def get_cache_status():
    """Get Redis cache status and statistics."""
    if not cache.redis_client:
        return {"status": "unavailable", "message": "Redis not connected"}
    
    try:
        # Get basic cache info
        info = await cache.redis_client.info()
        
        # Get cache statistics
        keys_count = await cache.redis_client.dbsize()
        
        return {
            "status": "healthy",
            "redis_info": {
                "version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "total_keys": keys_count
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Fake News Detection API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "analyze": "/analyze",
            "fact_check": "/fact-check",
            "health": "/health",
            "docs": "/docs" if settings.API_KEY != "default_api_key" else "disabled"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
