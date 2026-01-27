"""
Twilio integration stub for Railway deployment
"""
import logging

logger = logging.getLogger(__name__)

def send_sms(to_number, message):
    """
    Stub function - Twilio integration not available on Railway
    """
    logger.warning("Twilio credentials not configured. SMS not sent.")
    return False

def send_prediction_sms(subscriber, prediction):
    """
    Stub function - Twilio integration not available on Railway
    """
    logger.warning("Twilio credentials not configured. Prediction SMS not sent.")
    return False
