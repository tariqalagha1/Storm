from typing import List, Optional, Set
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from .database import get_db
from .models import User, UserRole, Permission, RolePermission, UserPermission
from .auth import get_current_user

# Default role permissions mapping
DEFAULT_ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.ADMIN_ALL,
        Permission.READ_USER, Permission.WRITE_USER, Permission.DELETE_USER,
        Permission.READ_PROJECT, Permission.WRITE_PROJECT, Permission.DELETE_PROJECT,
        Permission.READ_API_KEY, Permission.WRITE_API_KEY, Permission.DELETE_API_KEY,
        Permission.READ_SUBSCRIPTION, Permission.WRITE_SUBSCRIPTION,
        Permission.READ_USAGE, Permission.WRITE_USAGE,
        Permission.EXTERNAL_READ, Permission.EXTERNAL_WRITE, Permission.WEBHOOK_ACCESS,
        Permission.READ_SENSITIVE, Permission.WRITE_SENSITIVE
    ],
    UserRole.PREMIUM: [
        Permission.READ_USER, Permission.WRITE_USER,
        Permission.READ_PROJECT, Permission.WRITE_PROJECT, Permission.DELETE_PROJECT,
        Permission.READ_API_KEY, Permission.WRITE_API_KEY, Permission.DELETE_API_KEY,
        Permission.READ_SUBSCRIPTION,
        Permission.READ_USAGE, Permission.WRITE_USAGE,
        Permission.EXTERNAL_READ, Permission.EXTERNAL_WRITE,
        Permission.READ_SENSITIVE
    ],
    UserRole.USER: [
        Permission.READ_USER, Permission.WRITE_USER,
        Permission.READ_PROJECT, Permission.WRITE_PROJECT,
        Permission.READ_API_KEY, Permission.WRITE_API_KEY,
        Permission.READ_SUBSCRIPTION,
        Permission.READ_USAGE
    ],
    UserRole.API_INTEGRATION: [
        Permission.READ_USER,
        Permission.READ_PROJECT,
        Permission.READ_API_KEY,
        Permission.EXTERNAL_READ, Permission.EXTERNAL_WRITE,
        Permission.WEBHOOK_ACCESS
    ],
    UserRole.EXTERNAL_SERVICE: [
        Permission.EXTERNAL_READ, Permission.EXTERNAL_WRITE,
        Permission.WEBHOOK_ACCESS
    ]
}

class PermissionChecker:
    """Class to handle permission checking for users"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_permissions(self, user: User) -> Set[Permission]:
        """Get all permissions for a user (role-based + individual)"""
        permissions = set()
        
        # Get role-based permissions
        role_permissions = self.db.query(RolePermission).filter(
            RolePermission.role == user.role
        ).all()
        
        for rp in role_permissions:
            permissions.add(rp.permission)
        
        # Get individual user permissions (not expired)
        user_permissions = self.db.query(UserPermission).filter(
            UserPermission.user_id == user.id,
            (UserPermission.expires_at.is_(None) | 
             (UserPermission.expires_at > datetime.utcnow()))
        ).all()
        
        for up in user_permissions:
            permissions.add(up.permission)
        
        # If no permissions found in DB, use defaults
        if not permissions and user.role in DEFAULT_ROLE_PERMISSIONS:
            permissions = set(DEFAULT_ROLE_PERMISSIONS[user.role])
        
        return permissions
    
    def has_permission(self, user: User, permission: Permission) -> bool:
        """Check if user has a specific permission"""
        user_permissions = self.get_user_permissions(user)
        
        # Admin role has all permissions
        if Permission.ADMIN_ALL in user_permissions:
            return True
        
        return permission in user_permissions
    
    def has_any_permission(self, user: User, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions"""
        user_permissions = self.get_user_permissions(user)
        
        # Admin role has all permissions
        if Permission.ADMIN_ALL in user_permissions:
            return True
        
        return any(perm in user_permissions for perm in permissions)
    
    def has_all_permissions(self, user: User, permissions: List[Permission]) -> bool:
        """Check if user has all of the specified permissions"""
        user_permissions = self.get_user_permissions(user)
        
        # Admin role has all permissions
        if Permission.ADMIN_ALL in user_permissions:
            return True
        
        return all(perm in user_permissions for perm in permissions)

def get_permission_checker(db: Session = Depends(get_db)) -> PermissionChecker:
    """Dependency to get permission checker"""
    return PermissionChecker(db)

def require_permission(permission: Permission):
    """Decorator to require a specific permission"""
    def permission_dependency(
        current_user: User = Depends(get_current_user),
        permission_checker: PermissionChecker = Depends(get_permission_checker)
    ):
        if not permission_checker.has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission.value}' required"
            )
        return current_user
    
    return permission_dependency

def require_any_permission(permissions: List[Permission]):
    """Decorator to require any of the specified permissions"""
    def permission_dependency(
        current_user: User = Depends(get_current_user),
        permission_checker: PermissionChecker = Depends(get_permission_checker)
    ):
        if not permission_checker.has_any_permission(current_user, permissions):
            permission_names = [p.value for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these permissions required: {', '.join(permission_names)}"
            )
        return current_user
    
    return permission_dependency

def require_all_permissions(permissions: List[Permission]):
    """Decorator to require all of the specified permissions"""
    def permission_dependency(
        current_user: User = Depends(get_current_user),
        permission_checker: PermissionChecker = Depends(get_permission_checker)
    ):
        if not permission_checker.has_all_permissions(current_user, permissions):
            permission_names = [p.value for p in permissions]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"All of these permissions required: {', '.join(permission_names)}"
            )
        return current_user
    
    return permission_dependency

def require_external_access():
    """Decorator specifically for external API access"""
    return require_any_permission([
        Permission.EXTERNAL_READ,
        Permission.EXTERNAL_WRITE,
        Permission.ADMIN_ALL
    ])

def require_sensitive_data_access():
    """Decorator for accessing sensitive data"""
    return require_any_permission([
        Permission.READ_SENSITIVE,
        Permission.WRITE_SENSITIVE,
        Permission.ADMIN_ALL
    ])

def require_webhook_access():
    """Decorator for webhook operations"""
    return require_any_permission([
        Permission.WEBHOOK_ACCESS,
        Permission.ADMIN_ALL
    ])

async def initialize_default_permissions(db: Session):
    """Initialize default role permissions in the database"""
    for role, permissions in DEFAULT_ROLE_PERMISSIONS.items():
        for permission in permissions:
            # Check if permission already exists
            existing = db.query(RolePermission).filter(
                RolePermission.role == role,
                RolePermission.permission == permission
            ).first()
            
            if not existing:
                role_permission = RolePermission(
                    role=role,
                    permission=permission
                )
                db.add(role_permission)
    
    db.commit()