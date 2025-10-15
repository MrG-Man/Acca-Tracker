#!/bin/bash

# Football Predictions App Deployment Script
# Usage: ./deploy.sh [environment]

set -e  # Exit on any error

ENVIRONMENT=${1:-production}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "🚀 Deploying Football Predictions App"
echo "Environment: $ENVIRONMENT"
echo "Project Root: $PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if .env file exists
check_environment() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error ".env file not found!"
        log_info "Copy .env.example to .env and configure your settings:"
        log_info "cp .env.example .env"
        exit 1
    fi

    # Check for required environment variables
    required_vars=(
        "SECRET_KEY"
        "SOFASCORE_API_KEY"
    )

    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$PROJECT_ROOT/.env"; then
            log_error "Required environment variable $var not set in .env file"
            exit 1
        fi
    done

    log_info "Environment configuration validated"
}

# Install dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_info "Created virtual environment"
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install dependencies
    pip install -r requirements.txt

    log_info "Dependencies installed successfully"
}

# Run database migrations (if needed in future)
run_migrations() {
    log_info "Checking for database migrations..."

    # Placeholder for future database migrations
    # if [ -f "manage.py" ]; then
    #     python manage.py db upgrade
    # fi

    log_info "No migrations needed"
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."

    directories=(
        "logs"
        "data/backups"
        "static/uploads"
    )

    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    done
}

# Set proper permissions
set_permissions() {
    log_info "Setting proper permissions..."

    # Set permissions for logs and data directories
    chmod -R 755 logs/ data/ static/
    chmod -R 644 requirements.txt .env.example

    log_info "Permissions set"
}

# Run tests (if in development)
run_tests() {
    if [ "$ENVIRONMENT" = "development" ]; then
        log_info "Running tests..."

        source venv/bin/activate

        # Run basic health check
        python -c "
from app import app
with app.test_client() as client:
    response = client.get('/health')
    if response.status_code == 200:
        print('✅ Health check passed')
    else:
        print(f'❌ Health check failed: {response.status_code}')
        exit 1
"

        log_info "Tests completed"
    fi
}

# Start application
start_application() {
    log_info "Starting application..."

    source venv/bin/activate

    if [ "$ENVIRONMENT" = "production" ]; then
        # Use gunicorn for production
        log_info "Starting with Gunicorn..."

        # Set production environment variables
        export FLASK_ENV=production

        # Start gunicorn
        exec gunicorn --config gunicorn.conf.py app:app
    else
        # Use Flask development server
        log_info "Starting with Flask development server..."

        # Set development environment variables
        export FLASK_ENV=development

        exec python app.py
    fi
}

# Main deployment flow
main() {
    log_info "Starting deployment process..."

    check_environment
    install_dependencies
    create_directories
    set_permissions
    run_migrations
    run_tests

    log_info "🎉 Deployment preparation completed!"
    log_info "Starting application..."

    # Start the application
    start_application
}

# Handle script interruption
cleanup() {
    log_info "Deployment script interrupted"
    exit 0
}

# Set trap for cleanup
trap cleanup INT TERM

# Run main function
main "$@"