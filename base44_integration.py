"""
Base44 integration stub for Railway deployment
"""
import logging

logger = logging.getLogger(__name__)

def get_active_subscribers_from_base44():
    """
    Stub function - Base44 integration not available on Railway
    Returns empty list since Railway uses inline subscriber data from webhooks
    """
    logger.warning("Base44 credentials not configured. Using inline subscriber data from webhooks.")
    return []

def get_subscriber_from_base44(subscriber_id):
    """
    Stub function - Base44 integration not available on Railway
    Returns None since Railway uses inline subscriber data from webhooks
    """
    logger.warning(f"Base44 credentials not configured. Cannot fetch subscriber {subscriber_id}.")
    return None

def update_subscriber_prediction_in_base44(subscriber_id, prediction_data):
    """
    Stub function - Base44 integration not available on Railway
    """
    logger.warning("Base44 credentials not configured. Cannot update prediction in Base44.")
    return False
