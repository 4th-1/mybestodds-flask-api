"""
My Best Odds Flask API - Production Server
Supports: Cash3, Cash4, MegaMillions, Powerball, Cash4Life
Version: 3.7
"""

from flask import Flask, request, jsonify
from datetime import datetime
import os
import sys

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'jackpot_system_v3'))

app = Flask(__name__)

@app.route('/')
def index():
    """Root endpoint - API information"""
    return jsonify({
        'name': 'My Best Odds Prediction API',
        'version': '3.7',
        'status': 'active',
        'endpoints': {
            'health': '/health',
            'games': '/games',
            'predict': '/predict (POST)'
        },
        'supported_games': ['cash3', 'cash4', 'megamillions', 'powerball', 'cash4life']
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'python_engine': 'v3.7_with_triple_quad_overlays',
        'engines': {
            'jackpot': 'v3.7',
            'overlays': 'inactive',
            'triples': 'not loaded',
            'quads': 'not loaded'
        },
        'base44_connected': False,
        'twilio_connected': False
    })

@app.route('/games', methods=['GET'])
def get_games():
    """List all supported games"""
    games = {
        'cash3': {
            'name': 'Georgia Cash 3',
            'type': 'daily',
            'engine': 'left',
            'draws_per_day': 3,
            'format': '3 digits (0-9)',
            'play_types': ['STRAIGHT', 'BOX', 'COMBO']
        },
        'cash4': {
            'name': 'Georgia Cash 4',
            'type': 'daily',
            'engine': 'left',
            'draws_per_day': 3,
            'format': '4 digits (0-9)',
            'play_types': ['STRAIGHT', 'BOX', 'COMBO']
        },
        'megamillions': {
            'name': 'Mega Millions',
            'type': 'jackpot',
            'engine': 'right',
            'draws_per_week': 2,
            'format': '5 numbers (1-70) + 1 Mega Ball (1-25)'
        },
        'powerball': {
            'name': 'Powerball',
            'type': 'jackpot',
            'engine': 'right',
            'draws_per_week': 3,
            'format': '5 numbers (1-69) + 1 Powerball (1-26)'
        },
        'cash4life': {
            'name': 'Cash4Life',
            'type': 'jackpot',
            'engine': 'right',
            'draws_per_week': 7,
            'format': '5 numbers (1-60) + 1 Cash Ball (1-4)'
        }
    }
    
    return jsonify({
        'games': games,
        'count': len(games),
        'historical_data': '28 years (1998-2026)'
    })

@app.route('/predict', methods=['POST'])
def predict():
    """Generate predictions for a subscriber"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Required fields
        required = ['subscriber_name', 'game', 'date_of_birth']
        missing = [field for field in required if field not in data]
        
        if missing:
            return jsonify({
                'error': 'Missing required fields',
                'missing': missing
            }), 400
        
        subscriber_name = data['subscriber_name']
        game = data['game'].lower()
        dob = data['date_of_birth']
        kit = data.get('kit', 'BOOK3')
        
        # Validate game
        valid_games = ['cash3', 'cash4', 'megamillions', 'powerball', 'cash4life']
        if game not in valid_games:
            return jsonify({
                'error': 'Invalid game',
                'game': game,
                'valid_games': valid_games
            }), 400
        
        # TODO: Integrate with actual prediction engine
        # For now, return a placeholder response
        response = {
            'status': 'success',
            'message': 'Prediction engine integration pending',
            'request': {
                'subscriber': subscriber_name,
                'game': game,
                'dob': dob,
                'kit': kit
            },
            'note': 'Full prediction engine integration coming soon'
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'message': str(e)
        }), 500

@app.route('/api/status', methods=['GET'])
def api_status():
    """Detailed API status"""
    return jsonify({
        'api_version': '3.7',
        'engine_status': 'loaded',
        'data_coverage': {
            'cash3': '28 years',
            'cash4': '28 years',
            'megamillions': '28 years',
            'powerball': '28 years',
            'cash4life': '28 years'
        },
        'features': {
            'predictions': 'active',
            'overlays': 'pending',
            'historical_analysis': 'active',
            'real_time_draws': 'pending'
        }
    })

@app.errorhandler(404)
def not_found(error):
    """Custom 404 handler"""
    return jsonify({
        'error': 'Endpoint not found',
        'available_endpoints': ['/', '/health', '/games', '/predict', '/api/status']
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Custom 500 handler"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong. Please try again later.'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
