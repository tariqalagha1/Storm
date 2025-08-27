import time
import json
import hashlib
from typing import Dict, Optional, Callable, Any, Union, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import redis
import logging

from .database import get_db
from .models import User, APIKey, Usage, Permission, UserPermission, RolePermission
from .permissions import PermissionChecker
from .config import settings

logger = logging.getLogger(__name__)

# Redis client for rate limiting (fallback to in-memory if Redis not available)
try:
    redis_client = redis.Redis(
        host=getattr(settings, 'REDIS_HOST', 'localhost'),
        port=getattr(settings, 'REDIS_PORT', 6379),
        db=getattr(settings, 'REDIS_DB', 0),
        decode_responses=True
    )
    redis_client.ping()  # Test connection
    USE_REDIS = True
except:
    USE_REDIS = False
    # Fallback to in-memory storage
    rate_limit_storage = defaultdict(list)
    logger.warning("Redis not available, using in-memory rate limiting")

class RateLimiter:
    """Rate limiting implementation with Redis or in-memory fallback"""
    
    def __init__(self):
        self.use_redis = USE_REDIS
    
    def is_rate_limited(self, key: str, limit: int, window: int = 3600) -> tuple[bool, Dict[str, Any]]:
        """Check if request is rate limited
        
        Args:
            key: Unique identifier for rate limiting (e.g., user_id, api_key)
            limit: Maximum requests allowed in window
            window: Time window in seconds (default: 1 hour)
            
        Returns:
            Tuple of (is_limited, rate_limit_info)
        """
        current_time = int(time.time())
        window_start = current_time - window
        
        if self.use_redis:
            return self._redis_rate_limit(key, limit, window, current_time, window_start)
        else:
            return self._memory_rate_limit(key, limit, window, current_time, window_start)
    
    def _redis_rate_limit(self, key: str, limit: int, window: int, current_time: int, window_start: int) -> tuple[bool, Dict[str, Any]]:
        """Redis-based rate limiting"""
        try:
            pipe = redis_client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, window)
            
            results = pipe.execute()
            current_requests = results[1]
            
            rate_limit_info = {
                'limit': limit,
                'remaining': max(0, limit - current_requests - 1),
                'reset_time': current_time + window,
                'window': window
            }
            
            return current_requests >= limit, rate_limit_info
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            # Fallback to allowing request if Redis fails
            return False, {'limit': limit, 'remaining': limit, 'reset_time': current_time + window, 'window': window}
    
    def _memory_rate_limit(self, key: str, limit: int, window: int, current_time: int, window_start: int) -> tuple[bool, Dict[str, Any]]:
        """In-memory rate limiting fallback"""
        if key not in rate_limit_storage:
            rate_limit_storage[key] = []
        
        # Remove old entries
        rate_limit_storage[key] = [t for t in rate_limit_storage[key] if t > window_start]
        
        # Add current request
        rate_limit_storage[key].append(current_time)
        
        current_requests = len(rate_limit_storage[key])
        
        rate_limit_info = {
            'limit': limit,
            'remaining': max(0, limit - current_requests),
            'reset_time': current_time + window,
            'window': window
        }
        
        return current_requests > limit, rate_limit_info

class APIKeyAuth(HTTPBearer):
    """Custom API Key authentication"""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        # Check for API key in header
        api_key = request.headers.get('X-API-Key')
        if api_key:
            return HTTPAuthorizationCredentials(scheme='ApiKey', credentials=api_key)
        
        # Fallback to Bearer token
        return await super().__call__(request)

class APIAccessControlMiddleware:
    """Middleware for API access control, rate limiting, and usage tracking"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.permission_checker = PermissionChecker()
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Skip middleware for certain paths
        if self._should_skip_middleware(request.url.path):
            return await call_next(request)
        
        try:
            # Get database session
            db = next(get_db())
            
            # Authenticate and authorize
            auth_result = await self._authenticate_request(request, db)
            if isinstance(auth_result, Response):
                return auth_result
            
            user, api_key = auth_result
            
            # Check rate limits
            rate_limit_result = await self._check_rate_limits(request, user, api_key, db)
            if isinstance(rate_limit_result, Response):
                return rate_limit_result
            
            rate_limit_info = rate_limit_result
            
            # Check permissions
            permission_result = await self._check_permissions(request, user, db)
            if isinstance(permission_result, Response):
                return permission_result
            
            # Add user and API key to request state
            request.state.user = user
            request.state.api_key = api_key
            request.state.rate_limit_info = rate_limit_info
            
            # Process request
            response = await call_next(request)
            
            # Log usage
            await self._log_usage(request, response, user, api_key, start_time, db)
            
            # Add rate limit headers
            self._add_rate_limit_headers(response, rate_limit_info)
            
            return response
            
        except Exception as e:
            logger.error(f"API middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={'error': 'Internal server error', 'detail': str(e)}
            )
        finally:
            db.close()
    
    def _should_skip_middleware(self, path: str) -> bool:
        """Determine if middleware should be skipped for this path"""
        skip_paths = [
            '/docs', '/redoc', '/openapi.json',
            '/health', '/metrics',
            '/auth/login', '/auth/register',
            '/webhook'  # Webhooks have their own authentication
        ]
        
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    async def _authenticate_request(self, request: Request, db: Session) -> Union[Tuple[User, Optional[APIKey]], Response]:
        """Authenticate the request using JWT token or API key"""
        # Try API key authentication first
        api_key_header = request.headers.get('X-API-Key')
        if api_key_header:
            api_key = db.query(APIKey).filter(
                APIKey.key_hash == hashlib.sha256(api_key_header.encode()).hexdigest(),
                APIKey.is_active == True
            ).first()
            
            if not api_key:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={'error': 'Invalid API key'}
                )
            
            # Check API key expiration
            if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={'error': 'API key expired'}
                )
            
            user = api_key.user
            if not user.is_active:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={'error': 'User account is inactive'}
                )
            
            return user, api_key
        
        # Try JWT token authentication
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            # Here you would validate the JWT token
            # For now, we'll assume you have a function to decode and validate JWT
            try:
                from .auth import decode_access_token  # Assuming this function exists
                payload = decode_access_token(token)
                user_id = payload.get('sub')
                
                user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
                if not user:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={'error': 'Invalid token or user not found'}
                    )
                
                return user, None
                
            except Exception as e:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={'error': 'Invalid token', 'detail': str(e)}
                )
        
        # No authentication provided
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={'error': 'Authentication required'}
        )
    
    async def _check_rate_limits(self, request: Request, user: User, api_key: Optional[APIKey], db: Session) -> Union[Dict[str, Any], Response]:
        """Check rate limits for the request"""
        # Determine rate limit based on API key or user subscription
        if api_key and api_key.rate_limit:
            limit = api_key.rate_limit
            key = f"api_key:{api_key.id}"
        else:
            # Get user's subscription plan rate limit
            subscription = user.subscription
            if subscription and subscription.status.value == 'active':
                # Define rate limits per plan
                plan_limits = {
                    'free': 100,
                    'pro': 1000,
                    'enterprise': 10000
                }
                limit = plan_limits.get(subscription.plan.value, 100)
            else:
                limit = 100  # Default for free users
            
            key = f"user:{user.id}"
        
        # Check rate limit
        is_limited, rate_limit_info = self.rate_limiter.is_rate_limited(key, limit)
        
        if is_limited:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    'error': 'Rate limit exceeded',
                    'detail': f'Rate limit of {limit} requests per hour exceeded',
                    'rate_limit': rate_limit_info
                },
                headers={
                    'X-RateLimit-Limit': str(rate_limit_info['limit']),
                    'X-RateLimit-Remaining': str(rate_limit_info['remaining']),
                    'X-RateLimit-Reset': str(rate_limit_info['reset_time']),
                    'Retry-After': str(rate_limit_info['window'])
                }
            )
        
        return rate_limit_info
    
    async def _check_permissions(self, request: Request, user: User, db: Session) -> Optional[Response]:
        """Check if user has required permissions for the endpoint"""
        path = request.url.path
        method = request.method
        
        # Define endpoint permission requirements
        endpoint_permissions = {
            # User endpoints
            ('GET', '/api/v1/users'): ['user:read'],
            ('POST', '/api/v1/users'): ['user:write'],
            ('PUT', '/api/v1/users'): ['user:write'],
            ('DELETE', '/api/v1/users'): ['user:delete'],
            
            # Project endpoints
            ('GET', '/api/v1/projects'): ['project:read'],
            ('POST', '/api/v1/projects'): ['project:write'],
            ('PUT', '/api/v1/projects'): ['project:write'],
            ('DELETE', '/api/v1/projects'): ['project:delete'],
            
            # API key endpoints
            ('GET', '/api/v1/api-keys'): ['api_key:read'],
            ('POST', '/api/v1/api-keys'): ['api_key:write'],
            ('DELETE', '/api/v1/api-keys'): ['api_key:delete'],
            
            # External integration endpoints
            ('GET', '/api/v1/integrations'): ['external_integration:read'],
            ('POST', '/api/v1/integrations'): ['external_integration:write'],
            ('PUT', '/api/v1/integrations'): ['external_integration:write'],
            ('DELETE', '/api/v1/integrations'): ['external_integration:delete'],
            
            # Sensitive data endpoints
            ('GET', '/api/v1/sensitive-data'): ['sensitive_data:read'],
            ('POST', '/api/v1/sensitive-data'): ['sensitive_data:write'],
        }
        
        # Check for exact path match first
        required_permissions = endpoint_permissions.get((method, path))
        
        # If no exact match, check for pattern matches
        if not required_permissions:
            for (req_method, req_path), perms in endpoint_permissions.items():
                if method == req_method and self._path_matches(path, req_path):
                    required_permissions = perms
                    break
        
        # If no permissions required, allow access
        if not required_permissions:
            return None
        
        # Check if user has required permissions
        user_permissions = self.permission_checker.get_user_permissions(user.id, db)
        
        for permission in required_permissions:
            if permission not in user_permissions:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        'error': 'Insufficient permissions',
                        'detail': f'Required permission: {permission}',
                        'required_permissions': required_permissions
                    }
                )
        
        return None
    
    def _path_matches(self, actual_path: str, pattern_path: str) -> bool:
        """Check if actual path matches pattern (simple implementation)"""
        # Handle path parameters like /api/v1/users/{user_id}
        pattern_parts = pattern_path.split('/')
        actual_parts = actual_path.split('/')
        
        if len(pattern_parts) != len(actual_parts):
            return False
        
        for pattern_part, actual_part in zip(pattern_parts, actual_parts):
            if pattern_part.startswith('{') and pattern_part.endswith('}'):
                continue  # Path parameter, matches anything
            if pattern_part != actual_part:
                return False
        
        return True
    
    async def _log_usage(self, request: Request, response: Response, user: User, 
                        api_key: Optional[APIKey], start_time: float, db: Session):
        """Log API usage for analytics and billing"""
        try:
            response_time = time.time() - start_time
            
            usage = Usage(
                user_id=user.id,
                api_key_id=api_key.id if api_key else None,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time=response_time,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get('User-Agent'),
                timestamp=datetime.utcnow()
            )
            
            db.add(usage)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging usage: {e}")
            db.rollback()
    
    def _add_rate_limit_headers(self, response: Response, rate_limit_info: Dict[str, Any]):
        """Add rate limit headers to response"""
        response.headers['X-RateLimit-Limit'] = str(rate_limit_info['limit'])
        response.headers['X-RateLimit-Remaining'] = str(rate_limit_info['remaining'])
        response.headers['X-RateLimit-Reset'] = str(rate_limit_info['reset_time'])

# Middleware instance
api_access_control = APIAccessControlMiddleware()

# Dependency for getting current user from middleware
def get_current_user_from_middleware(request: Request) -> User:
    """Get current user from middleware state"""
    if not hasattr(request.state, 'user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Authentication required'
        )
    return request.state.user

def get_current_api_key_from_middleware(request: Request) -> Optional[APIKey]:
    """Get current API key from middleware state"""
    return getattr(request.state, 'api_key', None)

def get_rate_limit_info_from_middleware(request: Request) -> Dict[str, Any]:
    """Get rate limit info from middleware state"""
    return getattr(request.state, 'rate_limit_info', {})