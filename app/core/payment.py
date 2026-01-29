import stripe
import os
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

def create_checkout_session(amount: float, currency: str = "gbp", metadata: dict = None, success_url: str = None, cancel_url: str = None):
    """Create a Stripe Checkout Session"""
    try:
        job_id = metadata.get("job_id", "N/A") if metadata else "N/A"
        payment_type = metadata.get("payment_type", "Payment") if metadata else "Payment"
        
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": currency,
                    "unit_amount": int(amount * 100),
                    "product_data": {
                        "name": f"{payment_type.title()} Payment",
                        "description": f"Job ID: {job_id} - {payment_type.title()} payment"
                    }
                },
                "quantity": 1
            }],
            mode="payment",
            success_url=success_url or "https://ui-packers-y8cjd.ondigitalocean.app/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url or "https://ui-packers-y8cjd.ondigitalocean.app/payment/cancel",
            metadata=metadata or {}
        )
        return {
            "checkout_url": session.url,
            "session_id": session.id
        }
    except Exception as e:
        raise Exception(f"Checkout session creation failed: {str(e)}")

def verify_payment(payment_intent_id: str):
    """Verify payment status"""
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return intent.status == "succeeded"
    except Exception as e:
        raise Exception(f"Payment verification failed: {str(e)}")

def create_refund(session_id: str, amount: float = None):
    """Create a refund for Checkout Session"""
    try:
        # Get payment intent from session
        session = stripe.checkout.Session.retrieve(session_id)
        payment_intent_id = session.payment_intent
        
        refund_data = {"payment_intent": payment_intent_id}
        if amount:
            refund_data["amount"] = int(amount * 100)
        
        refund = stripe.Refund.create(**refund_data)
        return {
            "refund_id": refund.id,
            "status": refund.status
        }
    except Exception as e:
        raise Exception(f"Refund creation failed: {str(e)}")
