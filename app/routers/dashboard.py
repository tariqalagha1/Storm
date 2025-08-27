from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, desc
from typing import List, Dict, Any
from datetime import datetime, timedelta

from ..database import get_db
from ..models import User, Project, APIKey, Usage, Subscription
from ..schemas import (
    DashboardData, DashboardStats, UsageStats, ProjectResponse,
    APIKeyResponse, APIKeyCreate, APIKeyCreateResponse
)
from ..auth import get_current_user
import secrets
import hashlib

router = APIRouter()

@router.get("/stats", response_model=DashboardData)
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics and data"""
    # Get user's subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    # Get basic stats
    total_projects = db.query(func.count(Project.id)).filter(
        Project.owner_id == current_user.id,
        Project.is_active == True
    ).scalar() or 0
    
    active_api_keys = db.query(func.count(APIKey.id)).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).scalar() or 0
    
    # Get current month usage
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    usage_this_month = db.query(func.count(Usage.id)).filter(
        Usage.user_id == current_user.id,
        extract('month', Usage.timestamp) == current_month,
        extract('year', Usage.timestamp) == current_year
    ).scalar() or 0
    
    total_api_calls = db.query(func.count(Usage.id)).filter(
        Usage.user_id == current_user.id
    ).scalar() or 0
    
    # Get plan limits
    from .subscriptions import SUBSCRIPTION_PLANS
    plan_config = SUBSCRIPTION_PLANS.get(subscription.plan if subscription else "free", SUBSCRIPTION_PLANS["free"])
    plan_limit = plan_config['limits']['api_calls_per_month']
    
    # Create stats object
    stats = DashboardStats(
        total_projects=total_projects,
        total_api_calls=total_api_calls,
        active_api_keys=active_api_keys,
        current_plan=subscription.plan if subscription else "free",
        usage_this_month=usage_this_month,
        plan_limit=plan_limit
    )
    
    # Get recent usage (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_usage_data = db.query(
        func.date(Usage.timestamp).label('date'),
        func.count(Usage.id).label('requests'),
        func.sum(func.case([(Usage.status_code >= 400, 1)], else_=0)).label('errors'),
        func.avg(Usage.response_time).label('avg_response_time')
    ).filter(
        Usage.user_id == current_user.id,
        Usage.timestamp >= thirty_days_ago
    ).group_by(
        func.date(Usage.timestamp)
    ).order_by(
        func.date(Usage.timestamp)
    ).all()
    
    recent_usage = [
        UsageStats(
            date=str(row.date),
            requests=row.requests or 0,
            errors=row.errors or 0,
            avg_response_time=float(row.avg_response_time or 0)
        )
        for row in recent_usage_data
    ]
    
    # Get recent projects
    recent_projects_data = db.query(Project).filter(
        Project.owner_id == current_user.id,
        Project.is_active == True
    ).order_by(desc(Project.created_at)).limit(5).all()
    
    recent_projects = [ProjectResponse.from_orm(project) for project in recent_projects_data]
    
    return DashboardData(
        stats=stats,
        recent_usage=recent_usage,
        recent_projects=recent_projects
    )

@router.get("/projects", response_model=List[ProjectResponse])
async def get_user_projects(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's projects"""
    projects = db.query(Project).filter(
        Project.owner_id == current_user.id
    ).order_by(desc(Project.created_at)).offset(skip).limit(limit).all()
    
    return projects

@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project"""
    project = Project(
        name=project_data.get('name'),
        description=project_data.get('description'),
        owner_id=current_user.id
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return project

@router.get("/api-keys", response_model=List[APIKeyResponse])
async def get_user_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's API keys"""
    api_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id
    ).order_by(desc(APIKey.created_at)).all()
    
    # Convert to response format with key preview
    response_keys = []
    for key in api_keys:
        key_data = APIKeyResponse.from_orm(key)
        # Show only first 8 characters of the key
        key_data.key_preview = key.key_hash[:8] + "..."
        response_keys.append(key_data)
    
    return response_keys

@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new API key"""
    # Check if user has reached API key limit based on subscription
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    current_key_count = db.query(func.count(APIKey.id)).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).scalar() or 0
    
    # Set limits based on subscription plan
    max_keys = {
        "free": 1,
        "basic": 3,
        "premium": 10,
        "enterprise": 50
    }
    
    plan = subscription.plan if subscription else "free"
    if current_key_count >= max_keys.get(plan, 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum API keys reached for {plan} plan"
        )
    
    # Generate API key
    api_key = f"sk_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Create API key record
    db_api_key = APIKey(
        name=key_data.name,
        key_hash=key_hash,
        user_id=current_user.id,
        project_id=key_data.project_id
    )
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    # Return response with full API key (only shown once)
    response = APIKeyCreateResponse.from_orm(db_api_key)
    response.api_key = api_key
    response.key_preview = api_key[:8] + "..."
    
    return response

@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an API key"""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = False
    db.commit()
    
    return {"message": "API key deleted successfully"}

@router.get("/usage/analytics")
async def get_usage_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed usage analytics"""
    start_date = datetime.now() - timedelta(days=days)
    
    # Get usage by endpoint
    endpoint_usage = db.query(
        Usage.endpoint,
        func.count(Usage.id).label('count'),
        func.avg(Usage.response_time).label('avg_response_time')
    ).filter(
        Usage.user_id == current_user.id,
        Usage.timestamp >= start_date
    ).group_by(Usage.endpoint).all()
    
    # Get usage by status code
    status_usage = db.query(
        Usage.status_code,
        func.count(Usage.id).label('count')
    ).filter(
        Usage.user_id == current_user.id,
        Usage.timestamp >= start_date
    ).group_by(Usage.status_code).all()
    
    # Get hourly usage pattern
    hourly_usage = db.query(
        extract('hour', Usage.timestamp).label('hour'),
        func.count(Usage.id).label('count')
    ).filter(
        Usage.user_id == current_user.id,
        Usage.timestamp >= start_date
    ).group_by(extract('hour', Usage.timestamp)).all()
    
    return {
        "endpoint_usage": [
            {
                "endpoint": row.endpoint,
                "count": row.count,
                "avg_response_time": float(row.avg_response_time or 0)
            }
            for row in endpoint_usage
        ],
        "status_usage": [
            {
                "status_code": row.status_code,
                "count": row.count
            }
            for row in status_usage
        ],
        "hourly_usage": [
            {
                "hour": int(row.hour),
                "count": row.count
            }
            for row in hourly_usage
        ]
    }

@router.get("/export/usage")
async def export_usage_data(
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export usage data as CSV"""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD)"
        )
    
    usage_data = db.query(Usage).filter(
        Usage.user_id == current_user.id,
        Usage.timestamp >= start,
        Usage.timestamp <= end
    ).order_by(Usage.timestamp).all()
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Timestamp', 'Endpoint', 'Method', 'Status Code', 
        'Response Time (ms)', 'IP Address', 'User Agent'
    ])
    
    # Write data
    for usage in usage_data:
        writer.writerow([
            usage.timestamp.isoformat(),
            usage.endpoint,
            usage.method,
            usage.status_code,
            usage.response_time,
            usage.ip_address,
            usage.user_agent
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=usage_data.csv"}
    )