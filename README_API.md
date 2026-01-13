# My Best Odds Flask API
## Complete Flask API Project Structure

This directory contains the complete Flask API bridge connecting the Python prediction engine to the Base44 app.

## 📁 Project Structure

```
C:\MyBestOdds\
├── api_server.py              # Main Flask API server
├── base44_integration.py      # Base44 SDK wrapper
├── twilio_integration.py      # Twilio SMS client
├── .env                       # Environment configuration
├── requirements.txt           # Python dependencies
├── test_api_server.py         # API testing script
│
├── jackpot_system_v3/
│   └── run_kit_v3.py          # Prediction engine
│
└── data/
    └── subscribers/           # Subscriber configurations
        ├── BOOK3_TEST/
        ├── BOOK_TEST/
        └── BOSK_TEST/
```

## 🚀 Setup Instructions

### 1. Install Dependencies
```powershell
cd C:\MyBestOdds
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configure Environment Variables
Edit `.env` file with your credentials:
```env
BASE44_API_KEY=your_base44_api_key_here
BASE44_WORKSPACE_ID=your_workspace_id_here
BASE44_API_URL=https://app.base44.com/api/apps/your_workspace_id

TWILIO_ACCOUNT_SID=your_twilio_account_sid_here
TWILIO_AUTH_TOKEN=your_twilio_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
```

### 3. Run Flask API
```powershell
cd C:\MyBestOdds
.venv\Scripts\python.exe api_server.py
```

**Server will start on:**
- Local: http://127.0.0.1:5000
- Network: http://YOUR_IP:5000

## 📡 API Endpoints

### Health Check
```http
GET /health
```
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-13T12:00:00",
  "python_engine": "v3.7_recalibrated",
  "base44_connected": true,
  "twilio_connected": true
}
```

### Generate Batch Predictions
```http
POST /api/predictions/generate
Content-Type: application/json

{
  "date": "2026-01-13",
  "subscriber_ids": ["sub_123", "sub_456"]  // optional
}
```

**Response:**
```json
{
  "success": true,
  "generated": 15,
  "failed": 0,
  "predictions": [
    {
      "subscriber_id": "sub_123",
      "prediction_id": "pred_xyz",
      "games": ["Cash3", "Cash4", "MegaMillions"]
    }
  ]
}
```

### Generate Single Subscriber Prediction
```http
POST /api/predictions/generate/{subscriber_id}

{
  "date": "2026-01-13"
}
```

## 🔧 Core Components

### api_server.py (Main Flask App)
- Flask web server
- CORS configuration
- Prediction generation endpoints
- Integration with Base44 and Twilio

### base44_integration.py (Base44 SDK)
- `create_prediction()` - Push predictions to database
- `get_prediction()` - Query predictions
- `get_subscriber()` - Fetch subscriber details
- `list_active_subscribers()` - Get active users
- `update_prediction_status()` - Mark wins/losses

### twilio_integration.py (SMS Client)
- `send_sms()` - Basic SMS sending
- `send_prediction_alert()` - Daily prediction notifications
- `send_win_notification()` - Winning alerts
- `send_high_confidence_alert()` - 85%+ confidence alerts
- `send_draw_reminder()` - Pre-draw reminders

## 🧪 Testing

### Test Health Endpoint
```powershell
Invoke-RestMethod -Uri http://localhost:5000/health -Method GET
```

### Test Prediction Generation
```powershell
$body = @{ date = "2026-01-13" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:5000/api/predictions/generate -Method POST -Body $body -ContentType "application/json"
```

## 🌐 Production Deployment

### Option 1: ngrok (Development/Testing)
```powershell
.\ngrok.exe http 5000
```
Public URL will be shown (changes on restart with free tier)

### Option 2: Production Server (Recommended)
```powershell
gunicorn -w 4 -b 0.0.0.0:5000 api_server:app
```

### Option 3: Docker (Advanced)
Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "api_server:app"]
```

## 📦 Files to Copy for Deployment

**Essential Files:**
- `api_server.py`
- `base44_integration.py`
- `twilio_integration.py`
- `.env` (with your credentials)
- `requirements.txt`
- `run_kit_v3.py` (prediction engine)

**Optional:**
- `test_api_server.py` (testing)
- Subscriber configuration files

## 🔒 Security Notes

1. **Never commit .env file** - Contains sensitive credentials
2. **Use HTTPS in production** - Encrypt API traffic
3. **Rate limiting** - Implement request throttling
4. **API key rotation** - Regularly update credentials
5. **Input validation** - Sanitize all user inputs

## 📊 Monitoring

**Flask API Logs:**
```powershell
# View Flask console for real-time logs
INFO:__main__:Starting My Best Odds API Server on port 5000
INFO:__main__:Base44 connected: True
INFO:__main__:Twilio connected: True
```

**Base44 Database:**
- Check Prediction entity for new records
- Monitor subscriber status
- Track win/loss results

## 🆘 Troubleshooting

**Flask won't start:**
- Check Python virtual environment is activated
- Verify all dependencies installed: `pip list`
- Check port 5000 isn't already in use

**Base44 not connected:**
- Verify BASE44_API_KEY in .env file
- Check BASE44_WORKSPACE_ID matches your workspace
- Test API URL is accessible

**Twilio not connected:**
- Verify TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
- Check phone number format (+1234567890)
- Ensure Twilio account is active

**Predictions not generating:**
- Check subscriber config files exist
- Verify run_kit_v3.py path is correct
- Check Flask logs for error messages

## 📚 Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Base44 API Docs](https://docs.base44.com)
- [Twilio SMS Docs](https://www.twilio.com/docs/sms)
- [TWILIO_SETUP_GUIDE.md](TWILIO_SETUP_GUIDE.md) - SMS setup guide
- [API_README.md](API_README.md) - Original integration guide

## 📞 Support

**Email:** jdsmith0822@gmail.com  
**System:** My Best Odds v3.7 (Recalibrated)  
**Last Updated:** January 13, 2026
