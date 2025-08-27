from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import httpx
import asyncio
import logging

from ..database import get_db
from ..models import (
    User, Project, APIKey, Subscription, Usage, ExternalIntegration,
    AuditLog, UserRole, DataSensitivityLevel, ExternalServiceKey
)
from ..schemas import (
    ExternalIntegrationCreate, ExternalIntegrationUpdate, ExternalIntegrationResponse,
    UserCreateExternal, UserUpdateExternal, UserResponseExternal,
    ProjectCreateExternal, ProjectResponseExternal,
    ExternalAPIRequest, ExternalAPIResponse, ExternalAPIRequestWithKey,
    DataSyncRequest, DataSyncResponse,
    WebhookEventResponse, MessageResponse, PaginatedResponse
)
from ..permissions import (
    require_permission, require_external_access, require_sensitive_data_access
)
from ..middleware import get_current_user_from_middleware
from ..security import sanitize_for_api, SensitiveFieldHandler, DataEncryption
from ..webhooks import webhook_manager, WebhookEvent
from ..config import settings

logger = logging.getLogger(__name__)
encryption = DataEncryption()

router = APIRouter(prefix="/api/v1/external", tags=["External Integration"])

# External Integration Management
@router.post("/integrations", response_model=ExternalIntegrationResponse)
async def create_integration(
    integration: ExternalIntegrationCreate,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("external_integration:write"))
):
    """Create a new external integration"""
    # Check if integration name already exists for this user
    existing = db.query(ExternalIntegration).filter(
        ExternalIntegration.user_id == current_user.id,
        ExternalIntegration.name == integration.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration with this name already exists"
        )
    
    # Create new integration
    db_integration = ExternalIntegration(
        user_id=current_user.id,
        name=integration.name,
        integration_type=integration.integration_type,
        description=integration.description,
        webhook_url=integration.webhook_url,
        webhook_secret=integration.webhook_secret,
        api_key=integration.api_key,
        is_active=integration.is_active
    )
    
    db.add(db_integration)
    db.commit()
    db.refresh(db_integration)
    
    # Log audit trail
    audit_log = AuditLog(
        user_id=current_user.id,
        action="create",
        resource_type="external_integration",
        resource_id=db_integration.id,
        new_values={"name": integration.name, "type": integration.integration_type}
    )
    db.add(audit_log)
    db.commit()
    
    return db_integration

@router.get("/integrations", response_model=List[ExternalIntegrationResponse])
async def list_integrations(
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("external_integration:read"))
):
    """List user's external integrations"""
    integrations = db.query(ExternalIntegration).filter(
        ExternalIntegration.user_id == current_user.id
    ).all()
    
    return integrations

@router.get("/integrations/{integration_id}", response_model=ExternalIntegrationResponse)
async def get_integration(
    integration_id: int,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("external_integration:read"))
):
    """Get specific external integration"""
    integration = db.query(ExternalIntegration).filter(
        ExternalIntegration.id == integration_id,
        ExternalIntegration.user_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    return integration

@router.put("/integrations/{integration_id}", response_model=ExternalIntegrationResponse)
async def update_integration(
    integration_id: int,
    integration_update: ExternalIntegrationUpdate,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("external_integration:write"))
):
    """Update external integration"""
    integration = db.query(ExternalIntegration).filter(
        ExternalIntegration.id == integration_id,
        ExternalIntegration.user_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    # Store old values for audit
    old_values = {
        "name": integration.name,
        "description": integration.description,
        "webhook_url": integration.webhook_url,
        "is_active": integration.is_active
    }
    
    # Update fields
    update_data = integration_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(integration, field, value)
    
    integration.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(integration)
    
    # Log audit trail
    audit_log = AuditLog(
        user_id=current_user.id,
        action="update",
        resource_type="external_integration",
        resource_id=integration.id,
        old_values=old_values,
        new_values=update_data
    )
    db.add(audit_log)
    db.commit()
    
    return integration

@router.delete("/integrations/{integration_id}", response_model=MessageResponse)
async def delete_integration(
    integration_id: int,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("external_integration:delete"))
):
    """Delete external integration"""
    integration = db.query(ExternalIntegration).filter(
        ExternalIntegration.id == integration_id,
        ExternalIntegration.user_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    # Log audit trail before deletion
    audit_log = AuditLog(
        user_id=current_user.id,
        action="delete",
        resource_type="external_integration",
        resource_id=integration.id,
        old_values={"name": integration.name, "type": integration.integration_type}
    )
    db.add(audit_log)
    
    db.delete(integration)
    db.commit()
    
    return MessageResponse(message="Integration deleted successfully")

# External User Management
@router.post("/users", response_model=UserResponseExternal)
async def create_external_user(
    user_data: UserCreateExternal,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_external_access())
):
    """Create user via external API"""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Create new user
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        role=user_data.role,
        external_id=user_data.external_id,
        integration_source=user_data.integration_source,
        metadata=user_data.metadata,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Trigger webhook
    await webhook_manager.trigger_webhook(
        WebhookEvent.USER_CREATED,
        {
            'id': db_user.id,
            'email': db_user.email,
            'username': db_user.username,
            'external_id': db_user.external_id,
            'integration_source': db_user.integration_source
        },
        db_user.id,
        db
    )
    
    # Prepare response with user permissions and subscription info
    response_data = UserResponseExternal(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        full_name=db_user.full_name,
        role=db_user.role,
        is_active=db_user.is_active,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at,
        external_id=db_user.external_id,
        integration_source=db_user.integration_source,
        permissions=[],  # Would be populated from permission system
        subscription_plan=db_user.subscription.plan.value if db_user.subscription else None
    )
    
    return response_data

@router.get("/users/{user_id}", response_model=UserResponseExternal)
async def get_external_user(
    user_id: int,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_external_access())
):
    """Get user data for external API"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if current user has permission to access this user's data
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Sanitize data based on current user's integration type
    integration = db.query(ExternalIntegration).filter(
        ExternalIntegration.user_id == current_user.id,
        ExternalIntegration.is_active == True
    ).first()
    
    integration_type = integration.integration_type if integration else 'general'
    
    # Prepare sanitized response
    user_data = {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'full_name': user.full_name,
        'role': user.role.value,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat(),
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        'external_id': user.external_id,
        'integration_source': user.integration_source
    }
    
    sanitized_data = sanitize_for_api(user_data, integration_type)
    
    return UserResponseExternal(**sanitized_data)

@router.put("/users/{user_id}", response_model=UserResponseExternal)
async def update_external_user(
    user_id: int,
    user_update: UserUpdateExternal,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_external_access())
):
    """Update user via external API"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check permissions
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Store old values for audit
    old_values = {
        'email': user.email,
        'username': user.username,
        'full_name': user.full_name,
        'is_active': user.is_active
    }
    
    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    # Log audit trail
    audit_log = AuditLog(
        user_id=current_user.id,
        action="update",
        resource_type="user",
        resource_id=user.id,
        old_values=old_values,
        new_values=update_data
    )
    db.add(audit_log)
    db.commit()
    
    # Trigger webhook
    await webhook_manager.trigger_webhook(
        WebhookEvent.USER_UPDATED,
        {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'updated_fields': list(update_data.keys())
        },
        user.id,
        db
    )
    
    return UserResponseExternal(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        external_id=user.external_id,
        integration_source=user.integration_source
    )

# External Project Management
@router.post("/projects", response_model=ProjectResponseExternal)
async def create_external_project(
    project_data: ProjectCreateExternal,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_external_access())
):
    """Create project via external API"""
    # Check if project name already exists for this user
    existing = db.query(Project).filter(
        Project.owner_id == current_user.id,
        Project.name == project_data.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project with this name already exists"
        )
    
    # Create new project
    db_project = Project(
        name=project_data.name,
        description=project_data.description,
        owner_id=current_user.id,
        external_id=project_data.external_id,
        integration_source=project_data.integration_source,
        metadata=project_data.metadata
    )
    
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # Trigger webhook
    await webhook_manager.trigger_webhook(
        WebhookEvent.PROJECT_CREATED,
        {
            'id': db_project.id,
            'name': db_project.name,
            'owner_id': db_project.owner_id,
            'external_id': db_project.external_id
        },
        current_user.id,
        db
    )
    
    return ProjectResponseExternal(
        id=db_project.id,
        name=db_project.name,
        description=db_project.description,
        owner_id=db_project.owner_id,
        is_active=db_project.is_active,
        created_at=db_project.created_at,
        updated_at=db_project.updated_at,
        external_id=db_project.external_id,
        integration_source=db_project.integration_source,
        api_keys_count=len(db_project.api_keys)
    )

# Generic External API Proxy
@router.post("/api-call", response_model=ExternalAPIResponse)
async def make_external_api_call(
    api_request: ExternalAPIRequest,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_external_access())
):
    """Make authenticated API call to external service"""
    start_time = datetime.utcnow()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Storm-API/1.0',
                **api_request.headers
            }
            
            # Make the request
            response = await client.request(
                method=api_request.method,
                url=api_request.endpoint,
                headers=headers,
                params=api_request.query_params,
                json=api_request.body if api_request.body else None
            )
            
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {'raw_response': response.text}
            
            # Log the API call
            usage = Usage(
                user_id=current_user.id,
                endpoint=f"external:{api_request.endpoint}",
                method=api_request.method,
                status_code=response.status_code,
                response_time=response_time,
                timestamp=datetime.utcnow()
            )
            db.add(usage)
            db.commit()
            
            return ExternalAPIResponse(
                success=response.status_code < 400,
                status_code=response.status_code,
                data=response_data,
                response_time=response_time
            )
            
    except httpx.TimeoutException:
        return ExternalAPIResponse(
            success=False,
            status_code=408,
            error="Request timeout",
            response_time=(datetime.utcnow() - start_time).total_seconds()
        )
    except Exception as e:
        logger.error(f"External API call error: {e}")
        return ExternalAPIResponse(
            success=False,
            status_code=500,
            error=str(e),
            response_time=(datetime.utcnow() - start_time).total_seconds()
        )


# Enhanced External API Proxy with Stored Keys
@router.post("/api-call-with-key", response_model=ExternalAPIResponse)
async def make_external_api_call_with_key(
    api_request: ExternalAPIRequestWithKey,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_external_access())
):
    """Make authenticated API call to external service using stored service key"""
    start_time = datetime.utcnow()
    
    # Get the external service key
    service_key = db.query(ExternalServiceKey).filter(
        ExternalServiceKey.id == api_request.service_key_id,
        ExternalServiceKey.user_id == current_user.id,
        ExternalServiceKey.is_active == True
    ).first()
    
    if not service_key:
        return ExternalAPIResponse(
            success=False,
            status_code=404,
            error="External service key not found or inactive",
            response_time=(datetime.utcnow() - start_time).total_seconds()
        )
    
    # Check if key has expired
    if service_key.expires_at and service_key.expires_at < datetime.utcnow():
        return ExternalAPIResponse(
            success=False,
            status_code=401,
            error="External service key has expired",
            response_time=(datetime.utcnow() - start_time).total_seconds()
        )
    
    try:
        # Decrypt the API key
        decrypted_key = encryption.decrypt(service_key.encrypted_key)
        
        # Prepare headers, query params, and body based on key configuration
        headers, query_params, body = _prepare_request_with_key(
            service_key, decrypted_key, api_request
        )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Make the request
            response = await client.request(
                method=api_request.method,
                url=api_request.endpoint,
                headers=headers,
                params=query_params,
                json=body if body else None
            )
            
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {'raw_response': response.text}
            
            # Update service key usage
            service_key.usage_count += 1
            service_key.last_used = datetime.utcnow()
            
            # Log the API call
            usage = Usage(
                user_id=current_user.id,
                endpoint=f"external:{api_request.endpoint}",
                method=api_request.method,
                status_code=response.status_code,
                response_time=response_time,
                timestamp=datetime.utcnow()
            )
            db.add(usage)
            db.commit()
            
            return ExternalAPIResponse(
                success=response.status_code < 400,
                status_code=response.status_code,
                data=response_data,
                response_time=response_time
            )
            
    except Exception as e:
        logger.error(f"External API call with key error: {e}")
        return ExternalAPIResponse(
            success=False,
            status_code=500,
            error=str(e),
            response_time=(datetime.utcnow() - start_time).total_seconds()
        )


def _prepare_request_with_key(
    service_key: ExternalServiceKey, 
    decrypted_key: str, 
    api_request: ExternalAPIRequestWithKey
) -> tuple:
    """Prepare headers, query params, and body based on service key configuration"""
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Storm-API/1.0',
        **api_request.additional_headers
    }
    query_params = dict(api_request.query_params) if api_request.query_params else {}
    body = dict(api_request.body) if api_request.body else None
    
    # Apply the key based on usage context
    if service_key.usage_context == 'header':
        header_name = service_key.header_name or 'Authorization'
        if service_key.key_type == 'bearer_token':
            headers[header_name] = f"Bearer {decrypted_key}"
        elif service_key.key_type == 'api_key':
            prefix = service_key.prefix or ''
            headers[header_name] = f"{prefix}{decrypted_key}".strip()
        else:
            headers[header_name] = decrypted_key
            
    elif service_key.usage_context == 'query_param':
        param_name = service_key.query_param_name or 'api_key'
        query_params[param_name] = decrypted_key
        
    elif service_key.usage_context == 'body':
        if not body:
            body = {}
        body['api_key'] = decrypted_key
    
    return headers, query_params, body

# Data Synchronization
@router.post("/sync", response_model=DataSyncResponse)
async def sync_data(
    sync_request: DataSyncRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_external_access())
):
    """Synchronize data with external system"""
    import uuid
    
    sync_id = str(uuid.uuid4())
    
    # Create initial sync response
    sync_response = DataSyncResponse(
        sync_id=sync_id,
        entity_type=sync_request.entity_type,
        entity_id=sync_request.entity_id,
        status="pending",
        started_at=datetime.utcnow()
    )
    
    # Add background task for actual synchronization
    background_tasks.add_task(
        perform_data_sync,
        sync_request,
        sync_id,
        current_user.id,
        db
    )
    
    return sync_response

async def perform_data_sync(sync_request: DataSyncRequest, sync_id: str, user_id: int, db: Session):
    """Perform actual data synchronization in background"""
    try:
        # This is a placeholder for actual sync logic
        # In a real implementation, you would:
        # 1. Fetch data from external system
        # 2. Transform data according to field mappings
        # 3. Update local database
        # 4. Handle conflicts and errors
        
        await asyncio.sleep(2)  # Simulate processing time
        
        # Log completion (in real implementation, update sync status in database)
        logger.info(f"Data sync {sync_id} completed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Data sync {sync_id} failed: {e}")

# Webhook Management
@router.get("/webhooks/events", response_model=List[WebhookEventResponse])
async def list_webhook_events(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_external_access())
):
    """List recent webhook events for user's integrations"""
    # This would typically query a webhook events table
    # For now, return empty list as placeholder
    return []

@router.post("/webhooks/test", response_model=MessageResponse)
async def test_webhook(
    integration_id: int,
    current_user: User = Depends(get_current_user_from_middleware),
    db: Session = Depends(get_db),
    _: None = Depends(require_external_access())
):
    """Test webhook delivery for an integration"""
    integration = db.query(ExternalIntegration).filter(
        ExternalIntegration.id == integration_id,
        ExternalIntegration.user_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found"
        )
    
    if not integration.webhook_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No webhook URL configured for this integration"
        )
    
    # Send test webhook
    test_data = {
        'event': 'test',
        'integration_id': integration.id,
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'This is a test webhook from Storm API'
    }
    
    try:
        await webhook_manager.trigger_webhook(
            WebhookEvent.USER_UPDATED,  # Using existing event type for test
            test_data,
            current_user.id,
            db
        )
        
        return MessageResponse(message="Test webhook sent successfully")
        
    except Exception as e:
        logger.error(f"Test webhook failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook test failed: {str(e)}"
        )