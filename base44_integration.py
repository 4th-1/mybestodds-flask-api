"""
Base44 SDK Integration
======================
Python wrapper for Base44 API calls
"""

import os
import json
import requests
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class Base44Client:
    """
    Client for interacting with Base44 API
    
    Environment variables:
        BASE44_API_KEY: Base44 API authentication key
        BASE44_WORKSPACE_ID: Base44 workspace identifier
        BASE44_API_URL: Base44 API endpoint (default: https://api.base44.com)
    """
    
    def __init__(self):
        self.api_key = os.environ.get('BASE44_API_KEY')
        self.workspace_id = os.environ.get('BASE44_WORKSPACE_ID')
        self.api_url = os.environ.get('BASE44_API_URL', 'https://api.base44.com')
        
        # Check if credentials are configured
        self._connected = bool(self.api_key and self.workspace_id)
        
        if not self._connected:
            logger.warning("Base44 credentials not configured. Set BASE44_API_KEY and BASE44_WORKSPACE_ID environment variables.")
        else:
            logger.info(f"Base44 client initialized for workspace {self.workspace_id}")
    
    def is_connected(self) -> bool:
        """Check if Base44 credentials are configured"""
        return self._connected
    
    def _get_headers(self) -> Dict:
        """Get authentication headers for API requests"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'X-Workspace-ID': self.workspace_id
        }
    
    def create_prediction(self, subscriber_id: str, date: str, predictions: Dict) -> Dict:
        """
        Create a new prediction in Base44 Prediction entity
        
        Args:
            subscriber_id: Base44 subscriber ID
            date: ISO date string (e.g., "2026-01-11")
            predictions: Prediction data dict with game results
        
        Returns:
            {
                "success": true,
                "prediction_id": "pred_xyz123",
                "subscriber_id": "sub_abc",
                "date": "2026-01-11"
            }
        """
        if not self._connected:
            return {
                "success": False,
                "error": "Base44 not configured. Set environment variables."
            }
        
        try:
            # Prepare prediction payload
            payload = {
                "subscriber_id": subscriber_id,
                "date": date,
                "predictions": predictions,
                "engine_version": "v3.7_recalibrated",
                "generated_at": date
            }
            
            # Make API request to create prediction
            response = requests.post(
                f"{self.api_url}/v1/predictions",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"Created prediction {data.get('id')} for {subscriber_id}")
                return {
                    "success": True,
                    "prediction_id": data.get('id'),
                    "subscriber_id": subscriber_id,
                    "date": date
                }
            else:
                logger.error(f"Failed to create prediction: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "details": response.text
                }
                
        except requests.exceptions.Timeout:
            logger.error("Base44 API timeout")
            return {
                "success": False,
                "error": "API request timed out"
            }
        except Exception as e:
            logger.error(f"Error creating prediction: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_prediction(self, subscriber_id: str, date: str) -> Optional[Dict]:
        """
        Get prediction for a subscriber on a specific date
        
        Args:
            subscriber_id: Base44 subscriber ID
            date: ISO date string
        
        Returns:
            Prediction data dict or None if not found
        """
        if not self._connected:
            logger.error("Base44 not configured")
            return None
        
        try:
            response = requests.get(
                f"{self.api_url}/v1/predictions/{subscriber_id}/{date}",
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"No prediction found for {subscriber_id} on {date}")
                return None
            else:
                logger.error(f"Failed to get prediction: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting prediction: {e}")
            return None
    
    def get_subscriber(self, subscriber_id: str) -> Optional[Dict]:
        """
        Get subscriber details from Base44
        
        Args:
            subscriber_id: Base44 subscriber ID
        
        Returns:
            Subscriber data dict or None if not found
        """
        if not self._connected:
            logger.error("Base44 not configured")
            return None
        
        try:
            response = requests.get(
                f"{self.api_url}/v1/subscribers/{subscriber_id}",
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.info(f"Subscriber {subscriber_id} not found")
                return None
            else:
                logger.error(f"Failed to get subscriber: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting subscriber: {e}")
            return None
    
    def list_active_subscribers(self) -> list:
        """
        Get list of all active subscribers
        
        Returns:
            List of subscriber dicts with active subscriptions
        """
        if not self._connected:
            logger.error("Base44 not configured")
            return []
        
        try:
            response = requests.get(
                f"{self.api_url}/v1/subscribers?status=active",
                headers=self._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('subscribers', [])
            else:
                logger.error(f"Failed to list subscribers: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing subscribers: {e}")
            return []
    
    def update_prediction_status(self, prediction_id: str, status: str, results: Optional[Dict] = None) -> bool:
        """
        Update prediction status after draw occurs
        
        Args:
            prediction_id: Base44 prediction ID
            status: Status string ("pending", "completed", "won", "lost")
            results: Optional results data with actual winning numbers
        
        Returns:
            True if update successful, False otherwise
        """
        if not self._connected:
            logger.error("Base44 not configured")
            return False
        
        try:
            payload = {"status": status}
            if results:
                payload["results"] = results
            
            response = requests.patch(
                f"{self.api_url}/v1/predictions/{prediction_id}",
                headers=self._get_headers(),
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Updated prediction {prediction_id} status to {status}")
                return True
            else:
                logger.error(f"Failed to update prediction: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating prediction: {e}")
            return False


# Singleton instance for easy import
_client = None

def get_base44_client() -> Base44Client:
    """Get or create Base44 client singleton"""
    global _client
    if _client is None:
        _client = Base44Client()
    return _client
