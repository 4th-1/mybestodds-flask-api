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
    Run the v3.7 prediction engine and parse the generated JSON output files
    """
    try:
        # Create temporary subscriber config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(subscriber_data, f, indent=2)
            temp_config = f.name

        # Extract initials for output folder name
        name = subscriber_data.get('name', 'Unknown')
        initials = ''.join([part[0].upper() for part in name.split() if part])
        coverage_start = subscriber_data.get('coverage_start', '2026-01-31')
        coverage_end = subscriber_data.get('coverage_end', '2026-02-28')
        
        # Expected output directory path
        output_folder = f"{kit}_{initials}_{coverage_start}_to_{coverage_end}"
        output_path = os.path.join(JACKPOT_SYSTEM, "outputs", output_folder)

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
            # Try to read the generated summary.json file
            summary_file = os.path.join(output_path, "summary.json")
            
            predictions = []
            if os.path.exists(summary_file):
                try:
                    with open(summary_file, 'r') as f:
                        summary_data = json.load(f)
                    
                    # Extract predictions from summary
                    days = summary_data.get('days', [])
                    for day in days:
                        date = day.get('date')
                        picks = day.get('picks', [])
                        
                        for pick in picks:
                            predictions.append({
                                'date': date,
                                'game': pick.get('game', game),
                                'session': pick.get('session', ''),
                                'numbers': pick.get('combo', ''),
                                'confidence': pick.get('confidence', 0.0),
                                'band': pick.get('band', 'UNKNOWN'),
                                'odds': pick.get('odds', 'N/A'),
                                'play_type': pick.get('play_type', 'STRAIGHT')
                            })
                    
                    return {
                        'success': True,
                        'predictions': predictions,
                        'summary_path': summary_file,
                        'output_folder': output_path,
                        'logs': result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,  # Last 500 chars
                        'game': game,
                        'kit': kit
                    }
                except Exception as e:
                    # If JSON parsing fails, fall back to logs
                    return {
                        'success': True,
                        'output': result.stdout,
                        'predictions': [],
                        'warning': f'Could not parse summary.json: {str(e)}',
                        'game': game,
                        'kit': kit
                    }
            else:
                # summary.json doesn't exist, return logs
                return {
                    'success': True,
                    'output': result.stdout,
                    'predictions': [],
                    'warning': f'summary.json not found at {summary_file}',
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
        # Extract coverage_start from request, default to today
        from datetime import timedelta
        coverage_start = data.get('coverage_start', datetime.utcnow().strftime('%Y-%m-%d'))
        
        # Calculate coverage_end (30 days from coverage_start)
        start_dt = datetime.strptime(coverage_start, '%Y-%m-%d')
        end_dt = start_dt + timedelta(days=30)
        coverage_end = end_dt.strftime('%Y-%m-%d')
        
        subscriber_config = {
            'name': subscriber_name,
            'dob': dob,
            'kit': kit,
            'games': [game],
            'active': True,
            'preferences': data.get('preferences', {}),
            'play_types': data.get('play_types', ['STRAIGHT', 'BOX', 'COMBO']),
            'prediction_date': data.get('prediction_date', datetime.utcnow().strftime('%Y-%m-%d')),
            'coverage_start': coverage_start,
            'coverage_end': coverage_end
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
    """Batch generate predictions for all active subscribers (Base44 webhook)"""
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
                # Extract coverage_start from subscriber data, default to today
                coverage_start = sub.get('coverage_start', datetime.utcnow().strftime('%Y-%m-%d'))
                
                # Calculate coverage_end (30 days from coverage_start)
                from datetime import timedelta
                start_dt = datetime.strptime(coverage_start, '%Y-%m-%d')
                end_dt = start_dt + timedelta(days=30)
                coverage_end = end_dt.strftime('%Y-%m-%d')
                
                subscriber_config = {
                    'name': sub.get('name', f"sub_{sub['id']}"),
                    'dob': sub.get('date_of_birth', '1980-01-01'),
                    'kit': sub.get('kit', 'BOOK3'),
                    'games': sub.get('games', ['cash3']),
                    'active': True,
                    'prediction_date': target_date,
                    'coverage_start': coverage_start,
                    'coverage_end': coverage_end
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


@app.route('/api/predictions/generate/<subscriber_id>', methods=['POST'])
def generate_single_prediction(subscriber_id):
    """Generate prediction for a specific subscriber (Base44 UI trigger)"""
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('api_server')
    
    logger.info(f"Generating prediction for {subscriber_id} on 2026-01-26")
    
    try:
        data = request.get_json() or {}
        target_date = data.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        
        # Import Base44 integration
        sys.path.insert(0, PROJECT_ROOT)
        from base44_integration import get_subscriber_from_base44
        
        logger.info(f"Subscriber {subscriber_id} not in local configs - using inline data from webhook")
        
        # Try to get subscriber from Base44
        subscriber = get_subscriber_from_base44(subscriber_id)
        
        # Extract coverage_start from request, default to today
        coverage_start = data.get('coverage_start', datetime.utcnow().strftime('%Y-%m-%d'))
        
        # Calculate coverage_end (30 days from coverage_start)
        from datetime import timedelta
        start_dt = datetime.strptime(coverage_start, '%Y-%m-%d')
        end_dt = start_dt + timedelta(days=30)
        coverage_end = end_dt.strftime('%Y-%m-%d')
        
        if not subscriber:
            # If not in Base44, use inline data from request
            subscriber_config = {
                'name': data.get('name', subscriber_id),
                'dob': data.get('date_of_birth', data.get('dob', '1980-01-01')),
                'kit': data.get('kit', 'BOOK3'),
                'games': data.get('games', ['cash3']),
                'active': True,
                'prediction_date': target_date,
                'coverage_start': coverage_start,
                'coverage_end': coverage_end
            }
            logger.info(f"Generating predictions from inline data: {subscriber_config['name']}, DOB: {subscriber_config['dob']}, Kit: {subscriber_config['kit']}, Coverage: {coverage_start} to {coverage_end}")
        else:
            subscriber_config = {
                'name': subscriber.get('name', subscriber_id),
                'dob': subscriber.get('date_of_birth', '1980-01-01'),
                'kit': subscriber.get('kit', 'BOOK3'),
                'games': subscriber.get('games', ['cash3']),
                'active': True,
                'prediction_date': target_date,
                'coverage_start': coverage_start,
                'coverage_end': coverage_end
            }
        
        game = subscriber_config['games'][0] if subscriber_config['games'] else 'cash3'
        kit = subscriber_config['kit']
        
        logger.info(f"Running: /app/.venv/bin/python /app/jackpot_system_v3/run_kit_v3.py tmp{subscriber_id}.json {kit}")
        
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
            logger.error(f"Prediction failed: {result.get('error', 'Unknown error')}")
            return jsonify({
                'status': 'error',
                'subscriber_id': subscriber_id,
                'error': result.get('error', 'Prediction failed')
            }), 500
            
    except Exception as e:
        logger.error(f"Error generating prediction: {e}")
        return jsonify({
            'status': 'error',
            'subscriber_id': subscriber_id,
            'error': str(e)
        }), 500

@app.route('/api/predictions/<subscriber_id>/<target_date>', methods=['GET'])
def get_subscriber_prediction(subscriber_id, target_date):
    """Get prediction for specific subscriber and date"""
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

