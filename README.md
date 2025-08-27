# Storm - Modern SaaS Platform

A full-stack SaaS application built with Python (FastAPI) backend and React (TypeScript) frontend. Storm provides developers with a modern platform to create, manage, and scale APIs with enterprise-grade security, real-time analytics, and seamless integrations.

## Features

### 🚀 Core Features
- **User Authentication & Authorization** - Secure JWT-based authentication with role-based access control
- **API Management** - Create, manage, and monitor API endpoints
- **Real-time Analytics** - Comprehensive usage analytics and performance monitoring
- **Subscription Management** - Integrated Stripe billing with multiple pricing tiers
- **Project Organization** - Organize APIs into projects for better management
- **API Key Management** - Generate and manage API keys with rate limiting
- **Usage Tracking** - Detailed usage statistics and quota management

### 🛡️ Security
- Password hashing with bcrypt
- JWT token authentication (access + refresh tokens)
- Rate limiting and API quotas
- CORS protection
- Input validation and sanitization
- Secure file upload handling

### 📊 Analytics & Monitoring
- Real-time usage dashboards
- API performance metrics
- Error tracking and reporting
- Usage trends and insights
- Export capabilities

### 💳 Billing & Subscriptions
- Stripe integration for payments
- Multiple subscription tiers (Free, Basic, Premium)
- Usage-based billing
- Subscription management
- Webhook handling for payment events

## Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **SQLAlchemy** - SQL toolkit and ORM
- **PostgreSQL** - Primary database
- **Redis** - Caching and session storage
- **Celery** - Background task processing
- **Alembic** - Database migrations
- **Stripe** - Payment processing
- **Pydantic** - Data validation
- **JWT** - Authentication tokens

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **React Query** - Data fetching and caching
- **Zustand** - State management
- **Axios** - HTTP client
- **Recharts** - Data visualization
- **Heroicons** - Icon library
- **React Hot Toast** - Notifications

### Development Tools
- **Vite** - Build tool and dev server
- **ESLint** - Code linting
- **Prettier** - Code formatting
- **Black** - Python code formatting
- **pytest** - Testing framework
- **mypy** - Static type checking

## Project Structure

```
Storm/
├── backend/
│   ├── app/
│   │   ├── routers/          # API route handlers
│   │   ├── models.py         # Database models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── auth.py          # Authentication utilities
│   │   ├── config.py        # Configuration settings
│   │   └── database.py      # Database connection
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   ├── alembic.ini         # Database migration config
│   └── .env.example        # Environment variables template
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── store/          # State management
│   │   ├── App.tsx         # Main app component
│   │   └── index.tsx       # Entry point
│   ├── public/             # Static assets
│   ├── package.json        # Node.js dependencies
│   └── tailwind.config.js  # Tailwind configuration
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- Redis 6+

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Storm
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Set up database**
   ```bash
   # Create PostgreSQL database
   createdb storm_db
   
   # Run migrations
   alembic upgrade head
   ```

6. **Start the backend server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the development server**
   ```bash
   npm start
   ```

4. **Build for production**
   ```bash
   npm run build
   ```

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost/storm_db

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Environment
ENVIRONMENT=development
DEBUG=true

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Redis
REDIS_URL=redis://localhost:6379/0

# File Storage
UPLOAD_DIR=uploads
MAX_FILE_SIZE=5242880
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif

# Pagination
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
```

## API Documentation

Once the backend is running, you can access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Deployment

### Backend Deployment

1. **Using Docker** (recommended)
   ```bash
   # Build and run with Docker Compose
   docker-compose up -d
   ```

2. **Manual deployment**
   - Set up PostgreSQL and Redis
   - Configure environment variables
   - Run database migrations
   - Start the application with a WSGI server like Gunicorn

### Frontend Deployment

1. **Build the application**
   ```bash
   cd frontend
   npm run build
   ```

2. **Deploy to static hosting**
   - Upload the `build` folder to your hosting provider
   - Configure your web server to serve the React app
   - Set up proper routing for SPA

## Testing

### Backend Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

### Frontend Tests
```bash
cd frontend

# Run tests
npm test

# Run tests with coverage
npm test -- --coverage
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, email support@storm-saas.com or join our Discord community.

## Roadmap

- [ ] GraphQL API support
- [ ] Webhooks management
- [ ] Advanced analytics dashboard
- [ ] Team collaboration features
- [ ] API versioning
- [ ] Custom domains
- [ ] SSO integration
- [ ] Mobile app

---

**Storm** - Built with ❤️ for developers
