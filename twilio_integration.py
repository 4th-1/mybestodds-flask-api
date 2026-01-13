"""
Twilio SMS Integration for My Best Odds
Handles prediction alerts and winning notifications via SMS
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwilioClient:
    """Twilio SMS client for sending prediction alerts"""
    
    def __init__(self):
        """Initialize Twilio client with credentials from environment"""
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.client = None
        
        if self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio client initialized successfully")
            except ImportError:
                logger.error("Twilio package not installed. Run: pip install twilio")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
        else:
            logger.warning("Twilio credentials not configured in .env file")
    
    def is_connected(self) -> bool:
        """Check if Twilio client is properly configured"""
        return self.client is not None
    
    def send_sms(self, to_phone: str, message: str) -> Dict:
        """
        Send SMS message
        
        Args:
            to_phone: Recipient phone number in E.164 format (+1234567890)
            message: SMS message content (max 160 chars recommended)
            
        Returns:
            Dict with success status and message SID
        """
        if not self.is_connected():
            logger.error("Twilio client not initialized")
            return {"success": False, "error": "Twilio not configured"}
        
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_phone
            )
            
            logger.info(f"SMS sent to {to_phone}: {message.sid}")
            return {
                "success": True,
                "message_sid": message.sid,
                "status": message.status,
                "to": to_phone
            }
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {e}")
            return {
                "success": False,
                "error": str(e),
                "to": to_phone
            }
    
    def send_prediction_alert(
        self,
        subscriber: Dict,
        predictions: List[Dict],
        date: str
    ) -> Dict:
        """
        Send daily prediction alert to subscriber
        
        Args:
            subscriber: Subscriber data with phone number
            predictions: List of prediction objects
            date: Prediction date (YYYY-MM-DD)
            
        Returns:
            Dict with send status
        """
        phone = subscriber.get('phone')
        if not phone:
            return {"success": False, "error": "No phone number for subscriber"}
        
        first_name = subscriber.get('identity', {}).get('first_name', 'Player')
        kit_type = subscriber.get('kit_type', 'BOOK')
        
        # Format predictions for SMS (keep under 160 chars)
        top_predictions = predictions[:3]  # Top 3 predictions
        
        message = f"🎯 MY BEST ODDS {kit_type}\n\n"
        message += f"Hi {first_name}! Today's top picks:\n\n"
        
        for i, pred in enumerate(top_predictions, 1):
            game = pred.get('game', 'Unknown')
            number = pred.get('number', '???')
            confidence = pred.get('confidence', 0)
            band = pred.get('band', 'GREEN')
            
            emoji = "🔴" if band == "RED" else "🟡" if band == "YELLOW" else "🟢"
            message += f"{emoji} {game}: {number} ({confidence}%)\n"
        
        message += f"\nGood luck! 🍀"
        
        return self.send_sms(phone, message)
    
    def send_win_notification(
        self,
        subscriber: Dict,
        win_details: Dict
    ) -> Dict:
        """
        Send winning notification to subscriber
        
        Args:
            subscriber: Subscriber data with phone number
            win_details: Win information (game, number, amount, etc.)
            
        Returns:
            Dict with send status
        """
        phone = subscriber.get('phone')
        if not phone:
            return {"success": False, "error": "No phone number for subscriber"}
        
        first_name = subscriber.get('identity', {}).get('first_name', 'Player')
        game = win_details.get('game', 'Unknown')
        number = win_details.get('number', '???')
        amount = win_details.get('amount', 0)
        play_type = win_details.get('play_type', 'STRAIGHT')
        
        message = f"🎉 WINNER! 🎉\n\n"
        message += f"{first_name}, you predicted correctly!\n\n"
        message += f"🎮 Game: {game}\n"
        message += f"🔢 Number: {number}\n"
        message += f"💰 Est. Win: ${amount}\n"
        message += f"📋 Play: {play_type}\n\n"
        message += f"Congratulations! 🏆"
        
        return self.send_sms(phone, message)
    
    def send_high_confidence_alert(
        self,
        subscriber: Dict,
        prediction: Dict
    ) -> Dict:
        """
        Send high-confidence prediction alert (85%+ confidence)
        
        Args:
            subscriber: Subscriber data
            prediction: High-confidence prediction
            
        Returns:
            Dict with send status
        """
        phone = subscriber.get('phone')
        if not phone:
            return {"success": False, "error": "No phone number for subscriber"}
        
        first_name = subscriber.get('identity', {}).get('first_name', 'Player')
        game = prediction.get('game', 'Unknown')
        number = prediction.get('number', '???')
        confidence = prediction.get('confidence', 0)
        session = prediction.get('session', 'Unknown')
        draw_time = prediction.get('draw_time', 'Unknown')
        
        message = f"🚨 HIGH CONFIDENCE ALERT! 🚨\n\n"
        message += f"{first_name}, urgent prediction:\n\n"
        message += f"🎮 {game} {session}\n"
        message += f"🔢 {number}\n"
        message += f"💚 {confidence}% CONFIDENCE\n"
        message += f"⏰ Draw: {draw_time}\n\n"
        message += f"Don't miss this one! 🎯"
        
        return self.send_sms(phone, message)
    
    def send_draw_reminder(
        self,
        subscriber: Dict,
        game: str,
        session: str,
        draw_time: str,
        top_prediction: Dict
    ) -> Dict:
        """
        Send reminder before draw time
        
        Args:
            subscriber: Subscriber data
            game: Game name
            session: Session (Midday/Evening)
            draw_time: Draw time string
            top_prediction: Top prediction for this draw
            
        Returns:
            Dict with send status
        """
        phone = subscriber.get('phone')
        if not phone:
            return {"success": False, "error": "No phone number for subscriber"}
        
        first_name = subscriber.get('identity', {}).get('first_name', 'Player')
        number = top_prediction.get('number', '???')
        confidence = top_prediction.get('confidence', 0)
        
        message = f"⏰ DRAW REMINDER\n\n"
        message += f"{first_name}, {game} {session} in 15 min!\n\n"
        message += f"🔢 Top pick: {number}\n"
        message += f"💚 {confidence}% confidence\n"
        message += f"⏰ Draw: {draw_time}\n\n"
        message += f"Time to play! 🎰"
        
        return self.send_sms(phone, message)
    
    def send_bulk_sms(
        self,
        recipients: List[Dict],
        message: str
    ) -> Dict:
        """
        Send SMS to multiple recipients
        
        Args:
            recipients: List of dicts with 'phone' and optional 'name'
            message: Message to send to all
            
        Returns:
            Dict with success/failure counts
        """
        results = {
            "total": len(recipients),
            "success": 0,
            "failed": 0,
            "details": []
        }
        
        for recipient in recipients:
            phone = recipient.get('phone')
            if not phone:
                results['failed'] += 1
                continue
            
            result = self.send_sms(phone, message)
            if result.get('success'):
                results['success'] += 1
            else:
                results['failed'] += 1
            
            results['details'].append({
                "phone": phone,
                "status": result.get('status'),
                "message_sid": result.get('message_sid')
            })
        
        logger.info(f"Bulk SMS complete: {results['success']}/{results['total']} sent")
        return results


# Singleton instance
_twilio_client = None

def get_twilio_client() -> TwilioClient:
    """Get or create Twilio client singleton"""
    global _twilio_client
    if _twilio_client is None:
        _twilio_client = TwilioClient()
    return _twilio_client


# Convenience functions
def send_sms(to_phone: str, message: str) -> Dict:
    """Quick SMS send"""
    client = get_twilio_client()
    return client.send_sms(to_phone, message)


def send_prediction_alert(subscriber: Dict, predictions: List[Dict], date: str) -> Dict:
    """Quick prediction alert"""
    client = get_twilio_client()
    return client.send_prediction_alert(subscriber, predictions, date)


def send_win_notification(subscriber: Dict, win_details: Dict) -> Dict:
    """Quick win notification"""
    client = get_twilio_client()
    return client.send_win_notification(subscriber, win_details)


if __name__ == "__main__":
    # Test Twilio connection
    client = get_twilio_client()
    print(f"Twilio connected: {client.is_connected()}")
    
    if client.is_connected():
        print(f"Account SID: {client.account_sid[:10]}...")
        print(f"Phone number: {client.phone_number}")
