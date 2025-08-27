from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from ..database import get_db
from ..models import User, Subscription
from ..auth import get_current_user
from ..ai_service import ai_service
from ..config import settings

router = APIRouter()

@router.get("/usage-analysis")
async def analyze_usage_patterns(
    days: int = Query(default=7, ge=1, le=30, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Analyze API usage patterns and detect anomalies using AI"""
    
    if not settings.AI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analytics service is currently disabled"
        )
    
    try:
        # Perform AI-powered usage analysis
        analysis_result = await ai_service.analyze_api_usage(
            db=db,
            user_id=current_user.id,
            days=days
        )
        
        return {
            "success": True,
            "data": analysis_result,
            "analyzed_period": f"{days} days",
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze usage patterns: {str(e)}"
        )

@router.get("/ai-insights")
async def get_ai_insights(
    days: int = Query(default=7, ge=1, le=30, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get AI-generated insights about API usage and performance"""
    
    if not settings.AI_ENABLED or not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI insights service requires OpenAI API key configuration"
        )
    
    try:
        # Get usage analysis first
        usage_analysis = await ai_service.analyze_api_usage(
            db=db,
            user_id=current_user.id,
            days=days
        )
        
        # Get user context
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.id
        ).first()
        
        user_context = {
            "subscription_plan": subscription.plan.value if subscription else "free",
            "api_keys_count": len(current_user.api_keys) if current_user.api_keys else 0
        }
        
        # Generate AI insights
        ai_insights = await ai_service.generate_ai_insights(
            usage_data=usage_analysis,
            user_context=user_context
        )
        
        return {
            "success": True,
            "usage_summary": {
                "total_requests": usage_analysis.get("total_requests", 0),
                "error_rate": usage_analysis.get("error_rate", 0),
                "avg_response_time": usage_analysis.get("avg_response_time", 0),
                "anomalies_detected": len(usage_analysis.get("anomalies", []))
            },
            "ai_insights": ai_insights,
            "analyzed_period": f"{days} days",
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI insights: {str(e)}"
        )

@router.get("/anomalies")
async def get_anomalies(
    days: int = Query(default=7, ge=1, le=30, description="Number of days to analyze"),
    severity: Optional[str] = Query(default=None, pattern="^(low|medium|high)$", description="Filter by severity"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get detected anomalies in API usage patterns"""
    
    if not settings.AI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analytics service is currently disabled"
        )
    
    try:
        # Get usage analysis
        analysis_result = await ai_service.analyze_api_usage(
            db=db,
            user_id=current_user.id,
            days=days
        )
        
        anomalies = analysis_result.get("anomalies", [])
        
        # Filter by severity if specified
        if severity:
            anomalies = [a for a in anomalies if a.get("severity") == severity]
        
        # Group anomalies by type
        anomaly_types = {}
        for anomaly in anomalies:
            anomaly_type = anomaly.get("anomaly_type", "unknown")
            if anomaly_type not in anomaly_types:
                anomaly_types[anomaly_type] = []
            anomaly_types[anomaly_type].append(anomaly)
        
        return {
            "success": True,
            "total_anomalies": len(anomalies),
            "anomalies": anomalies,
            "anomalies_by_type": anomaly_types,
            "severity_filter": severity,
            "analyzed_period": f"{days} days",
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve anomalies: {str(e)}"
        )

@router.get("/usage-predictions")
async def get_usage_predictions(
    days_ahead: int = Query(default=7, ge=1, le=30, description="Number of days to predict"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get AI-powered predictions for future API usage"""
    
    if not settings.AI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analytics service is currently disabled"
        )
    
    try:
        # Generate usage predictions
        predictions = await ai_service.predict_usage_trends(
            db=db,
            user_id=current_user.id,
            days_ahead=days_ahead
        )
        
        return {
            "success": True,
            "predictions": predictions,
            "prediction_period": f"{days_ahead} days ahead",
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate usage predictions: {str(e)}"
        )

@router.get("/smart-recommendations")
async def get_smart_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get AI-powered recommendations for API optimization"""
    
    if not settings.AI_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analytics service is currently disabled"
        )
    
    try:
        # Get recent usage analysis
        usage_analysis = await ai_service.analyze_api_usage(
            db=db,
            user_id=current_user.id,
            days=7
        )
        
        # Get user subscription info
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.id
        ).first()
        
        recommendations = []
        
        # Generate recommendations based on analysis
        error_rate = usage_analysis.get("error_rate", 0)
        avg_response_time = usage_analysis.get("avg_response_time", 0)
        total_requests = usage_analysis.get("total_requests", 0)
        anomalies_count = len(usage_analysis.get("anomalies", []))
        
        # Error rate recommendations
        if error_rate > 5:
            recommendations.append({
                "type": "error_reduction",
                "priority": "high",
                "title": "High Error Rate Detected",
                "description": f"Your API has a {error_rate:.1f}% error rate. Consider implementing better error handling and monitoring.",
                "action": "Review error logs and implement retry mechanisms"
            })
        
        # Performance recommendations
        if avg_response_time > 1000:
            recommendations.append({
                "type": "performance",
                "priority": "medium",
                "title": "Slow Response Times",
                "description": f"Average response time is {avg_response_time:.0f}ms. Consider optimization.",
                "action": "Implement caching, database optimization, or CDN"
            })
        
        # Usage pattern recommendations
        if total_requests > 0 and anomalies_count > total_requests * 0.1:
            recommendations.append({
                "type": "monitoring",
                "priority": "medium",
                "title": "Unusual Usage Patterns",
                "description": f"Detected {anomalies_count} anomalies in recent usage. Monitor for potential issues.",
                "action": "Set up automated alerts for unusual patterns"
            })
        
        # Subscription recommendations
        if subscription and subscription.plan.value == "free" and total_requests > 100:
            recommendations.append({
                "type": "upgrade",
                "priority": "low",
                "title": "Consider Upgrading Plan",
                "description": "Your usage suggests you might benefit from a paid plan with higher limits.",
                "action": "Review available plans and upgrade if needed"
            })
        
        # Default recommendation if no issues found
        if not recommendations:
            recommendations.append({
                "type": "optimization",
                "priority": "low",
                "title": "API Performance Looks Good",
                "description": "Your API is performing well. Consider implementing advanced monitoring for continued optimization.",
                "action": "Set up detailed analytics and monitoring dashboards"
            })
        
        return {
            "success": True,
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
            "based_on_period": "7 days",
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )

@router.get("/health")
async def ai_service_health() -> Dict[str, Any]:
    """Check AI service health and configuration"""
    
    return {
        "ai_enabled": settings.AI_ENABLED,
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "services": {
            "anomaly_detection": "available",
            "usage_analysis": "available",
            "predictions": "available",
            "ai_insights": "available" if settings.OPENAI_API_KEY else "requires_openai_key"
        },
        "status": "healthy" if settings.AI_ENABLED else "disabled"
    }