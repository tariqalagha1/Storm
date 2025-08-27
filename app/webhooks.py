import asyncio
import json
import hmac
import hashlib
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import event
from fastapi import BackgroundTasks
import logging

from .database import get_db
from .models import (
    User, Project, APIKey, Subscription, Usage, Notification,
    ExternalIntegration, AuditLog, DataSensitivityLevel
)
from .security import sanitize_for_api
from .config import settings

logger = logging.getLogger(__name__)

class WebhookEvent(str, Enum):
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    
    PROJECT_CREATED = "project.created"
    PROJECT_UPDATED = "project.updated"
    PROJECT_DELETED = "project.deleted"
    
    API_KEY_CREATED = "api_key.created"
    API_KEY_UPDATED = "api_key.updated"
    API_KEY_DELETED = "api_key.deleted"
    
    SUBSCRIPTION_CREATED = "subscription.created"
    SUBSCRIPTION_UPDATED = "subscription.updated"
    SUBSCRIPTION_CANCELLED = "subscription.cancelled"
    
    USAGE_RECORDED = "usage.recorded"
    USAGE_LIMIT_REACHED = "usage.limit_reached"
    
    NOTIFICATION_CREATED = "notification.created"

class WebhookPayload:
    """Structure for webhook payload"""
    
    def __init__(self, event: WebhookEvent, data: Dict[str, Any], 
                 user_id: Optional[int] = None, integration_type: str = 'general'):
        self.event = event
        self.data = data
        self.user_id = user_id
        self.integration_type = integration_type
        self.timestamp = datetime.utcnow().isoformat()
        self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique webhook ID"""
        import uuid
        return str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'event': self.event.value,
            'data': self.data,
            'user_id': self.user_id,
            'timestamp': self.timestamp,
            'integration_type': self.integration_type
        }

class WebhookSigner:
    """Handle webhook signature generation and verification"""
    
    @staticmethod
    def generate_signature(payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload"""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    @staticmethod
    def verify_signature(payload: str, signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        expected_signature = WebhookSigner.generate_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)

class WebhookDelivery:
    """Handle webhook delivery to external endpoints"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.max_retries = 3
        self.retry_delays = [1, 5, 15]  # seconds
    
    async def deliver_webhook(self, webhook_url: str, payload: WebhookPayload, 
                            secret: Optional[str] = None) -> bool:
        """Deliver webhook to external endpoint with retries"""
        payload_json = json.dumps(payload.to_dict())
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Storm-Webhook/1.0',
            'X-Webhook-Event': payload.event.value,
            'X-Webhook-ID': payload.id,
            'X-Webhook-Timestamp': payload.timestamp
        }
        
        # Add signature if secret is provided
        if secret:
            signature = WebhookSigner.generate_signature(payload_json, secret)
            headers['X-Webhook-Signature'] = signature
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    webhook_url,
                    content=payload_json,
                    headers=headers
                )
                
                if response.status_code in [200, 201, 202, 204]:
                    logger.info(f"Webhook delivered successfully to {webhook_url}")
                    return True
                else:
                    logger.warning(f"Webhook delivery failed with status {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Webhook delivery attempt {attempt + 1} failed: {str(e)}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delays[attempt])
        
        logger.error(f"Webhook delivery failed after {self.max_retries} attempts to {webhook_url}")
        return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

class WebhookManager:
    """Manage webhook subscriptions and delivery"""
    
    def __init__(self):
        self.delivery = WebhookDelivery()
        self.event_handlers: Dict[WebhookEvent, List[Callable]] = {}
    
    def register_handler(self, event: WebhookEvent, handler: Callable):
        """Register a handler for a specific webhook event"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
    
    async def trigger_webhook(self, event: WebhookEvent, data: Dict[str, Any], 
                            user_id: Optional[int] = None, db: Optional[Session] = None):
        """Trigger webhook for an event"""
        if not db:
            return
        
        # Get active integrations that should receive this webhook
        integrations = db.query(ExternalIntegration).filter(
            ExternalIntegration.is_active == True,
            ExternalIntegration.webhook_url.isnot(None)
        ).all()
        
        for integration in integrations:
            # Check if this integration should receive this event
            if self._should_send_webhook(integration, event, user_id):
                # Sanitize data based on integration type
                sanitized_data = sanitize_for_api(data, integration.integration_type)
                
                # Create webhook payload
                payload = WebhookPayload(
                    event=event,
                    data=sanitized_data,
                    user_id=user_id,
                    integration_type=integration.integration_type
                )
                
                # Deliver webhook asynchronously
                asyncio.create_task(
                    self.delivery.deliver_webhook(
                        integration.webhook_url,
                        payload,
                        integration.webhook_secret
                    )
                )
        
        # Call registered handlers
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    await handler(event, data, user_id)
                except Exception as e:
                    logger.error(f"Webhook handler error: {str(e)}")
    
    def _should_send_webhook(self, integration: ExternalIntegration, 
                           event: WebhookEvent, user_id: Optional[int]) -> bool:
        """Determine if webhook should be sent to this integration"""
        # Parse integration configuration to determine which events to send
        # This could be expanded to include more sophisticated filtering
        
        # For now, send all events to all active integrations
        # In production, you might want to filter based on:
        # - Event type preferences
        # - User permissions
        # - Integration-specific settings
        
        return True
    
    async def close(self):
        """Close webhook manager resources"""
        await self.delivery.close()

# Global webhook manager instance
webhook_manager = WebhookManager()

# Database event listeners for automatic webhook triggering
def setup_database_listeners():
    """Setup SQLAlchemy event listeners for automatic webhook triggering"""
    
    @event.listens_for(User, 'after_insert')
    def user_created(mapper, connection, target):
        """Trigger webhook when user is created"""
        asyncio.create_task(_trigger_webhook_with_db(
            WebhookEvent.USER_CREATED,
            {
                'id': target.id,
                'email': target.email,
                'username': target.username,
                'role': target.role.value,
                'created_at': target.created_at.isoformat() if target.created_at else None
            },
            target.id
        ))
    
    @event.listens_for(User, 'after_update')
    def user_updated(mapper, connection, target):
        """Trigger webhook when user is updated"""
        asyncio.create_task(_trigger_webhook_with_db(
            WebhookEvent.USER_UPDATED,
            {
                'id': target.id,
                'email': target.email,
                'username': target.username,
                'role': target.role.value,
                'updated_at': target.updated_at.isoformat() if target.updated_at else None
            },
            target.id
        ))
    
    @event.listens_for(Project, 'after_insert')
    def project_created(mapper, connection, target):
        """Trigger webhook when project is created"""
        asyncio.create_task(_trigger_webhook_with_db(
            WebhookEvent.PROJECT_CREATED,
            {
                'id': target.id,
                'name': target.name,
                'description': target.description,
                'owner_id': target.owner_id,
                'created_at': target.created_at.isoformat() if target.created_at else None
            },
            target.owner_id
        ))
    
    @event.listens_for(Project, 'after_update')
    def project_updated(mapper, connection, target):
        """Trigger webhook when project is updated"""
        asyncio.create_task(_trigger_webhook_with_db(
            WebhookEvent.PROJECT_UPDATED,
            {
                'id': target.id,
                'name': target.name,
                'description': target.description,
                'owner_id': target.owner_id,
                'is_active': target.is_active,
                'updated_at': target.updated_at.isoformat() if target.updated_at else None
            },
            target.owner_id
        ))
    
    @event.listens_for(APIKey, 'after_insert')
    def api_key_created(mapper, connection, target):
        """Trigger webhook when API key is created"""
        asyncio.create_task(_trigger_webhook_with_db(
            WebhookEvent.API_KEY_CREATED,
            {
                'id': target.id,
                'name': target.name,
                'user_id': target.user_id,
                'project_id': target.project_id,
                'rate_limit': target.rate_limit,
                'created_at': target.created_at.isoformat() if target.created_at else None
            },
            target.user_id
        ))
    
    @event.listens_for(Subscription, 'after_update')
    def subscription_updated(mapper, connection, target):
        """Trigger webhook when subscription is updated"""
        asyncio.create_task(_trigger_webhook_with_db(
            WebhookEvent.SUBSCRIPTION_UPDATED,
            {
                'id': target.id,
                'user_id': target.user_id,
                'plan': target.plan.value,
                'status': target.status.value,
                'updated_at': target.updated_at.isoformat() if target.updated_at else None
            },
            target.user_id
        ))
    
    @event.listens_for(Usage, 'after_insert')
    def usage_recorded(mapper, connection, target):
        """Trigger webhook when usage is recorded"""
        asyncio.create_task(_trigger_webhook_with_db(
            WebhookEvent.USAGE_RECORDED,
            {
                'id': target.id,
                'user_id': target.user_id,
                'endpoint': target.endpoint,
                'method': target.method,
                'status_code': target.status_code,
                'response_time': float(target.response_time) if target.response_time else None,
                'timestamp': target.timestamp.isoformat() if target.timestamp else None
            },
            target.user_id
        ))

async def _trigger_webhook_with_db(event: WebhookEvent, data: Dict[str, Any], user_id: Optional[int]):
    """Helper function to trigger webhook with database session"""
    try:
        # Get a new database session
        from .database import SessionLocal
        db = SessionLocal()
        try:
            await webhook_manager.trigger_webhook(event, data, user_id, db)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error triggering webhook: {str(e)}")

# Helper functions for manual webhook triggering
async def trigger_user_webhook(event: WebhookEvent, user: User, db: Session):
    """Manually trigger user-related webhook"""
    user_data = {
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'full_name': user.full_name,
        'role': user.role.value,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None
    }
    
    await webhook_manager.trigger_webhook(event, user_data, user.id, db)

async def trigger_project_webhook(event: WebhookEvent, project: Project, db: Session):
    """Manually trigger project-related webhook"""
    project_data = {
        'id': project.id,
        'name': project.name,
        'description': project.description,
        'owner_id': project.owner_id,
        'is_active': project.is_active,
        'created_at': project.created_at.isoformat() if project.created_at else None,
        'updated_at': project.updated_at.isoformat() if project.updated_at else None
    }
    
    await webhook_manager.trigger_webhook(event, project_data, project.owner_id, db)

async def trigger_subscription_webhook(event: WebhookEvent, subscription: Subscription, db: Session):
    """Manually trigger subscription-related webhook"""
    subscription_data = {
        'id': subscription.id,
        'user_id': subscription.user_id,
        'plan': subscription.plan.value,
        'status': subscription.status.value,
        'current_period_start': subscription.current_period_start.isoformat() if subscription.current_period_start else None,
        'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        'created_at': subscription.created_at.isoformat() if subscription.created_at else None,
        'updated_at': subscription.updated_at.isoformat() if subscription.updated_at else None
    }
    
    await webhook_manager.trigger_webhook(event, subscription_data, subscription.user_id, db)

# Initialize database listeners
setup_database_listeners()