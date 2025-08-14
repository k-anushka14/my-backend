# Fake News Detection Backend

A production-ready, AI-powered backend service for detecting fake news in Chrome extensions. Built with FastAPI, HuggingFace transformers, and Redis caching.

## 🚀 Features

- **AI-Powered Detection**: Uses HuggingFace `distilbert-base-uncased-finetuned-fake-news` model
- **Fact-Checking Integration**: Google Fact Check Tools API + Politifact fallback
- **High Performance**: Redis caching, async processing, rate limiting
- **Production Ready**: Docker support, health checks, comprehensive error handling
- **Security**: API key authentication, input sanitization, CORS protection

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chrome Ext    │    │   FastAPI       │    │   Redis Cache   │
│                 │───▶│   Backend       │───▶│                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   HuggingFace   │
                       │   AI Model      │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Google Fact     │
                       │ Check API       │
                       └─────────────────┘
```

## 📋 Requirements

- Python 3.9+
- Redis 6.0+
- 4GB+ RAM (for AI model)
- Docker & Docker Compose (recommended)

## 🛠️ Installation

### Option 1: Docker (Recommended)

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd fake-news-backend
   cp env.example .env
   ```

2. **Configure environment**:
   ```bash
   # Edit .env file with your settings
   API_KEY=your_secure_api_key_here
   CHROME_EXTENSION_ID=your_extension_id
   GOOGLE_FACT_CHECK_API_KEY=your_google_api_key
   ```

3. **Start services**:
   ```bash
   docker-compose up -d
   ```

4. **Verify deployment**:
   ```bash
   curl http://localhost:8000/health
   ```

### Option 2: Local Development

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Redis**:
   ```bash
   # macOS
   brew install redis && brew services start redis
   
   # Ubuntu/Debian
   sudo apt install redis-server && sudo systemctl start redis
   
   # Windows
   # Download Redis from https://redis.io/download
   ```

3. **Configure environment**:
   ```bash
   cp env.example .env
   # Edit .env with your settings
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Secure API key for authentication | `default_api_key` |
| `CHROME_EXTENSION_ID` | Your Chrome extension ID | `default_extension_id` |
| `REDIS_HOST` | Redis server hostname | `localhost` |
| `REDIS_PORT` | Redis server port | `6379` |
| `GOOGLE_FACT_CHECK_API_KEY` | Google Fact Check API key | None |
| `RATE_LIMIT_PER_MINUTE` | API rate limiting | `10` |
| `REQUEST_TIMEOUT_SECONDS` | Request timeout | `5` |

### API Key Setup

1. Generate a secure API key:
   ```bash
   openssl rand -hex 32
   ```

2. Add to your `.env` file:
   ```bash
   API_KEY=your_generated_key_here
   ```

3. Use in Chrome extension requests:
   ```javascript
   headers: {
     'X-API-Key': 'your_generated_key_here'
   }
   ```

## 📚 API Documentation

### Base URL
```
http://localhost:8000
```

### Authentication
All protected endpoints require the `X-API-Key` header:
```http
X-API-Key: your_api_key_here
```

### Endpoints

#### 1. Text Analysis
**POST** `/analyze`

Analyze text for fake news detection.

**Request Body**:
```json
{
  "text": "Your text to analyze here..."
}
```

**Response**:
```json
{
  "score": 75,
  "label": "suspicious",
  "reason": "pattern_detection:keyword_match:conspiracy",
  "model_confidence": 0.823,
  "patterns_detected": 2,
  "text_length": 156
}
```

#### 2. Fact-Checking
**GET** `/fact-check?query=your_query_here`

Perform fact-checking on a query.

**Response**:
```json
{
  "claims": [
    {
      "text": "COVID vaccine causes autism",
      "rating": "False",
      "url": "https://politifact.com/factchecks/2021/...",
      "reviewer": "PolitiFact",
      "source": "politifact_scraping"
    }
  ],
  "source": "politifact_scraping",
  "total_results": 1
}
```

#### 3. Health Check
**GET** `/health`

Check service health and status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15 10:30:00 UTC",
  "services": {
    "redis": "healthy",
    "ai_model": "healthy",
    "fact_check": {...}
  }
}
```

#### 4. Model Information
**GET** `/model/info`

Get AI model status and information.

#### 5. Cache Status
**GET** `/cache/status`

Get Redis cache statistics.

## 🔒 Security Features

- **Input Sanitization**: Prevents XSS and injection attacks
- **Rate Limiting**: 10 requests per minute per IP
- **API Key Authentication**: Secure endpoint protection
- **CORS Protection**: Restricted to Chrome extension origins
- **Request Validation**: Pydantic model validation
- **Error Handling**: Secure error messages in production

## 📊 Performance Features

- **Redis Caching**: 
  - Model predictions: 24 hours TTL
  - API responses: 1 hour TTL
- **Async Processing**: Concurrent request handling
- **Model Optimization**: ONNX runtime support
- **Connection Pooling**: Efficient HTTP client management

## 🧪 Testing

### Manual Testing

1. **Health Check**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Text Analysis** (with API key):
   ```bash
   curl -X POST "http://localhost:8000/analyze" \
        -H "X-API-Key: your_api_key" \
        -H "Content-Type: application/json" \
        -d '{"text": "This is a test message"}'
   ```

3. **Fact-Checking**:
   ```bash
   curl "http://localhost:8000/fact-check?query=COVID%20vaccine" \
        -H "X-API-Key: your_api_key"
   ```

### Load Testing

Use tools like Apache Bench or wrk:
```bash
# Install wrk
# macOS: brew install wrk
# Ubuntu: sudo apt install wrk

# Test with 100 requests, 10 concurrent
wrk -t10 -c10 -d30s -H "X-API-Key: your_api_key" \
    http://localhost:8000/health
```

## 🚀 Deployment

### Production Considerations

1. **Environment Variables**:
   - Use strong, unique API keys
   - Configure proper Redis credentials
   - Set appropriate CORS origins

2. **Monitoring**:
   - Enable health check endpoints
   - Monitor Redis memory usage
   - Track API response times

3. **Scaling**:
   - Use Redis cluster for high availability
   - Deploy multiple backend instances
   - Use load balancer for distribution

### Docker Production

```bash
# Build production image
docker build -t fake-news-backend:latest .

# Run with production settings
docker run -d \
  --name fake-news-backend \
  -p 8000:8000 \
  -e API_KEY=your_production_key \
  -e REDIS_HOST=your_redis_host \
  fake-news-backend:latest
```

## 🔍 Troubleshooting

### Common Issues

1. **Model Loading Fails**:
   - Check available memory (4GB+ required)
   - Verify internet connection for model download
   - Check disk space

2. **Redis Connection Issues**:
   - Verify Redis is running: `redis-cli ping`
   - Check Redis configuration in `.env`
   - Ensure Redis port is accessible

3. **Rate Limiting**:
   - Check rate limit configuration
   - Verify client IP detection
   - Monitor request frequency

### Logs

```bash
# Docker logs
docker-compose logs backend

# Follow logs
docker-compose logs -f backend

# Check specific service
docker logs fake-news-backend
```

## 📈 Monitoring

### Key Metrics

- **Response Time**: Target < 2 seconds
- **Cache Hit Rate**: Target > 80%
- **Model Load Time**: Target < 30 seconds
- **Error Rate**: Target < 1%

### Health Check Alerts

Monitor the `/health` endpoint for:
- Redis connectivity
- AI model status
- Fact-check service availability

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review API documentation
3. Open a GitHub issue
4. Check service health endpoints

---

**Built with ❤️ for combating misinformation**
