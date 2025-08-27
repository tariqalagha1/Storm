from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, Any
import stripe
from datetime import datetime, timedelta

from ..database import get_db
from ..models import User, Subscription, SubscriptionPlan, SubscriptionStatus
from ..schemas import (
    SubscriptionResponse, SubscriptionUpdate, MessageResponse
)
from ..auth import get_current_user
from ..config import settings

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter()

# Subscription plans configuration
SUBSCRIPTION_PLANS = {
    SubscriptionPlan.FREE: {
        "name": "Free",
        "price": 0,
        "features": ["5 API calls per day", "Basic support"],
        "limits": {"api_calls_per_month": 150}
    },
    SubscriptionPlan.BASIC: {
        "name": "Basic",
        "price": 9.99,
        "stripe_price_id": "price_basic_monthly",
        "features": ["1,000 API calls per month", "Email support", "Basic analytics"],
        "limits": {"api_calls_per_month": 1000}
    },
    SubscriptionPlan.PREMIUM: {
        "name": "Premium",
        "price": 29.99,
        "stripe_price_id": "price_premium_monthly",
        "features": ["10,000 API calls per month", "Priority support", "Advanced analytics", "Custom integrations"],
        "limits": {"api_calls_per_month": 10000}
    },
    SubscriptionPlan.ENTERPRISE: {
        "name": "Enterprise",
        "price": 99.99,
        "stripe_price_id": "price_enterprise_monthly",
        "features": ["Unlimited API calls", "24/7 support", "Custom features", "SLA guarantee"],
        "limits": {"api_calls_per_month": -1}  # -1 means unlimited
    }
}

@router.get("/plans")
async def get_subscription_plans():
    """Get available subscription plans"""
    return SUBSCRIPTION_PLANS

@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        # Create default free subscription if none exists
        subscription = Subscription(
            user_id=current_user.id,
            plan=SubscriptionPlan.FREE,
            status=SubscriptionStatus.ACTIVE
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    
    return subscription

@router.post("/create-checkout-session")
async def create_checkout_session(
    plan: SubscriptionPlan,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe checkout session for subscription"""
    if plan == SubscriptionPlan.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create checkout session for free plan"
        )
    
    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription plan"
        )
    
    plan_config = SUBSCRIPTION_PLANS[plan]
    
    try:
        # Create or get Stripe customer
        subscription = db.query(Subscription).filter(
            Subscription.user_id == current_user.id
        ).first()
        
        if subscription and subscription.stripe_customer_id:
            customer_id = subscription.stripe_customer_id
        else:
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name or current_user.username,
                metadata={"user_id": current_user.id}
            )
            customer_id = customer.id
            
            # Update subscription with customer ID
            if subscription:
                subscription.stripe_customer_id = customer_id
                db.commit()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan_config['stripe_price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{settings.FRONTEND_URL}/dashboard?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/pricing",
            metadata={
                "user_id": current_user.id,
                "plan": plan.value
            }
        )
        
        return {"checkout_url": checkout_session.url}
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )

@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel current subscription"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    if subscription.plan == SubscriptionPlan.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel free plan"
        )
    
    try:
        if subscription.stripe_subscription_id:
            # Cancel Stripe subscription
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
        
        # Update subscription status
        subscription.status = SubscriptionStatus.CANCELLED
        db.commit()
        
        return {"message": "Subscription cancelled successfully"}
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )

@router.post("/reactivate")
async def reactivate_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reactivate cancelled subscription"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    if subscription.status != SubscriptionStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is not cancelled"
        )
    
    try:
        if subscription.stripe_subscription_id:
            # Reactivate Stripe subscription
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False
            )
        
        # Update subscription status
        subscription.status = SubscriptionStatus.ACTIVE
        db.commit()
        
        return {"message": "Subscription reactivated successfully"}
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )

@router.get("/usage")
async def get_subscription_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current subscription usage"""
    from ..models import Usage
    from sqlalchemy import func, extract
    
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    # Get current month usage
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    usage_count = db.query(func.count(Usage.id)).filter(
        Usage.user_id == current_user.id,
        extract('month', Usage.timestamp) == current_month,
        extract('year', Usage.timestamp) == current_year
    ).scalar() or 0
    
    plan_config = SUBSCRIPTION_PLANS[subscription.plan]
    limit = plan_config['limits']['api_calls_per_month']
    
    return {
        "current_usage": usage_count,
        "limit": limit,
        "unlimited": limit == -1,
        "percentage_used": (usage_count / limit * 100) if limit > 0 else 0,
        "plan": subscription.plan,
        "status": subscription.status
    }

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhooks"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        await handle_successful_payment(session, db)
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        await handle_successful_payment_renewal(invoice, db)
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        await handle_failed_payment(invoice, db)
    
    return {"status": "success"}

async def handle_successful_payment(session: Dict[str, Any], db: Session):
    """Handle successful payment from Stripe"""
    user_id = int(session['metadata']['user_id'])
    plan = session['metadata']['plan']
    
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()
    
    if subscription:
        subscription.plan = SubscriptionPlan(plan)
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.stripe_subscription_id = session['subscription']
        subscription.current_period_start = datetime.utcnow()
        subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
        db.commit()

async def handle_successful_payment_renewal(invoice: Dict[str, Any], db: Session):
    """Handle successful payment renewal"""
    subscription_id = invoice['subscription']
    
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if subscription:
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_start = datetime.utcfromtimestamp(invoice['period_start'])
        subscription.current_period_end = datetime.utcfromtimestamp(invoice['period_end'])
        db.commit()

async def handle_failed_payment(invoice: Dict[str, Any], db: Session):
    """Handle failed payment"""
    subscription_id = invoice['subscription']
    
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription_id
    ).first()
    
    if subscription:
        subscription.status = SubscriptionStatus.PAST_DUE
        db.commit()