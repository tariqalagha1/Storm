from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from datetime import datetime

from .database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    PREMIUM = "premium"
    API_INTEGRATION = "api_integration"
    EXTERNAL_SERVICE = "external_service"

class Permission(str, enum.Enum):
    # User permissions
    READ_USER = "read_user"
    WRITE_USER = "write_user"
    DELETE_USER = "delete_user"
    
    # Project permissions
    READ_PROJECT = "read_project"
    WRITE_PROJECT = "write_project"
    DELETE_PROJECT = "delete_project"
    
    # API Key permissions
    READ_API_KEY = "read_api_key"
    WRITE_API_KEY = "write_api_key"
    DELETE_API_KEY = "delete_api_key"
    
    # Subscription permissions
    READ_SUBSCRIPTION = "read_subscription"
    WRITE_SUBSCRIPTION = "write_subscription"
    
    # Usage permissions
    READ_USAGE = "read_usage"
    WRITE_USAGE = "write_usage"
    
    # External integration permissions
    EXTERNAL_READ = "external_read"
    EXTERNAL_WRITE = "external_write"
    WEBHOOK_ACCESS = "webhook_access"
    
    # Sensitive data permissions
    READ_SENSITIVE = "read_sensitive"
    WRITE_SENSITIVE = "write_sensitive"
    
    # Admin permissions
    ADMIN_ALL = "admin_all"

class DataSensitivityLevel(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"

class SubscriptionPlan(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    projects = relationship("Project", back_populates="owner")
    api_keys = relationship("APIKey", back_populates="user")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    plan = Column(Enum(SubscriptionPlan), default=SubscriptionPlan.FREE)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="subscription")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    settings = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    api_keys = relationship("APIKey", back_populates="project")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    key_hash = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    rate_limit = Column(Integer, default=1000)  # requests per hour
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    project = relationship("Project", back_populates="api_keys")

class Usage(Base):
    __tablename__ = "usage"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time = Column(Numeric, nullable=True)  # in milliseconds
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    notification_type = Column(String, default="info")  # info, warning, error, success
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)

class RolePermission(Base):
    __tablename__ = "role_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(Enum(UserRole), nullable=False)
    permission = Column(Enum(Permission), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Unique constraint to prevent duplicate role-permission combinations
    __table_args__ = (UniqueConstraint('role', 'permission', name='unique_role_permission'),)

class UserPermission(Base):
    __tablename__ = "user_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission = Column(Enum(Permission), nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    granted_by_user = relationship("User", foreign_keys=[granted_by])

class ExternalIntegration(Base):
    __tablename__ = "external_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    integration_type = Column(String, nullable=False)  # finance, medical, etc.
    api_endpoint = Column(String, nullable=False)
    auth_method = Column(String, nullable=False)  # api_key, oauth2, jwt
    auth_config = Column(Text, nullable=True)  # JSON string for auth configuration
    webhook_url = Column(String, nullable=True)
    webhook_secret = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    data_mapping = Column(Text, nullable=True)  # JSON string for field mapping
    sensitivity_level = Column(Enum(DataSensitivityLevel), default=DataSensitivityLevel.INTERNAL)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")

class ExternalServiceKey(Base):
    __tablename__ = "external_service_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Display name for the key
    service_name = Column(String, nullable=False)  # e.g., "OpenAI", "Stripe", "SendGrid"
    key_type = Column(String, nullable=False)  # "api_key", "bearer_token", "oauth_token"
    encrypted_key = Column(Text, nullable=False)  # Encrypted API key
    description = Column(Text, nullable=True)
    usage_context = Column(String, nullable=True)  # "header", "query_param", "body"
    header_name = Column(String, nullable=True)  # e.g., "Authorization", "X-API-Key"
    query_param_name = Column(String, nullable=True)  # e.g., "api_key", "token"
    prefix = Column(String, nullable=True)  # e.g., "Bearer ", "sk-"
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    sensitivity_level = Column(Enum(DataSensitivityLevel), default=DataSensitivityLevel.CONFIDENTIAL)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    project = relationship("Project")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # CREATE, READ, UPDATE, DELETE
    resource_type = Column(String, nullable=False)  # user, project, api_key, etc.
    resource_id = Column(String, nullable=True)
    old_values = Column(Text, nullable=True)  # JSON string
    new_values = Column(Text, nullable=True)  # JSON string
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    integration_id = Column(Integer, ForeignKey("external_integrations.id"), nullable=True)
    sensitivity_level = Column(Enum(DataSensitivityLevel), default=DataSensitivityLevel.INTERNAL)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    api_key = relationship("APIKey")
    integration = relationship("ExternalIntegration")