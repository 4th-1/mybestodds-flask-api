# My Best Odds - Flask API

Flask API bridge connecting Python lottery prediction engine (v3.7 recalibrated) to Base44 app with integrated SMS notifications.

## 🎯 Overview

This API bridges a sophisticated Python-based lottery prediction engine with a React/Base44 frontend application. It handles automated daily prediction generation, database synchronization, and subscriber notifications via SMS.

## ✨ Features

- **Prediction Engine Integration**: v3.7 recalibrated with 2026 lottery data
- **Base44 Database Sync**: Automatic prediction storage and retrieval
- **SMS Notifications**: Twilio integration for real-time alerts
- **Multi-Game Support**: Cash3, Cash4, MegaMillions, Powerball, Cash4Life
- **Automated Scheduling**: Daily 5:30am prediction generation
- **RESTful API**: Clean endpoints for frontend integration

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Base44 account with API credentials
- Twilio account (optional, for SMS)
- ngrok (for development tunneling)

### Installation

```bash
# Clone repository
git clone https://github.com/4th-1/mybestodds-flask-api.git
cd mybestodds-flask-api

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

Create `.env` file with:
```env
BASE44_API_KEY=your_api_key_here
BASE44_WORKSPACE_ID=your_workspace_id
BASE44_API_URL=https://app.base44.com/api/apps/your_workspace

TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=+1234567890

FLASK_ENV=development
PORT=5000
```

### Run

```bash
# Start Flask API
python api_server.py

# Server runs on http://localhost:5000
```

## 📡 API Endpoints

### Health Check
```http
GET /health
```

### Generate Predictions
```http
POST /api/predictions/generate
Content-Type: application/json

{
  "date": "2026-01-13",
  "subscriber_ids": ["sub_123"]  // optional
}
```

### Single Subscriber
```http
POST /api/predictions/generate/{subscriber_id}
```

## 🏗️ Architecture

```
Flask API (api_server.py)
├── Base44 Integration (base44_integration.py)
│   ├── create_prediction()
│   ├── get_prediction()
│   └── update_prediction_status()
├── Twilio Integration (twilio_integration.py)
│   ├── send_prediction_alert()
│   ├── send_win_notification()
│   └── send_high_confidence_alert()
└── Prediction Engine (run_kit_v3.py)
    └── Multi-engine scoring system
```

## 📚 Documentation

- [Complete API Documentation](README_API.md)
- [Twilio SMS Setup Guide](TWILIO_SETUP_GUIDE.md)
- [Prediction Engine Details](API_README.md)

## 🔒 Security

- Never commit `.env` file
- Use environment variables for credentials
- Enable HTTPS in production
- Implement rate limiting
- Rotate API keys regularly

## 🧪 Testing

```bash
# Test health endpoint
curl http://localhost:5000/health

# Test prediction generation
curl -X POST http://localhost:5000/api/predictions/generate \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-01-13"}'
```

## 📦 Dependencies

- Flask 3.0.0 - Web framework
- Requests 2.31.0 - HTTP client
- Twilio 9.9.1 - SMS integration
- python-dotenv 1.0.0 - Environment variables
- pandas, numpy - Data processing

## 🚢 Production Deployment

```bash
# Using Gunicorn (recommended)
gunicorn -w 4 -b 0.0.0.0:5000 api_server:app

# Or with Docker
docker build -t mybestodds-api .
docker run -p 5000:5000 --env-file .env mybestodds-api
```

## 📞 Support

**Email:** jdsmith0822@gmail.com  
**System:** My Best Odds v3.7 (Recalibrated)  
**Last Updated:** January 13, 2026

## 📄 License

Proprietary - All Rights Reserved

---

Built with ❤️ for My Best Odds subscribers
