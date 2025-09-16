# Overview

Founders Management is a Flask-based web application designed for World of Warcraft (WoW) gold trading businesses to manage purchases, sales, and inventory tracking. The system integrates with Telegram WebApp for user authentication and provides real-time exchange rate monitoring, profit calculations, and comprehensive transaction management. Gold quantities are displayed in the standard WoW format (1k, 2k, 1.5k, etc.).

**Status**: Successfully imported and configured for Replit environment (September 16, 2025)

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Framework
- **Flask Application**: Core web framework with SQLAlchemy ORM for database operations
- **Database Layer**: SQLite for development with PostgreSQL support for production via configurable DATABASE_URL
- **Session Management**: Flask sessions with configurable secret keys for security

## Authentication System
- **Cross-Platform Telegram Integration**: Enhanced authentication supporting both mobile and desktop Telegram clients
- **Platform Detection**: Automatic detection of mobile vs desktop clients with appropriate handling
- **Session Consistency**: Cross-platform session management ensuring seamless user experience when switching between devices
- **User Management**: Role-based access control with whitelisting and admin privileges
- **Enhanced Session Caching**: Extended session lifetime (30 days) with platform-aware session validation

## Data Models
- **User Model**: Stores Telegram user data, authentication status, and role permissions
- **Purchase Model**: Records gold purchases with seller info, amounts, prices, and currencies
- **Sale Model**: Tracks gold sales with revenue calculations
- **Exchange Rate Model**: Caches live currency conversion rates

## Frontend Architecture
- **Template Engine**: Jinja2 templates with responsive design using TailwindCSS
- **Progressive Web App**: Mobile-optimized interface designed for Telegram WebApp
- **Dark Mode Support**: System-wide theme switching with persistent preferences
- **Real-time Updates**: JavaScript integration for live exchange rates and form validation

## Business Logic
- **Inventory Management**: Automatic calculation of available gold inventory from purchases minus sales
- **Multi-currency Support**: CAD, USD, and IRR currency handling with live exchange rates
- **Profit Calculations**: Real-time profit/loss analysis based on purchase costs and sale revenues

## Security Model
- **Access Control**: Whitelist-based user authorization with admin oversight
- **Data Validation**: Server-side input validation and sanitization
- **CSRF Protection**: Form-based security measures for transaction integrity

# External Dependencies

## Third-party Services
- **PriceToDay API**: Free market Iranian Rial (IRR) exchange rates via https://api.priceto.day/v1/latest/irr/usd
- **ExchangeRate.host API**: Live currency conversion rates for CAD/USD pairs (fallback for IRR)
- **Telegram WebApp API**: User authentication and app integration within Telegram ecosystem

## Frontend Libraries
- **TailwindCSS**: Utility-first CSS framework via CDN for responsive styling
- **Feather Icons**: SVG icon library for consistent UI elements
- **Telegram WebApp SDK**: JavaScript SDK for WebApp functionality and user data access

## Python Dependencies
- **Flask**: Web application framework
- **SQLAlchemy**: Database ORM and query builder
- **Requests**: HTTP client for external API calls
- **Werkzeug**: WSGI utilities including ProxyFix for deployment

## Development Environment
- **PostgreSQL**: Development database provided by Replit's built-in PostgreSQL service
- **Neon PostgreSQL**: Production database for Vercel deployment with optimized connection pooling  
- **Environment Variables**: Configuration management for API keys, database URLs, and application secrets
- **Replit Configuration**: Web application configured to run on port 5000 with proper proxy settings

## Deployment Configuration
- **Hybrid Environment Support**: Automatically detects and configures for Replit (dev) vs Vercel (production)
- **Neon Database Integration**: Optimized connection settings for Neon's serverless PostgreSQL
- **SSL Security**: Required SSL connections for production database
- **Connection Pooling**: Configured for Vercel's serverless environment
- **Replit Deployment**: Configured for autoscale deployment target with proper WSGI configuration

# Recent Changes

## September 16, 2025 - GitHub Import and Replit Setup
- Successfully imported Flask application from GitHub repository
- Configured for Replit environment with PostgreSQL database integration
- Set up proper web workflow on port 5000 with webview output
- Cleaned up requirements.txt to remove duplicates
- Fixed minor LSP diagnostics for better code quality
- Configured deployment settings for production readiness
- Application successfully running with Telegram WebApp authentication interface