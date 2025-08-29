# Overview

Founders Management is a Flask-based web application designed for gold trading businesses to manage purchases, sales, and inventory tracking. The system integrates with Telegram WebApp for user authentication and provides real-time exchange rate monitoring, profit calculations, and comprehensive transaction management.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Framework
- **Flask Application**: Core web framework with SQLAlchemy ORM for database operations
- **Database Layer**: SQLite for development with PostgreSQL support for production via configurable DATABASE_URL
- **Session Management**: Flask sessions with configurable secret keys for security

## Authentication System
- **Telegram WebApp Integration**: Primary authentication method using Telegram's WebApp API
- **User Management**: Role-based access control with whitelisting and admin privileges
- **Session-based Auth**: Server-side session management for authenticated users

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
- **ExchangeRate.host API**: Live currency conversion rates for CAD/USD/IRR pairs
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
- **SQLite**: Local development database
- **PostgreSQL**: Production database support via environment configuration
- **Environment Variables**: Configuration management for API keys, database URLs, and application secrets