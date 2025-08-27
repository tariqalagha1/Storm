from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import asyncio
import pandas as pd
import io
from pydantic import BaseModel

from ..database import get_db
from ..models import User, Subscription
from ..auth import get_current_user
from ..ai_service_v2 import advanced_ai_service
from ..config import settings

router = APIRouter()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Pydantic models for request/response
class ModelTrainingRequest(BaseModel):
    name: str
    description: str
    model_type: str  # 'regression', 'classification', 'deep_learning'
    target_column: str
    hyperparameters: Optional[Dict[str, Any]] = {}

class CustomEndpointRequest(BaseModel):
    name: str
    description: str
    model_id: str
    pricing: Optional[Dict[str, float]] = {"per_request": 0.01}

class AlertThresholdRequest(BaseModel):
    error_rate: Optional[float] = 5.0
    response_time: Optional[float] = 2000.0
    request_rate: Optional[float] = 1000.0
    anomaly_score: Optional[float] = 0.8

# Real-time monitoring endpoints
@router.websocket("/ws/real-time-monitoring")
async def websocket_real_time_monitoring(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring data"""
    await manager.connect(websocket)
    try:
        while True:
            # Get real-time dashboard data
            dashboard_data = await advanced_ai_service.monitoring.get_real_time_dashboard_data()
            
            # Send data to client
            await manager.send_personal_message(
                json.dumps(dashboard_data),
                websocket
            )
            
            # Wait 5 seconds before next update
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await websocket.close(code=1000)
        manager.disconnect(websocket)

@router.post("/real-time-metrics")
async def submit_real_time_metrics(
    metrics: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Submit real-time metrics for processing"""
    
    if not settings.AI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analytics service is currently disabled"
        )
    
    try:
        # Add user context to metrics
        metrics['user_id'] = current_user.id
        metrics['timestamp'] = datetime.now().isoformat()
        
        # Process metrics
        result = await advanced_ai_service.monitoring.process_real_time_metrics(metrics)
        
        # Broadcast alerts to connected clients if any
        if result.get('alerts_triggered', 0) > 0:
            alert_message = {
                "type": "alert",
                "alerts": result['alerts'],
                "user_id": current_user.id
            }
            await manager.broadcast(json.dumps(alert_message))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process real-time metrics: {str(e)}"
        )

@router.get("/real-time-dashboard")
async def get_real_time_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get real-time dashboard data"""
    
    if not settings.AI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analytics service is currently disabled"
        )
    
    try:
        dashboard_data = await advanced_ai_service.monitoring.get_real_time_dashboard_data()
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard data: {str(e)}"
        )

@router.put("/alert-thresholds")
async def update_alert_thresholds(
    thresholds: AlertThresholdRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update alert thresholds for real-time monitoring"""
    
    try:
        # Update thresholds in monitoring service
        advanced_ai_service.monitoring.alert_thresholds.update(thresholds.dict(exclude_unset=True))
        
        return {
            "success": True,
            "message": "Alert thresholds updated successfully",
            "thresholds": advanced_ai_service.monitoring.alert_thresholds
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert thresholds: {str(e)}"
        )

# AI Marketplace endpoints
@router.get("/marketplace/models")
async def get_marketplace_models(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all available AI models in the marketplace"""
    
    try:
        models = await advanced_ai_service.marketplace.get_marketplace_models()
        
        return {
            "success": True,
            "models": models,
            "total_models": len(models)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get marketplace models: {str(e)}"
        )

@router.post("/marketplace/custom-endpoint")
async def create_custom_endpoint(
    endpoint_request: CustomEndpointRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a custom AI endpoint in the marketplace"""
    
    try:
        endpoint_config = {
            "name": endpoint_request.name,
            "description": endpoint_request.description,
            "model_id": endpoint_request.model_id,
            "pricing": endpoint_request.pricing
        }
        
        result = await advanced_ai_service.marketplace.create_custom_endpoint(
            user_id=current_user.id,
            endpoint_config=endpoint_config
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create custom endpoint: {str(e)}"
        )

@router.get("/marketplace/my-endpoints")
async def get_user_endpoints(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user's custom AI endpoints"""
    
    try:
        # Get user's endpoints from Redis
        endpoint_ids = await advanced_ai_service.marketplace.redis_client.smembers(f"user_endpoints:{current_user.id}")
        endpoints = []
        
        for endpoint_id in endpoint_ids:
            endpoint_info = await advanced_ai_service.marketplace.redis_client.hgetall(f"custom_endpoint:{endpoint_id}")
            if endpoint_info:
                endpoints.append(endpoint_info)
        
        return {
            "success": True,
            "endpoints": endpoints,
            "total_endpoints": len(endpoints)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user endpoints: {str(e)}"
        )

# Custom ML model training endpoints
@router.post("/train-custom-model")
async def train_custom_model(
    training_request: ModelTrainingRequest,
    training_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Train a custom ML model with user data"""
    
    if not settings.AI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analytics service is currently disabled"
        )
    
    try:
        # Read uploaded file
        contents = await training_file.read()
        
        # Parse CSV data
        if training_file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV files are supported for training data"
            )
        
        # Validate target column exists
        if training_request.target_column not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target column '{training_request.target_column}' not found in data"
            )
        
        # Prepare model config
        model_config = {
            "name": training_request.name,
            "description": training_request.description,
            "type": training_request.model_type,
            "target_column": training_request.target_column,
            "hyperparameters": training_request.hyperparameters
        }
        
        # Train model
        result = await advanced_ai_service.train_custom_model(
            user_id=current_user.id,
            model_config=model_config,
            training_data=df
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to train custom model: {str(e)}"
        )

@router.get("/my-models")
async def get_user_models(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user's trained models"""
    
    try:
        user_models = []
        
        for model_id, model_data in advanced_ai_service.custom_models.items():
            if model_data['info']['user_id'] == current_user.id:
                user_models.append(model_data['info'])
        
        return {
            "success": True,
            "models": user_models,
            "total_models": len(user_models)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user models: {str(e)}"
        )

# Advanced visualization endpoints
@router.get("/visualizations/usage-trends")
async def get_usage_trends_chart(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Generate interactive usage trends visualization"""
    
    try:
        # Get usage data
        usage_analysis = await advanced_ai_service.analyze_api_usage(
            db=db,
            user_id=current_user.id,
            days=days
        )
        
        # Create sample data for visualization (in real implementation, use actual usage data)
        import numpy as np
        dates = pd.date_range(start=datetime.now() - pd.Timedelta(days=days), end=datetime.now(), freq='H')
        sample_data = pd.DataFrame({
            'timestamp': dates,
            'request_count': np.random.poisson(50, len(dates)),
            'response_time': np.random.normal(200, 50, len(dates))
        })
        
        # Generate visualization
        chart_result = await advanced_ai_service.generate_advanced_visualizations(
            data=sample_data,
            chart_type="usage_trends"
        )
        
        return chart_result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate usage trends chart: {str(e)}"
        )

@router.get("/visualizations/performance-heatmap")
async def get_performance_heatmap(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Generate performance heatmap visualization"""
    
    try:
        # Create sample data for heatmap
        import numpy as np
        dates = pd.date_range(start=datetime.now() - pd.Timedelta(days=days), end=datetime.now(), freq='H')
        sample_data = pd.DataFrame({
            'timestamp': dates,
            'response_time': np.random.normal(200, 50, len(dates))
        })
        
        # Generate heatmap
        chart_result = await advanced_ai_service.generate_advanced_visualizations(
            data=sample_data,
            chart_type="performance_heatmap"
        )
        
        return chart_result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate performance heatmap: {str(e)}"
        )

# Intelligent automation endpoints
@router.get("/auto-scaling/recommendations")
async def get_auto_scaling_recommendations(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get intelligent auto-scaling recommendations"""
    
    try:
        # Get current system metrics (in real implementation, fetch from monitoring system)
        current_metrics = {
            "requests_per_second": 45,
            "avg_response_time": 250,
            "error_rate": 2.1,
            "cpu_usage": 65,
            "memory_usage": 70
        }
        
        recommendations = await advanced_ai_service.intelligent_auto_scaling(current_metrics)
        
        return recommendations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get auto-scaling recommendations: {str(e)}"
        )

@router.get("/predictive-maintenance")
async def get_predictive_maintenance(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get predictive maintenance analysis"""
    
    try:
        # Get system metrics trends (in real implementation, fetch from monitoring system)
        system_metrics = {
            "cpu_trend": [45, 48, 52, 55, 58, 62, 65],  # Last 7 measurements
            "memory_trend": [60, 62, 65, 68, 70, 72, 75],
            "disk_usage": 78,
            "network_latency": [10, 12, 11, 15, 18, 20, 22]
        }
        
        maintenance_analysis = await advanced_ai_service.predictive_maintenance(system_metrics)
        
        return maintenance_analysis
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get predictive maintenance analysis: {str(e)}"
        )

@router.get("/intelligent-pricing")
async def get_intelligent_pricing(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get AI-powered pricing recommendations"""
    
    try:
        # Get user's usage patterns
        usage_analysis = await advanced_ai_service.analyze_api_usage(
            db=db,
            user_id=current_user.id,
            days=30
        )
        
        # Get subscription info
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.id
        ).first()
        
        current_plan = subscription.plan.value if subscription else "free"
        total_requests = usage_analysis.get("total_requests", 0)
        avg_response_time = usage_analysis.get("avg_response_time", 0)
        error_rate = usage_analysis.get("error_rate", 0)
        
        # AI-powered pricing recommendations
        pricing_recommendations = []
        
        # Usage-based recommendations
        if total_requests > 10000 and current_plan == "free":
            pricing_recommendations.append({
                "type": "upgrade_suggestion",
                "current_plan": current_plan,
                "suggested_plan": "pro",
                "reason": "High usage volume detected",
                "potential_savings": "$50/month with bulk pricing",
                "confidence": 0.9
            })
        
        # Performance-based recommendations
        if avg_response_time < 100 and error_rate < 1:
            pricing_recommendations.append({
                "type": "premium_features",
                "suggestion": "Consider premium SLA tier",
                "reason": "Excellent performance metrics",
                "additional_cost": "$20/month",
                "benefits": ["99.99% uptime guarantee", "Priority support", "Advanced monitoring"]
            })
        
        # Cost optimization
        if total_requests < 1000 and current_plan != "free":
            pricing_recommendations.append({
                "type": "cost_optimization",
                "suggestion": "Consider downgrading to save costs",
                "reason": "Low usage detected",
                "potential_savings": "$30/month",
                "confidence": 0.8
            })
        
        return {
            "success": True,
            "current_plan": current_plan,
            "usage_summary": {
                "total_requests": total_requests,
                "avg_response_time": avg_response_time,
                "error_rate": error_rate
            },
            "pricing_recommendations": pricing_recommendations,
            "analysis_period": "30 days",
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate pricing recommendations: {str(e)}"
        )

# Health check for Phase 2 features
@router.get("/v2/health")
async def ai_service_v2_health() -> Dict[str, Any]:
    """Check Phase 2 AI service health and capabilities"""
    
    return {
        "ai_enabled": settings.AI_ENABLED,
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "phase_2_features": {
            "real_time_monitoring": "available",
            "ai_marketplace": "available",
            "custom_ml_training": "available",
            "advanced_visualizations": "available",
            "intelligent_automation": "available",
            "predictive_maintenance": "available",
            "intelligent_pricing": "available"
        },
        "services": {
            "anomaly_detection": "available",
            "usage_analysis": "available",
            "predictions": "available",
            "ai_insights": "available" if settings.OPENAI_API_KEY else "requires_openai_key",
            "deep_learning": "available",
            "real_time_alerts": "available",
            "custom_models": "available"
        },
        "status": "healthy" if settings.AI_ENABLED else "disabled",
        "version": "2.0",
        "active_connections": len(manager.active_connections)
    }