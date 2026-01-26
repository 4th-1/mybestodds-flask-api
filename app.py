"""
My Best Odds Flask API - Production Server
Supports: Cash3, Cash4, MegaMillions, Powerball, Cash4Life
Version: 3.7
"""

from flask import Flask, request, jsonify
from datetime import datetime
import os
import sys
import json
import subprocess
import tempfile

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
JACKPOT_SYSTEM = os.path.join(PROJECT_ROOT, 'jackpot_system_v3')
sys.path.insert(0, JACKPOT_SYSTEM)

app = Flask(__name__)

# Helper function to run prediction engine
def run_prediction_engine(subscriber_data, game, kit='BOOK3'):
    """
    Run the actual v3.7 prediction engine
    """
    try:
        # Create temporary subscriber config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(subscriber_data, f, indent=2)
            temp_config = f.name
        
        # Path to run_kit_v3.py
        run_kit_script = os.path.join(JACKPOT_SYSTEM, 'run_kit_v3.py')
        
        # Run the prediction engine
        result = subprocess.run(
            ['python', run_kit_script, temp_config, kit],
            capture_output=True,
            text=True,
            cwd=JACKPOT_SYSTEM,
            timeout=300  # 5 minute timeout
        )
        
        # Clean up temp file
        try:
            os.unlink(temp_config)
        except:
            pass
        
        if result.returncode == 0:
            return {
                'success': True,
                'output': result.stdout,
                'game': game,
                'kit': kit
            }
        else:
            return {
                'success': False,
                'error': result.stderr,
                'returncode': result.returncode
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Prediction engine timeout (exceeded 5 minutes)'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

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
        
        # Build subscriber configuration
        subscriber_config = {
            'name': subscriber_name,
            'dob': dob,
            'kit': kit,
            'games': [game],
            'active': True,
            'preferences': data.get('preferences', {}),
            'play_types': data.get('play_types', ['STRAIGHT', 'BOX', 'COMBO']),
            'prediction_date': data.get('prediction_date', datetime.utcnow().strftime('%Y-%m-%d'))
        }
        
        # Run the actual prediction engine
        result = run_prediction_engine(subscriber_config, game, kit)
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'subscriber': subscriber_name,
                'game': game,
                'kit': kit,
                'dob': dob,
                'prediction_date': subscriber_config['prediction_date'],
                'engine_output': result['output'],
                'message': 'Predictions generated successfully',
                'note': 'Check engine_output for detailed forecast data'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'error': 'Prediction engine failed',
                'details': result.get('error', 'Unknown error'),
                'subscriber': subscriber_name,
                'game': game
            }), 500
        
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


# Base44 Integration Endpoints
@app.route('/api/predictions/generate', methods=['POST'])
def generate_batch_predictions():
    ""\"Batch generate predictions for all active subscribers (Base44 webhook)""\"
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('api_server')
    
    logger.info(f"Received POST request to /api/predictions/generate")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Content-Type: {request.content_type}")
    
    try:
        data = request.get_json() or {}
        target_date = data.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        
        logger.info(f"Generating predictions for {target_date}")
        
        # Import Base44 integration
        sys.path.insert(0, PROJECT_ROOT)
        from base44_integration import get_active_subscribers_from_base44
        
        # Get active subscribers from Base44
        subscribers = get_active_subscribers_from_base44()
        
        if not subscribers:
            logger.warning("No active subscribers found in Base44")
            return jsonify({
                'status': 'success',
                'message': 'No active subscribers to process',
                'predictions': [],
                'date': target_date
            }), 200
        
        # Generate predictions for each subscriber
        results = {'success': [], 'failed': []}
        
        for sub in subscribers:
            try:
                subscriber_config = {
                    'name': sub.get('name', f"sub_{sub['id']}"),
                    'dob': sub.get('date_of_birth', '1980-01-01'),
                    'kit': sub.get('kit', 'BOOK3'),
                    'games': sub.get('games', ['cash3']),
                    'active': True,
                    'prediction_date': target_date
                }
                
                game = subscriber_config['games'][0] if subscriber_config['games'] else 'cash3'
                kit = subscriber_config['kit']
                
                logger.info(f"Generating prediction for {subscriber_config['name']} on {target_date}")
                
                result = run_prediction_engine(subscriber_config, game, kit)
                
                if result['success']:
                    results['success'].append({
                        'subscriber_id': sub['id'],
                        'name': subscriber_config['name'],
                        'game': game,
                        'kit': kit
                    })
                else:
                    results['failed'].append({
                        'subscriber_id': sub['id'],
                        'name': subscriber_config['name'],
                        'error': result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                logger.error(f"Failed to process subscriber {sub.get('id', 'unknown')}: {e}")
                results['failed'].append({
                    'subscriber_id': sub.get('id', 'unknown'),
                    'error': str(e)
                })
        
        logger.info(f"Generation complete: {len(results['success'])} success, {len(results['failed'])} failed")
        
        return jsonify({
            'status': 'success',
            'date': target_date,
            'total_subscribers': len(subscribers),
            'successful': len(results['success']),
            'failed': len(results['failed']),
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Batch generation error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/predictions/<subscriber_id>/<target_date>', methods=['GET'])
def get_subscriber_prediction(subscriber_id, target_date):
    ""\"Get prediction for specific subscriber and date""\"
    import logging
    logger = logging.getLogger('api_server')
    
    logger.info(f"Fetching prediction for {subscriber_id} on {target_date}")
    
    try:
        # Import Base44 integration
        sys.path.insert(0, PROJECT_ROOT)
        from base44_integration import get_subscriber_from_base44
        
        # Get subscriber from Base44
        subscriber = get_subscriber_from_base44(subscriber_id)
        
        if not subscriber:
            return jsonify({
                'error': 'Subscriber not found',
                'subscriber_id': subscriber_id
            }), 404
        
        # Build subscriber config
        subscriber_config = {
            'name': subscriber.get('name', f"sub_{subscriber_id}"),
            'dob': subscriber.get('date_of_birth', '1980-01-01'),
            'kit': subscriber.get('kit', 'BOOK3'),
            'games': subscriber.get('games', ['cash3']),
            'active': True,
            'prediction_date': target_date
        }
        
        game = subscriber_config['games'][0] if subscriber_config['games'] else 'cash3'
        kit = subscriber_config['kit']
        
        # Generate prediction
        result = run_prediction_engine(subscriber_config, game, kit)
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'subscriber_id': subscriber_id,
                'subscriber_name': subscriber_config['name'],
                'date': target_date,
                'game': game,
                'kit': kit,
                'prediction': result['output']
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'subscriber_id': subscriber_id,
                'error': result.get('error', 'Prediction failed')
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching prediction: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


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

