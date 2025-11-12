# 🚀 Crypto Trading Dashboard

A real-time cryptocurrency trading dashboard with live price updates, alerts, and comprehensive analytics for 2000+ USDT trading pairs.

---

## 🚀 Deployment

This repository no longer contains provider-specific deployment automation.
We removed AWS/ECR-specific scripts and docs to keep the repository provider-agnostic.

For deployment instructions and provider-specific notes, see `./docs/DEPLOYMENT_GUIDE.md`.

If you want a ready-made script for a provider (Hetzner, DigitalOcean, etc.), I can add one tailored to your target—tell me which provider you prefer.

---

## 📋 Features

### Core Features
- **Real-Time Data**: Live cryptocurrency prices via Binance WebSocket
- **2000+ Trading Pairs**: All USDT pairs with real-time updates
- **Advanced Metrics**: RSI, price changes (1m, 2m, 3m, 5m, 10m, 15m, 60m), volume analysis
- **Smart Alerts**: Price, volume, RSI, pump/dump detection with Email & Telegram notifications
- **Telegram Integration**: Real-time notifications via Telegram bot
- **Multi-Exchange Links**: Quick access to Binance, Bybit, MEXC, KuCoin, TradingView
- **Plan Management**: Free, Basic ($9.99), and Enterprise ($29.99) subscription tiers
- **Auto Logout**: 30-minute inactivity timeout for security
- **Plan Expiration**: Automatic notifications at 7, 3, and 1 days before expiry

### Alert Types
1. **Price Movement**: Track percentage changes over time
2. **Volume Change**: Monitor trading volume spikes
3. **New Coin Listing**: Get notified of new trading pairs
4. **RSI Overbought** (>70): Identify potentially oversold coins
5. **RSI Oversold** (<30): Find potentially undervalued coins
6. **Pump Alert**: Detect rapid price increases (>5% in 1m)
7. **Dump Alert**: Detect rapid price drops (<-5% in 1m)

### Subscription Tiers
- **Free**: Limited access, basic features
- **Basic ($9.99/month)**: Up to 10 alerts, email notifications, Telegram integration, RSI indicators
- **Enterprise ($29.99/month)**: Unlimited alerts, advanced indicators, custom conditions, priority support

---

### Frontend
- **Framework**: Next.js 15.5.2 (React 19.1.0)
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS 4
- **UI Components**: Radix UI, Lucide Icons
- **State Management**: React Query
- **Real-time**: WebSocket connections
- **Authentication**: Firebase Auth

### Backend
- **Framework**: Django 5.2.6
- **Language**: Python 3.12
- **API**: Django REST Framework 3.16.1
- **WebSocket**: Django Channels 4.3.1
- **Task Queue**: Celery 5.3.4
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Connection Pool**: PgBouncer

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Load Balancer**: Nginx
- **Data Source**: Binance WebSocket API
- **Payments**: Stripe
- **Notifications**: Telegram Bot API

## 📦 Project Structure

```
.
├── frontend/               # Next.js frontend application
│   ├── src/
│   │   ├── app/           # App router pages
│   │   ├── components/    # Reusable React components
│   │   ├── lib/           # Utilities and helpers
│   │   └── styles/        # Global styles
│   ├── public/            # Static assets
│   └── package.json
│
├── backend/               # Django backend application
│   ├── core/             # Main app
│   │   ├── models.py     # Database models
│   │   ├── views.py      # API endpoints
│   │   ├── tasks.py      # Celery background tasks
│   │   ├── consumers.py  # WebSocket consumers
│   │   └── management/   # Custom commands
│   ├── project_config/   # Django settings
│   ├── requirements.txt  # Python dependencies
│   └── Dockerfile
│
├── nginx/                # Nginx configuration
├── pgbouncer/            # Connection pooler config
├── db/                   # Database initialization
├── docs/                 # Documentation
│   ├── README.md         # This file
│   └── DEPLOYMENT_GUIDE.md
├── docker-compose.yml    # Multi-container setup
└── package.json          # Root package info
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local development)
- Python 3.12+ (for local development)

### Environment Setup

1. **Clone the repository**
```bash
git clone https://github.com/your-repo/crypto-trading-dashboard.git
cd crypto-trading-dashboard
```

2. **Set up environment variables**

Backend (.env):
```bash
cd backend
cp .env.example .env
# Edit .env with your configuration
```

Frontend (.env.local):
```bash
cd frontend
cp .env.example .env.local
# Edit .env.local with your configuration
```

3. **Start with Docker Compose**
```bash
docker-compose up --build
```

Services will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **Admin Panel**: http://localhost:8080/admin/

---

## 🔧 Configuration

### Key Environment Variables

**Backend (.env):**
```env
DATABASE_URL=postgresql://user:pass@postgres:5432/crypto_db
REDIS_URL=redis://redis:6379/0
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
STRIPE_SECRET_KEY=your_stripe_secret_key
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

**Frontend (.env.local):**
```env
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=your_stripe_public_key
```

---

## 📊 Architecture

### System Overview

```
### System Overview

```
Users → Nginx → [Frontend + Backend]
                       ↓
           ┌───────────┴────────────┐
           │                        │
    PgBouncer → PostgreSQL    Redis (Cache)
           │                        │
           ↓                        ↓
    [Celery Workers]        [Task Queue]
           ↓
   Binance WebSocket API
```

### Docker Services
- **postgres**: PostgreSQL 15 database
- **pgbouncer**: Connection pooler (100 connections → 2000 clients)
- **redis**: Cache and message broker
- **backend1**: Django REST API
- **celery-worker**: Background task processor
- **celery-beat**: Task scheduler (runs daily: alerts, plan expiration checks)
- **data-worker**: Binance WebSocket data consumer
- **calc-worker**: Distributed metric calculations
- **nginx**: Load balancer and reverse proxy
- **frontend**: Next.js application

---

## 🔐 Security

- JWT authentication with access/refresh tokens
- 30-minute inactivity timeout with warning
- CORS protection
- Rate limiting (100 req/s per IP)
- SQL injection protection (Django ORM)
- XSS protection
- CSRF tokens
- Security headers (CSP, HSTS, X-Frame-Options)
- Environment variable secrets

---

## 📈 Performance Features

- **Database Indexing**: Optimized queries on symbol, price, volume, timestamps
- **Redis Caching**: 60s TTL for API responses
- **Connection Pooling**: PgBouncer for efficient database connections
- **Load Balancing**: Nginx round-robin across backend replicas
- **Lazy Loading**: Frontend loads 50 rows at a time
- **WebSocket**: Real-time updates without polling
- **Celery**: Distributed task processing

---
```

## 🔧 Configuration

### Key Environment Variables

**Backend:**
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis cache URL
- `CELERY_BROKER_URL`: Celery broker URL
- `BINANCE_API_KEY`: Binance API credentials
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `STRIPE_SECRET_KEY`: Stripe payment key
- `FIREBASE_PRIVATE_KEY`: Firebase auth credentials

**Frontend:**
- `NEXT_PUBLIC_API_URL`: Backend API URL
- `NEXT_PUBLIC_WS_URL`: WebSocket URL
- `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`: Stripe public key
- `NEXT_PUBLIC_FIREBASE_CONFIG`: Firebase config

### Docker Compose Services

- `postgres`: PostgreSQL database
- `pgbouncer`: Connection pooler
- `redis`: Cache and message broker
- `backend1`, `backend2`: Django app replicas
- `celery-worker`: Background task processor
- `celery-beat`: Task scheduler
- `calc-worker-1-4`: Calculation workers
- `data-worker`: Binance WebSocket consumer
- `nginx`: Load balancer
- `frontend`: Next.js app

## 📚 API Documentation

### Authentication
All API endpoints (except `/api/register/` and `/api/login/`) require authentication:
```
Authorization: Bearer <access_token>
```

### Main Endpoints

#### User Management
- `POST /api/register/` - Create new user account
- `POST /api/login/` - Authenticate user
- `GET /api/user-info/` - Get current user details
- `PATCH /api/update-profile/` - Update user profile

#### Crypto Data
- `GET /api/crypto-data/` - Get cryptocurrency data (paginated, sortable)
- `GET /api/exchanges/` - Get available exchanges
- `POST /api/refresh-data/` - Trigger data refresh

#### Alerts
- `GET /api/alerts/` - List user alerts
- `POST /api/alerts/` - Create new alert
- `DELETE /api/alerts/<id>/` - Delete alert

#### Telegram
- `GET /api/telegram-status/` - Check Telegram connection
- `GET /api/telegram-connect/` - Get connection URL
- `POST /api/telegram-disconnect/` - Disconnect Telegram
- `POST /api/telegram-test-alert/` - Send test alert

#### Payments
- `POST /api/create-checkout-session/` - Create Stripe session
- `POST /api/webhook/` - Stripe webhook handler
- `GET /api/payment-history/` - Get payment history

### WebSocket Endpoints

Connect to: `ws://localhost:8080/ws/crypto/`

**Messages Received:**
```json
{
  "type": "price_update",
  "data": {
    "symbol": "BTCUSDT",
    "last_price": 45000.50,
    "price_change_percent_24h": 2.5,
    ...
  }
}
```

## 🔐 Security

- HTTPS/TLS encryption
- JWT authentication
- CORS protection
- Rate limiting (100 req/s per IP)
- SQL injection protection (ORM)
- XSS protection
- CSRF tokens
- Security headers (CSP, HSTS, X-Frame-Options)
- Input validation and sanitization
- Environment variable secrets

## 🧪 Testing

### Run Tests
```bash
# Backend tests
cd backend
python manage.py test

# Frontend tests
cd frontend
npm test
```

## 📈 Performance

### Optimizations
- **Database**: Indexes on symbol, price, volume, timestamps
- **Caching**: Redis with 60s TTL for API responses
- **Connection Pooling**: PgBouncer (100 DB connections → 2000 clients)
- **Load Balancing**: Nginx round-robin across backend replicas
- **Lazy Loading**: Frontend loads 50 rows at a time
- **WebSocket**: Real-time updates without polling
- **Celery**: Distributed task processing (8 workers)

### Benchmarks
- **Initial Load**: 2-3 seconds for 2000+ symbols
- **Real-time Updates**: <100ms latency
- **API Response**: <200ms average
- **Concurrent Users**: Tested up to 1000 users
- **Database Queries**: <50ms average

## 🐛 Troubleshooting

### Common Issues

**Database connection errors:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check connection
docker-compose exec postgres pg_isready
```

**Redis connection errors:**
```bash
# Test Redis
docker-compose exec redis redis-cli ping
```

**WebSocket disconnections:**
- Check firewall rules
- Verify nginx timeout settings
- Check Binance API status

**Missing data:**
```bash
# Trigger manual refresh
curl -X POST http://localhost:8080/api/refresh-data/
```

## 📖 Documentation

- [Deployment Guide](./docs/DEPLOYMENT_GUIDE.md) - Complete production deployment instructions
- [API Documentation](./docs/API.md) - Detailed API reference
- [Architecture](./docs/ARCHITECTURE.md) - System architecture overview

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is proprietary and confidential.

## 👨‍💻 Authors

- **Your Name** - *Initial work*

## 🙏 Acknowledgments

- Binance for cryptocurrency data API
- Django & Next.js communities
- Open source contributors

## 📞 Support

For support, email support@yourdomain.com or open an issue on GitHub.

---

**Built with ❤️ for crypto traders**
# Test
# Test auto-deploy
