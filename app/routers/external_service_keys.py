from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import httpx
import asyncio
import logging

from ..database import get_db
from ..models import ExternalServiceKey, User, Project, DataSensitivityLevel
from ..schemas import (
    ExternalServiceKeyCreate, ExternalServiceKeyUpdate, ExternalServiceKeyResponse,
    ExternalServiceKeyTestRequest, ExternalServiceKeyTestResponse, MessageResponse
)
from ..auth import get_current_user
from ..security import DataEncryption
from ..middleware import check_rate_limit

logger = logging.getLogger(__name__)
router = APIRouter()
encryption = DataEncryption()

@router.get("/", response_model=List[ExternalServiceKeyResponse])
async def get_external_service_keys(
    project_id: Optional[int] = None,
    service_name: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all external service keys for the current user"""
    query = db.query(ExternalServiceKey).filter(ExternalServiceKey.user_id == current_user.id)
    
    if project_id is not None:
        query = query.filter(ExternalServiceKey.project_id == project_id)
    if service_name:
        query = query.filter(ExternalServiceKey.service_name.ilike(f"%{service_name}%"))
    if is_active is not None:
        query = query.filter(ExternalServiceKey.is_active == is_active)
    
    keys = query.order_by(ExternalServiceKey.created_at.desc()).all()
    
    # Convert to response format with masked keys
    response_keys = []
    for key in keys:
        key_dict = {
            "id": key.id,
            "name": key.name,
            "service_name": key.service_name,
            "key_type": key.key_type,
            "description": key.description,
            "usage_context": key.usage_context,
            "header_name": key.header_name,
            "query_param_name": key.query_param_name,
            "prefix": key.prefix,
            "project_id": key.project_id,
            "expires_at": key.expires_at,
            "key_preview": _mask_api_key(encryption.decrypt(key.encrypted_key)),
            "is_active": key.is_active,
            "last_used": key.last_used,
            "usage_count": key.usage_count,
            "user_id": key.user_id,
            "sensitivity_level": key.sensitivity_level.value,
            "created_at": key.created_at,
            "updated_at": key.updated_at
        }
        response_keys.append(ExternalServiceKeyResponse(**key_dict))
    
    return response_keys

@router.post("/", response_model=ExternalServiceKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_external_service_key(
    key_data: ExternalServiceKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new external service API key"""
    # Check if project exists and belongs to user
    if key_data.project_id:
        project = db.query(Project).filter(
            Project.id == key_data.project_id,
            Project.owner_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
    
    # Check for duplicate key names within the same service for this user
    existing_key = db.query(ExternalServiceKey).filter(
        ExternalServiceKey.user_id == current_user.id,
        ExternalServiceKey.service_name == key_data.service_name,
        ExternalServiceKey.name == key_data.name
    ).first()
    
    if existing_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A key with name '{key_data.name}' already exists for service '{key_data.service_name}'"
        )
    
    # Encrypt the API key
    encrypted_key = encryption.encrypt(key_data.api_key)
    
    # Create the external service key
    db_key = ExternalServiceKey(
        name=key_data.name,
        service_name=key_data.service_name,
        key_type=key_data.key_type,
        encrypted_key=encrypted_key,
        description=key_data.description,
        usage_context=key_data.usage_context,
        header_name=key_data.header_name,
        query_param_name=key_data.query_param_name,
        prefix=key_data.prefix,
        user_id=current_user.id,
        project_id=key_data.project_id,
        expires_at=key_data.expires_at,
        sensitivity_level=DataSensitivityLevel.CONFIDENTIAL
    )
    
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    
    # Return response with masked key
    key_dict = {
        "id": db_key.id,
        "name": db_key.name,
        "service_name": db_key.service_name,
        "key_type": db_key.key_type,
        "description": db_key.description,
        "usage_context": db_key.usage_context,
        "header_name": db_key.header_name,
        "query_param_name": db_key.query_param_name,
        "prefix": db_key.prefix,
        "project_id": db_key.project_id,
        "expires_at": db_key.expires_at,
        "key_preview": _mask_api_key(key_data.api_key),
        "is_active": db_key.is_active,
        "last_used": db_key.last_used,
        "usage_count": db_key.usage_count,
        "user_id": db_key.user_id,
        "sensitivity_level": db_key.sensitivity_level.value,
        "created_at": db_key.created_at,
        "updated_at": db_key.updated_at
    }
    
    return ExternalServiceKeyResponse(**key_dict)

@router.get("/{key_id}", response_model=ExternalServiceKeyResponse)
async def get_external_service_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific external service key"""
    key = db.query(ExternalServiceKey).filter(
        ExternalServiceKey.id == key_id,
        ExternalServiceKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External service key not found"
        )
    
    # Return response with masked key
    key_dict = {
        "id": key.id,
        "name": key.name,
        "service_name": key.service_name,
        "key_type": key.key_type,
        "description": key.description,
        "usage_context": key.usage_context,
        "header_name": key.header_name,
        "query_param_name": key.query_param_name,
        "prefix": key.prefix,
        "project_id": key.project_id,
        "expires_at": key.expires_at,
        "key_preview": _mask_api_key(encryption.decrypt(key.encrypted_key)),
        "is_active": key.is_active,
        "last_used": key.last_used,
        "usage_count": key.usage_count,
        "user_id": key.user_id,
        "sensitivity_level": key.sensitivity_level.value,
        "created_at": key.created_at,
        "updated_at": key.updated_at
    }
    
    return ExternalServiceKeyResponse(**key_dict)

@router.put("/{key_id}", response_model=ExternalServiceKeyResponse)
async def update_external_service_key(
    key_id: int,
    key_data: ExternalServiceKeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an external service key"""
    key = db.query(ExternalServiceKey).filter(
        ExternalServiceKey.id == key_id,
        ExternalServiceKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External service key not found"
        )
    
    # Update fields
    update_data = key_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(key, field, value)
    
    key.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(key)
    
    # Return response with masked key
    key_dict = {
        "id": key.id,
        "name": key.name,
        "service_name": key.service_name,
        "key_type": key.key_type,
        "description": key.description,
        "usage_context": key.usage_context,
        "header_name": key.header_name,
        "query_param_name": key.query_param_name,
        "prefix": key.prefix,
        "project_id": key.project_id,
        "expires_at": key.expires_at,
        "key_preview": _mask_api_key(encryption.decrypt(key.encrypted_key)),
        "is_active": key.is_active,
        "last_used": key.last_used,
        "usage_count": key.usage_count,
        "user_id": key.user_id,
        "sensitivity_level": key.sensitivity_level.value,
        "created_at": key.created_at,
        "updated_at": key.updated_at
    }
    
    return ExternalServiceKeyResponse(**key_dict)

@router.delete("/{key_id}", response_model=MessageResponse)
async def delete_external_service_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an external service key"""
    key = db.query(ExternalServiceKey).filter(
        ExternalServiceKey.id == key_id,
        ExternalServiceKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External service key not found"
        )
    
    db.delete(key)
    db.commit()
    
    return MessageResponse(message="External service key deleted successfully")

@router.post("/{key_id}/test", response_model=ExternalServiceKeyTestResponse)
async def test_external_service_key(
    key_id: int,
    test_request: ExternalServiceKeyTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test an external service key by making a test API call"""
    key = db.query(ExternalServiceKey).filter(
        ExternalServiceKey.id == key_id,
        ExternalServiceKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External service key not found"
        )
    
    if not key.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot test inactive key"
        )
    
    # Check if key is expired
    if key.expires_at and key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot test expired key"
        )
    
    try:
        # Decrypt the API key
        decrypted_key = encryption.decrypt(key.encrypted_key)
        
        # Prepare headers
        headers = test_request.additional_headers.copy() if test_request.additional_headers else {}
        
        # Add authentication based on key configuration
        if key.usage_context == "header":
            auth_value = f"{key.prefix or ''}{decrypted_key}"
            headers[key.header_name or "Authorization"] = auth_value
        
        # Prepare query parameters
        params = {}
        if key.usage_context == "query_param":
            params[key.query_param_name or "api_key"] = decrypted_key
        
        # Prepare request body
        json_data = None
        if key.usage_context == "body" and test_request.test_payload:
            json_data = test_request.test_payload.copy()
            json_data["api_key"] = decrypted_key
        elif test_request.test_payload:
            json_data = test_request.test_payload
        
        # Make the test request
        start_time = datetime.utcnow()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=test_request.test_method,
                url=test_request.test_endpoint,
                headers=headers,
                params=params,
                json=json_data
            )
        
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds() * 1000
        
        # Update usage statistics
        key.last_used = datetime.utcnow()
        key.usage_count += 1
        db.commit()
        
        # Prepare response preview (first 200 chars)
        response_text = response.text
        response_preview = response_text[:200] + "..." if len(response_text) > 200 else response_text
        
        return ExternalServiceKeyTestResponse(
            success=response.status_code < 400,
            status_code=response.status_code,
            response_preview=response_preview,
            response_time_ms=response_time
        )
        
    except httpx.TimeoutException:
        return ExternalServiceKeyTestResponse(
            success=False,
            error_message="Request timed out after 30 seconds"
        )
    except httpx.RequestError as e:
        return ExternalServiceKeyTestResponse(
            success=False,
            error_message=f"Request failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error testing external service key {key_id}: {str(e)}")
        return ExternalServiceKeyTestResponse(
            success=False,
            error_message="An unexpected error occurred during testing"
        )

@router.post("/{key_id}/toggle", response_model=ExternalServiceKeyResponse)
async def toggle_external_service_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle the active status of an external service key"""
    key = db.query(ExternalServiceKey).filter(
        ExternalServiceKey.id == key_id,
        ExternalServiceKey.user_id == current_user.id
    ).first()
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="External service key not found"
        )
    
    key.is_active = not key.is_active
    key.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(key)
    
    # Return response with masked key
    key_dict = {
        "id": key.id,
        "name": key.name,
        "service_name": key.service_name,
        "key_type": key.key_type,
        "description": key.description,
        "usage_context": key.usage_context,
        "header_name": key.header_name,
        "query_param_name": key.query_param_name,
        "prefix": key.prefix,
        "project_id": key.project_id,
        "expires_at": key.expires_at,
        "key_preview": _mask_api_key(encryption.decrypt(key.encrypted_key)),
        "is_active": key.is_active,
        "last_used": key.last_used,
        "usage_count": key.usage_count,
        "user_id": key.user_id,
        "sensitivity_level": key.sensitivity_level.value,
        "created_at": key.created_at,
        "updated_at": key.updated_at
    }
    
    return ExternalServiceKeyResponse(**key_dict)

def _mask_api_key(api_key: str) -> str:
    """Mask an API key for display purposes"""
    if not api_key:
        return ""
    
    if len(api_key) <= 8:
        return "*" * len(api_key)
    
    # Show first 4 and last 4 characters
    return f"{api_key[:4]}{'*' * (len(api_key) - 8)}{api_key[-4:]}"

def get_external_service_key_for_request(db: Session, user_id: int, service_name: str, key_name: str = None) -> Optional[str]:
    """Helper function to get decrypted API key for making HTTP requests"""
    query = db.query(ExternalServiceKey).filter(
        ExternalServiceKey.user_id == user_id,
        ExternalServiceKey.service_name == service_name,
        ExternalServiceKey.is_active == True
    )
    
    if key_name:
        query = query.filter(ExternalServiceKey.name == key_name)
    
    # Check for expiration
    query = query.filter(
        (ExternalServiceKey.expires_at.is_(None)) | 
        (ExternalServiceKey.expires_at > datetime.utcnow())
    )
    
    key = query.first()
    
    if not key:
        return None
    
    # Update usage statistics
    key.last_used = datetime.utcnow()
    key.usage_count += 1
    db.commit()
    
    # Return decrypted key
    return encryption.decrypt(key.encrypted_key)

def prepare_request_with_external_key(db: Session, user_id: int, service_name: str, 
                                    headers: dict = None, params: dict = None, 
                                    body: dict = None, key_name: str = None) -> tuple:
    """Helper function to prepare HTTP request with external service key"""
    key_record = db.query(ExternalServiceKey).filter(
        ExternalServiceKey.user_id == user_id,
        ExternalServiceKey.service_name == service_name,
        ExternalServiceKey.is_active == True
    )
    
    if key_name:
        key_record = key_record.filter(ExternalServiceKey.name == key_name)
    
    # Check for expiration
    key_record = key_record.filter(
        (ExternalServiceKey.expires_at.is_(None)) | 
        (ExternalServiceKey.expires_at > datetime.utcnow())
    ).first()
    
    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active API key found for service '{service_name}'"
        )
    
    # Decrypt the API key
    decrypted_key = encryption.decrypt(key_record.encrypted_key)
    
    # Prepare request components
    final_headers = headers.copy() if headers else {}
    final_params = params.copy() if params else {}
    final_body = body.copy() if body else {}
    
    # Add authentication based on key configuration
    if key_record.usage_context == "header":
        auth_value = f"{key_record.prefix or ''}{decrypted_key}"
        final_headers[key_record.header_name or "Authorization"] = auth_value
    elif key_record.usage_context == "query_param":
        final_params[key_record.query_param_name or "api_key"] = decrypted_key
    elif key_record.usage_context == "body":
        final_body["api_key"] = decrypted_key
    
    # Update usage statistics
    key_record.last_used = datetime.utcnow()
    key_record.usage_count += 1
    db.commit()
    
    return final_headers, final_params, final_body