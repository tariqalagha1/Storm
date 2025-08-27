from pydantic import BaseModel, EmailStr, Field, validator, root_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from .models import UserRole, SubscriptionStatus, SubscriptionPlan, Permission, DataSensitivityLevel

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    role: UserRole
    avatar_url: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Authentication Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Subscription Schemas
class SubscriptionBase(BaseModel):
    plan: SubscriptionPlan

class SubscriptionCreate(SubscriptionBase):
    pass

class SubscriptionUpdate(BaseModel):
    plan: Optional[SubscriptionPlan] = None
    status: Optional[SubscriptionStatus] = None

class SubscriptionResponse(SubscriptionBase):
    id: int
    user_id: int
    status: SubscriptionStatus
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Project Schemas
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# API Key Schemas
class APIKeyBase(BaseModel):
    name: str
    project_id: Optional[int] = None

class APIKeyCreate(APIKeyBase):
    pass

class APIKeyResponse(APIKeyBase):
    id: int
    key_preview: str  # Only show first 8 characters
    is_active: bool
    last_used: Optional[datetime] = None
    usage_count: int
    rate_limit: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class APIKeyCreateResponse(APIKeyResponse):
    api_key: str  # Full key only shown once during creation

# External Service Key Schemas
class ExternalServiceKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    service_name: str = Field(..., min_length=1, max_length=50)
    key_type: str = Field(..., pattern="^(api_key|bearer_token|oauth_token|basic_auth)$")
    description: Optional[str] = Field(None, max_length=500)
    usage_context: str = Field(..., pattern="^(header|query_param|body)$")
    header_name: Optional[str] = Field(None, max_length=50)
    query_param_name: Optional[str] = Field(None, max_length=50)
    prefix: Optional[str] = Field(None, max_length=20)
    project_id: Optional[int] = None
    expires_at: Optional[datetime] = None

class ExternalServiceKeyCreate(ExternalServiceKeyBase):
    api_key: str = Field(..., min_length=1)  # The actual API key to encrypt
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if len(v.strip()) < 8:
            raise ValueError('API key must be at least 8 characters long')
        return v.strip()

class ExternalServiceKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    usage_context: Optional[str] = Field(None, pattern="^(header|query_param|body)$")
    header_name: Optional[str] = Field(None, max_length=50)
    query_param_name: Optional[str] = Field(None, max_length=50)
    prefix: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None

class ExternalServiceKeyResponse(ExternalServiceKeyBase):
    id: int
    key_preview: str  # Masked version of the key
    is_active: bool
    last_used: Optional[datetime] = None
    usage_count: int
    user_id: int
    sensitivity_level: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ExternalServiceKeyTestRequest(BaseModel):
    key_id: int
    test_endpoint: str = Field(..., pattern="^https?://.*")
    test_method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH|DELETE)$")
    additional_headers: Optional[Dict[str, str]] = {}
    test_payload: Optional[Dict[str, Any]] = None

class ExternalServiceKeyTestResponse(BaseModel):
    success: bool
    status_code: Optional[int] = None
    response_preview: Optional[str] = None  # First 200 chars of response
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = None

# Dashboard Schemas
class DashboardStats(BaseModel):
    total_projects: int
    total_api_calls: int
    active_api_keys: int
    current_plan: SubscriptionPlan
    usage_this_month: int
    plan_limit: int

class UsageStats(BaseModel):
    date: str
    requests: int
    errors: int
    avg_response_time: float

class DashboardData(BaseModel):
    stats: DashboardStats
    recent_usage: List[UsageStats]
    recent_projects: List[ProjectResponse]

# Notification Schemas
class NotificationBase(BaseModel):
    title: str
    message: str
    notification_type: str = "info"

class NotificationCreate(NotificationBase):
    user_id: int

class NotificationResponse(NotificationBase):
    id: int
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Generic Response Schemas
class MessageResponse(BaseModel):
    message: str

class PaginatedResponse(BaseModel):
    items: List[BaseModel]
    total: int
    page: int
    size: int
    pages: int

# Error Schemas
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None

# External Integration Schemas
class ExternalIntegrationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    integration_type: str = Field(..., pattern="^(financial|medical|general)$")
    description: Optional[str] = Field(None, max_length=500)
    webhook_url: Optional[str] = Field(None, pattern="^https?://.*")
    is_active: bool = True
    
class ExternalIntegrationCreate(ExternalIntegrationBase):
    webhook_secret: Optional[str] = Field(None, min_length=16)
    api_key: Optional[str] = Field(None, min_length=32)
    
class ExternalIntegrationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    webhook_url: Optional[str] = Field(None, pattern="^https?://.*")
    is_active: Optional[bool] = None
    
class ExternalIntegrationResponse(ExternalIntegrationBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Permission Schemas
class PermissionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    
class PermissionResponse(PermissionBase):
    id: int
    
    class Config:
        from_attributes = True

class UserPermissionBase(BaseModel):
    user_id: int
    permission_id: int
    granted_by: Optional[int] = None
    
class UserPermissionResponse(UserPermissionBase):
    id: int
    granted_at: datetime
    permission: PermissionResponse
    
    class Config:
        from_attributes = True

# Enhanced API Schemas for External Integration
class APIFieldMapping(BaseModel):
    """Schema for mapping internal fields to external API fields"""
    internal_field: str
    external_field: str
    field_type: str = Field(..., pattern="^(string|integer|float|boolean|datetime|email|phone|ssn|medical_id)$")
    is_required: bool = True
    is_sensitive: bool = False
    sensitivity_level: Optional[str] = Field(None, pattern="^(public|internal|confidential|restricted)$")
    validation_pattern: Optional[str] = None
    
class APIEndpointConfig(BaseModel):
    """Configuration for external API endpoints"""
    endpoint_name: str = Field(..., min_length=1, max_length=100)
    method: str = Field(..., pattern="^(GET|POST|PUT|PATCH|DELETE)$")
    path: str = Field(..., min_length=1)
    requires_auth: bool = True
    required_permissions: List[str] = []
    field_mappings: List[APIFieldMapping] = []
    rate_limit: Optional[int] = Field(None, gt=0)
    
class ExternalAPIRequest(BaseModel):
    """Schema for external API requests"""
    endpoint: str
    method: str = "POST"
    headers: Optional[Dict[str, str]] = {}
    query_params: Optional[Dict[str, Any]] = {}
    body: Optional[Dict[str, Any]] = {}
    
    @validator('method')
    def validate_method(cls, v):
        allowed_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        if v.upper() not in allowed_methods:
            raise ValueError(f'Method must be one of: {", ".join(allowed_methods)}')
        return v.upper()

class ExternalAPIRequestWithKey(BaseModel):
    """Schema for external API requests using stored service keys"""
    endpoint: str
    method: str = "POST"
    service_key_id: int  # ID of the stored external service key to use
    additional_headers: Optional[Dict[str, str]] = {}
    query_params: Optional[Dict[str, Any]] = {}
    body: Optional[Dict[str, Any]] = {}
    
    @validator('method')
    def validate_method(cls, v):
        allowed_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        if v.upper() not in allowed_methods:
            raise ValueError(f'Method must be one of: {", ".join(allowed_methods)}')
        return v.upper()
        
class ExternalAPIResponse(BaseModel):
    """Generic schema for external API responses"""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    response_time: Optional[float] = None
    
# Webhook Schemas
class WebhookEventBase(BaseModel):
    event_type: str = Field(..., pattern="^(user|project|api_key|subscription|usage|notification)\.(created|updated|deleted)$")
    data: Dict[str, Any]
    user_id: Optional[int] = None
    integration_type: str = Field(default="general", pattern="^(financial|medical|general|public)$")
    
class WebhookEventResponse(WebhookEventBase):
    id: str
    timestamp: datetime
    
class WebhookDeliveryStatus(BaseModel):
    webhook_id: str
    endpoint_url: str
    status: str = Field(..., pattern="^(pending|delivered|failed|retrying)$")
    attempts: int = Field(default=0, ge=0)
    last_attempt: Optional[datetime] = None
    next_retry: Optional[datetime] = None
    error_message: Optional[str] = None
    
# Enhanced User Schemas with External Integration Support
class UserCreateExternal(BaseModel):
    """Schema for creating users via external API"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    role: UserRole = UserRole.USER
    external_id: Optional[str] = Field(None, max_length=100)  # ID from external system
    integration_source: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = {}  # Additional data from external system
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must contain only letters, numbers, hyphens, and underscores')
        return v
        
class UserUpdateExternal(BaseModel):
    """Schema for updating users via external API"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    
class UserResponseExternal(BaseModel):
    """Enhanced user response for external APIs"""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    external_id: Optional[str]
    integration_source: Optional[str]
    permissions: List[str] = []  # List of permission names
    subscription_plan: Optional[str] = None
    api_usage: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
        
# Enhanced Project Schemas
class ProjectCreateExternal(BaseModel):
    """Schema for creating projects via external API"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    external_id: Optional[str] = Field(None, max_length=100)
    integration_source: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = {}
    
class ProjectResponseExternal(BaseModel):
    """Enhanced project response for external APIs"""
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    external_id: Optional[str]
    integration_source: Optional[str]
    api_keys_count: int = 0
    usage_stats: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
        
# Data Synchronization Schemas
class DataSyncRequest(BaseModel):
    """Schema for data synchronization requests"""
    entity_type: str = Field(..., pattern="^(user|project|subscription|usage)$")
    entity_id: int
    sync_direction: str = Field(..., pattern="^(import|export|bidirectional)$")
    field_mappings: Optional[List[APIFieldMapping]] = []
    force_update: bool = False
    
class DataSyncResponse(BaseModel):
    """Schema for data synchronization responses"""
    sync_id: str
    entity_type: str
    entity_id: int
    status: str = Field(..., pattern="^(pending|in_progress|completed|failed)$")
    records_processed: int = 0
    records_updated: int = 0
    records_created: int = 0
    errors: List[str] = []
    started_at: datetime
    completed_at: Optional[datetime] = None
    
# Audit Log Schemas
class AuditLogResponse(BaseModel):
    """Schema for audit log entries"""
    id: int
    user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[int]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True