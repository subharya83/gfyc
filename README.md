# County Migration Assistant

## Overview

The **County Migration Assistant** is a comprehensive web application designed to help users identify optimal US counties for relocation based on personalized preferences. By analyzing [multiple factors](./Factors.md) including economic indicators, lifestyle metrics, quality of life measures, and demographic characteristics, the application provides data-driven, tailored recommendations to simplify relocation decisions.

This project integrates both **event-driven migration factors** (pandemics, natural disasters, economic disruptions) and **underlying structural mobility factors** (economic opportunity, lifestyle preferences, demographics) to create a holistic tool for migration analysis. Data is automatically collected from publicly available government APIs on a periodic basis, as documented [here](./Datasources.md).

---

## Key Features

### 1. Intelligent Preference Collection
- **Interactive questionnaire** with intuitive slider-based inputs
- Covers multiple dimensions:
  - **Economic factors**: Job opportunities, cost of living, income potential, tax burden
  - **Lifestyle factors**: Climate preferences, urban/rural preference, recreational opportunities, cultural amenities
  - **Demographic factors**: Family considerations, retirement planning, education quality, healthcare access
  - **Risk factors**: Natural disaster exposure, crime rates, environmental concerns
- Weighted importance system allowing users to prioritize what matters most
- Smart defaults based on demographic profiles

### 2. Advanced County Matching Algorithm
- **Multi-factor scoring system** that processes user preferences against comprehensive county data
- Considers diverse data points:
  - **Economic indicators**: Median income, unemployment rates, wage growth trends, cost of living index
  - **Quality of life metrics**: Healthcare rankings, education quality scores, air quality index
  - **Environmental factors**: Climate patterns, natural disaster risk assessments, pollution levels
  - **Social indicators**: Crime statistics, demographic diversity, community engagement
- **Machine learning-powered** recommendations that improve with user feedback
- Explainable results showing why each county was recommended

### 3. Interactive Results Dashboard
- **Ranked recommendations** with detailed county profiles
- **Comprehensive insights** for each county:
  - Key statistics with data visualization
  - Pros and cons analysis
  - Cost of living breakdowns
  - Interactive maps showing geographic context
  - Historical trends and projections
- **Comparison tools**:
  - Side-by-side county comparisons
  - Custom metric selection
  - Export to PDF/CSV for offline analysis
- **Exploration features**:
  - Filter and refine results
  - Save favorites for later review
  - Share recommendations via unique links

### 4. User Account Management
- **Secure authentication** with email verification
- **Profile management**:
  - Save multiple preference sets (e.g., "retirement", "career change", "family relocation")
  - History of past searches and results
  - Update preferences and rerun analysis
- **Personalization**:
  - Saved favorite counties
  - Notes and annotations
  - Progress tracking

### 5. Responsive, Accessible Design
- **Mobile-first approach** ensuring seamless experience across all devices
- **WCAG 2.1 AA compliant** for accessibility
- **Progressive Web App (PWA)** capabilities for offline access
- **Dark mode** support

---

## Technical Architecture

### System Architecture Overview

```
┌─────────────────┐
│   React SPA     │ ◄─── User Interface Layer
│  (Frontend)     │
└────────┬────────┘
         │ HTTPS/REST
         ▼
┌─────────────────┐
│   Express API   │ ◄─── Application Layer
│   (Backend)     │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────┐
│PostgreSQL│ │  Python  │ ◄─── Data & Algorithm Layer
│    DB    │ │ ML Engine│
└─────────┘ └──────────┘
         │
         ▼
┌─────────────────┐
│  External APIs  │ ◄─── Data Collection Layer
│ (Census, BLS,   │
│  NOAA, etc.)    │
└─────────────────┘
```

### Frontend Stack

**Framework & Libraries:**
- **React 18+** - Component-based UI development
- **TypeScript** - Type-safe JavaScript
- **Next.js** (optional) - Server-side rendering and routing
- **State Management**: Redux Toolkit or Zustand
- **UI Components**: 
  - Material-UI (MUI) or shadcn/ui
  - Tailwind CSS for utility-first styling
- **Data Visualization**:
  - Recharts or Chart.js for statistical graphs
  - Leaflet.js or Mapbox GL for interactive maps
- **Form Handling**: React Hook Form with Zod validation
- **HTTP Client**: Axios or TanStack Query (React Query)

**Key Features:**
- Server-side rendering for SEO
- Code splitting and lazy loading
- Progressive Web App capabilities
- Responsive grid system
- Optimistic UI updates

### Backend Stack

**Framework & Components:**
- **Node.js 18+** with **Express.js** - API server
- **TypeScript** - Type-safe backend code
- **PostgreSQL 15+** - Primary database
  - Connection pooling with pg-pool
  - Query optimization with indexes
  - Full-text search capabilities
- **Redis** - Caching layer for improved performance
- **Python 3.11+** - ML and data processing
  - FastAPI for ML model serving
  - scikit-learn for recommendation algorithm
  - pandas for data manipulation
  - NumPy for numerical computations

**API Design:**
- RESTful API architecture
- JWT-based authentication
- Rate limiting and request throttling
- API versioning
- Comprehensive error handling
- OpenAPI/Swagger documentation

**Security Measures:**
- HTTPS/TLS encryption
- Helmet.js for security headers
- CORS configuration
- SQL injection prevention
- XSS protection
- CSRF tokens
- Input validation and sanitization
- Secure password hashing (bcrypt)

### Database Schema

**Core Tables:**
- `users` - User accounts and authentication
- `user_preferences` - Saved preference sets
- `counties` - County reference data
- `census_data` - Demographic and economic data
- `employment_data` - BLS employment statistics
- `housing_data` - Real estate metrics
- `climate_data` - Weather and climate information
- `economic_data` - Additional economic indicators
- `recommendations` - Cached recommendation results
- `user_searches` - Search history and analytics

**Performance Optimizations:**
- Compound indexes on frequently queried columns
- Materialized views for complex aggregations
- Partitioning for large historical tables
- Connection pooling
- Query result caching

### Matching Algorithm

**Approach:**
- **Weighted scoring model** combining multiple factors
- **Normalization** of all metrics to 0-100 scale
- **User preference weighting** applied to each factor
- **Composite score calculation** for ranking
- **Outlier detection** to filter unrealistic results

**Algorithm Components:**

1. **Data Preprocessing**:
   - Handle missing values
   - Normalize metrics across different scales
   - Calculate composite indices

2. **Scoring Engine**:
   - Apply user preference weights
   - Calculate factor scores
   - Aggregate into overall county score

3. **Ranking & Filtering**:
   - Sort by composite score
   - Apply minimum threshold filters
   - Diversity injection for variety

4. **Explainability**:
   - Generate explanation for each recommendation
   - Identify key factors driving the score
   - Provide comparison to user's current location

**Machine Learning Enhancement:**
- Collaborative filtering based on similar users
- Content-based recommendations using county features
- Feedback loop for continuous improvement
- A/B testing framework for algorithm optimization

### Data Pipeline

**Collection Process:**
- **Scheduled jobs** (cron) for periodic data updates
- **API integrations** with government data sources:
  - US Census Bureau API
  - Bureau of Labor Statistics (BLS)
  - NOAA Climate Data
  - FRED Economic Data
  - Zillow Housing Data
- **Error handling** with retry logic and fallbacks
- **Data validation** ensuring quality and consistency
- **Logging and monitoring** for pipeline health

**Processing Steps:**
1. Extract data from external APIs
2. Transform and normalize data
3. Validate data quality
4. Load into PostgreSQL database
5. Update materialized views
6. Clear relevant caches
7. Generate data quality reports

**Data Freshness:**
- Census data: Annual updates
- Employment data: Monthly updates
- Housing data: Monthly updates
- Climate data: Daily aggregation to monthly
- Economic indicators: Monthly updates

---

## Deployment Architecture

### Production Environment

**Frontend Deployment:**
- **Platform**: Vercel or Netlify
- **CDN**: Cloudflare or AWS CloudFront
- **Features**:
  - Automatic deployments from git
  - Preview deployments for PR reviews
  - Edge caching for static assets
  - Global distribution for low latency

**Backend Deployment:**
- **Platform**: AWS, Google Cloud, or Azure
- **Compute Options**:
  - **Option 1**: EC2/GCE instances with auto-scaling
  - **Option 2**: Container orchestration (ECS, GKE, AKS)
  - **Option 3**: Serverless (AWS Lambda, Cloud Functions)
- **Load Balancing**: Application Load Balancer
- **Auto-scaling**: Based on CPU/memory metrics

**Database Hosting:**
- **Platform**: AWS RDS, Google Cloud SQL, or managed PostgreSQL
- **Configuration**:
  - Multi-AZ deployment for high availability
  - Automated backups with point-in-time recovery
  - Read replicas for query performance
  - Monitoring with CloudWatch/Stackdriver

**Caching Layer:**
- **Redis Cloud** or **AWS ElastiCache**
- In-memory caching for frequently accessed data
- Session storage
- Rate limiting counters

**Monitoring & Logging:**
- **Application Monitoring**: New Relic, Datadog, or Application Insights
- **Error Tracking**: Sentry
- **Log Aggregation**: CloudWatch Logs, Elasticsearch/Kibana
- **Uptime Monitoring**: Pingdom, StatusCake
- **Analytics**: Google Analytics, Mixpanel

### CI/CD Pipeline

```
Git Push → GitHub Actions/GitLab CI
    ↓
Run Tests (Unit, Integration, E2E)
    ↓
Build Docker Images
    ↓
Deploy to Staging
    ↓
Run Smoke Tests
    ↓
Manual Approval
    ↓
Deploy to Production
    ↓
Health Checks & Monitoring
```

**Automated Checks:**
- Linting (ESLint, Pylint)
- Type checking (TypeScript, mypy)
- Unit tests (Jest, pytest)
- Integration tests
- Security scanning (Snyk, OWASP)
- Performance testing

---

## Development Setup

### Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Git

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/county-migration-assistant.git
   cd county-migration-assistant
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and database credentials
   ```

3. **Install frontend dependencies:**
   ```bash
   cd frontend
   npm install
   ```

4. **Install backend dependencies:**
   ```bash
   cd ../backend
   npm install
   pip install -r requirements.txt
   ```

5. **Set up database:**
   ```bash
   # Create database
   createdb county_migration
   
   # Run migrations
   npm run migrate
   ```

6. **Seed initial data:**
   ```bash
   npm run seed
   ```

7. **Start development servers:**
   ```bash
   # Terminal 1 - Backend
   cd backend
   npm run dev
   
   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   
   # Terminal 3 - Data collection (optional)
   cd data-pipeline
   python collectData_improved.py --config config.json
   ```

8. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:5000
   - API Documentation: http://localhost:5000/api-docs

### Development Workflow

1. Create feature branch from `main`
2. Implement changes with tests
3. Run linting and tests locally
4. Create pull request
5. Address code review feedback
6. Merge to `main` after approval
7. Automatic deployment to staging
8. Manual promotion to production

---

## API Documentation

### Authentication Endpoints

```
POST   /api/v1/auth/register        - Create new user account
POST   /api/v1/auth/login           - User login
POST   /api/v1/auth/logout          - User logout
POST   /api/v1/auth/refresh         - Refresh access token
POST   /api/v1/auth/forgot-password - Password reset request
POST   /api/v1/auth/reset-password  - Reset password
```

### User Endpoints

```
GET    /api/v1/users/profile        - Get user profile
PUT    /api/v1/users/profile        - Update user profile
DELETE /api/v1/users/profile        - Delete user account
GET    /api/v1/users/preferences    - List saved preferences
POST   /api/v1/users/preferences    - Create preference set
PUT    /api/v1/users/preferences/:id - Update preference set
DELETE /api/v1/users/preferences/:id - Delete preference set
```

### County Endpoints

```
GET    /api/v1/counties             - List all counties
GET    /api/v1/counties/:fips       - Get county details
GET    /api/v1/counties/:fips/stats - Get county statistics
GET    /api/v1/counties/search      - Search counties
```

### Recommendation Endpoints

```
POST   /api/v1/recommendations      - Generate recommendations
GET    /api/v1/recommendations/:id  - Get saved recommendations
POST   /api/v1/recommendations/:id/feedback - Submit feedback
```

### Data Endpoints

```
GET    /api/v1/data/factors         - List available factors
GET    /api/v1/data/statistics      - Get aggregated statistics
GET    /api/v1/data/trends          - Get trend data
```

---

## Project Structure

```
county-migration-assistant/
├── frontend/                    # React frontend application
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── store/              # Redux store
│   │   ├── services/           # API services
│   │   ├── utils/              # Utility functions
│   │   ├── types/              # TypeScript types
│   │   └── styles/             # Global styles
│   ├── public/                 # Static assets
│   ├── tests/                  # Frontend tests
│   └── package.json
│
├── backend/                     # Node.js backend API
│   ├── src/
│   │   ├── controllers/        # Request handlers
│   │   ├── models/             # Database models
│   │   ├── routes/             # API routes
│   │   ├── middleware/         # Express middleware
│   │   ├── services/           # Business logic
│   │   ├── utils/              # Utility functions
│   │   └── config/             # Configuration
│   ├── tests/                  # Backend tests
│   ├── migrations/             # Database migrations
│   └── package.json
│
├── ml-service/                  # Python ML service
│   ├── models/                 # ML models
│   ├── services/               # Recommendation engine
│   ├── utils/                  # Helper functions
│   ├── tests/                  # Python tests
│   └── requirements.txt
│
├── data-pipeline/              # Data collection scripts
│   ├── collectors/             # Data fetchers (improved versions)
│   │   ├── collectData_improved.py
│   │   ├── ResolveGeoCodes_improved.py
│   │   └── manageDB_improved.py
│   ├── processors/             # Data processing
│   ├── config/                 # Pipeline configuration
│   └── requirements.txt
│
├── infrastructure/             # Infrastructure as Code
│   ├── terraform/              # Terraform configs
│   ├── docker/                 # Dockerfiles
│   └── kubernetes/             # K8s manifests
│
├── docs/                       # Documentation
│   ├── api/                    # API documentation
│   ├── architecture/           # Architecture diagrams
│   └── guides/                 # User guides
│
├── .github/                    # GitHub configurations
│   └── workflows/              # CI/CD workflows
│
├── Datasources.md              # Data source documentation
├── Factors.md                  # Factor definitions
├── README.md                   # This file
├── .gitignore
├── .env.example
└── docker-compose.yml          # Local development setup
```

---

## Roadmap

### Phase 1: Foundation (Months 1-2)
**Goal**: Establish core infrastructure and data pipeline

- ✅ Research and identify data sources
- ✅ Design database schema
- ✅ Implement secure data collection scripts
- ✅ Set up development environment
- 🔄 Create initial dataset
- 🔄 Design API architecture
- 📋 Design UI/UX wireframes

### Phase 2: Backend Development (Months 3-4)
**Goal**: Build robust backend services

- 📋 Implement RESTful API endpoints
- 📋 Build authentication system
- 📋 Develop county matching algorithm v1
- 📋 Create database models and migrations
- 📋 Implement caching layer
- 📋 Write comprehensive tests
- 📋 Set up monitoring and logging

### Phase 3: Frontend Development (Months 4-5)
**Goal**: Create engaging user interface

- 📋 Build component library
- 📋 Implement preference questionnaire
- 📋 Develop results dashboard
- 📋 Create interactive maps
- 📋 Build comparison tools
- 📋 Implement user authentication flow
- 📋 Add responsive design

### Phase 4: ML Enhancement (Month 6)
**Goal**: Improve recommendations with ML

- 📋 Train initial recommendation model
- 📋 Implement collaborative filtering
- 📋 Add feedback collection system
- 📋 Create explainability features
- 📋 Set up A/B testing framework
- 📋 Build model monitoring dashboard

### Phase 5: Testing & Optimization (Month 7)
**Goal**: Ensure quality and performance

- 📋 Comprehensive integration testing
- 📋 Performance optimization
- 📋 Security audit
- 📋 Accessibility testing
- 📋 User acceptance testing
- 📋 Load testing
- 📋 Bug fixes and refinements

### Phase 6: Deployment (Month 8)
**Goal**: Launch to production

- 📋 Set up production infrastructure
- 📋 Configure CI/CD pipeline
- 📋 Deploy to staging environment
- 📋 Beta testing with select users
- 📋 Production deployment
- 📋 Monitoring setup
- 📋 Documentation finalization

### Phase 7: Post-Launch (Months 9-12)
**Goal**: Iterate based on user feedback

- 📋 Gather user feedback
- 📋 Implement priority features
- 📋 Improve algorithm accuracy
- 📋 Add social sharing capabilities
- 📋 Expand data sources
- 📋 Mobile app development
- 📋 Advanced analytics dashboard

### Future Enhancements

**Advanced Features:**
- Real-time migration trends visualization
- Community forums and discussions
- Expert consultations integration
- Virtual county tours
- Cost calculator tools
- Job board integration
- School district comparisons
- Healthcare facility finder

**Data Expansion:**
- International migration support
- Micro-level neighborhood data
- Real-time housing availability
- Local business directories
- Community event calendars
- Transportation infrastructure

**Platform Expansion:**
- Native mobile apps (iOS/Android)
- API for third-party integrations
- White-label solutions for organizations
- Enterprise features for relocation services
- Integration with moving companies

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards

- Follow the project's code style (enforced by linters)
- Write meaningful commit messages
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

---

## License

[Add your license here - e.g., MIT, Apache 2.0, etc.]

---

## Support

- **Documentation**: [docs.countymigration.app](https://docs.countymigration.app)
- **Issues**: [GitHub Issues](https://github.com/your-org/county-migration-assistant/issues)
- **Email**: support@countymigration.app
- **Community**: [Discord](https://discord.gg/your-invite) or [Slack](https://your-workspace.slack.com)

---

## Acknowledgments

- US Census Bureau for demographic data
- Bureau of Labor Statistics for employment data
- NOAA for climate information
- Federal Reserve Economic Data (FRED)
- Zillow for housing market data
- All open-source contributors

---

**Legend:**
- ✅ Completed
- 🔄 In Progress
- 📋 Planned

Last Updated: February 2026