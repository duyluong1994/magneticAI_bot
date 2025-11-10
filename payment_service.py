"""Payment service for handling payment completion logic."""
from datetime import datetime
from decimal import Decimal

from database import Payment, PaymentStatus, User
from sqlalchemy.orm import Session


def update_user_lifetime_earnings_if_needed(db: Session, payment: Payment):
    """
    Update user's totalPaidOut if payment is completed and not already counted.
    This replicates the updateUserLifetimeEarningsIfNeeded function from payment.js
    Note: Does not commit - commit should be done by caller
    """
    if payment.status == PaymentStatus.COMPLETED:
        user = db.query(User).filter(User.id == payment.userId).first()
        if user:
            current_total = Decimal(str(user.totalPaidOut)) if user.totalPaidOut else Decimal('0.00')
            payment_amount = Decimal(str(payment.amount)) if payment.amount else Decimal('0.00')
            user.totalPaidOut = float(current_total + payment_amount)


def complete_payments(db: Session, payment_ids: list) -> dict:
    """
    Complete multiple payments. Replicates the /complete-payout endpoint logic.
    
    Args:
        db: Database session
        payment_ids: List of payment IDs (UUIDs as strings)
    
    Returns:
        dict with success status, message, and details
    """
    if not payment_ids:
        return {
            'success': False,
            'message': 'Payment IDs are required'
        }
    
    if not isinstance(payment_ids, list):
        return {
            'success': False,
            'message': 'Payment IDs must be an array'
        }
    
    if len(payment_ids) == 0:
        return {
            'success': False,
            'message': 'Payment IDs array cannot be empty'
        }
    
    results = []
    success_count = 0
    not_found_count = 0
    error_count = 0
    
    for payment_id in payment_ids:
        try:
            # Use raw SQL to avoid enum validation issues
            from sqlalchemy import text

            # First check if payment exists and get current status
            result = db.execute(
                text("SELECT status, \"userId\", amount FROM \"Payments\" WHERE id = :payment_id"),
                {"payment_id": payment_id}
            ).first()
            
            if result:
                current_status = result.status  # This will be a string like 'processing'
                was_completed = current_status == 'completed'
                user_id = result.userId
                amount = result.amount
                
                # Update payment status using raw SQL
                # PostgreSQL will automatically convert string to enum if value matches
                # No need to cast explicitly - just send the string value
                db.execute(
                    text("""
                        UPDATE "Payments" 
                        SET status = :status,
                            "processedAt" = :processed_at,
                            "updatedAt" = :updated_at
                        WHERE id = :payment_id
                    """),
                    {
                        "payment_id": payment_id,
                        "status": PaymentStatus.COMPLETED.value,  # 'completed' - PostgreSQL will auto-convert
                        "processed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                )
                
                # Update user lifetime earnings if not already completed
                if not was_completed:
                    # Get user and update totalPaidOut
                    user_result = db.execute(
                        text("SELECT \"totalPaidOut\" FROM \"Users\" WHERE id = :user_id"),
                        {"user_id": user_id}
                    ).first()
                    
                    if user_result:
                        current_total = Decimal(str(user_result.totalPaidOut)) if user_result.totalPaidOut else Decimal('0.00')
                        payment_amount = Decimal(str(amount)) if amount else Decimal('0.00')
                        new_total = float(current_total + payment_amount)
                        
                        db.execute(
                            text("UPDATE \"Users\" SET \"totalPaidOut\" = :total WHERE id = :user_id"),
                            {"user_id": user_id, "total": new_total}
                        )
                
                db.commit()
                
                results.append({
                    'paymentId': payment_id,
                    'status': 'completed',
                    'wasAlreadyCompleted': was_completed
                })
                success_count += 1
            else:
                results.append({
                    'paymentId': payment_id,
                    'status': 'not_found'
                })
                not_found_count += 1
        except Exception as e:
            db.rollback()
            results.append({
                'paymentId': payment_id,
                'status': 'error',
                'error': str(e)
            })
            error_count += 1
    
    return {
        'success': True,
        'message': f'Processed {len(payment_ids)} payment(s). {success_count} completed, {not_found_count} not found, {error_count} errors.',
        'results': results,
        'summary': {
            'total': len(payment_ids),
            'completed': success_count,
            'not_found': not_found_count,
            'errors': error_count
        }
    }

