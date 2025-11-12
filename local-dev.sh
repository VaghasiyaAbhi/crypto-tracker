#!/bin/bash

# Local Development Helper Script
# Provides easy commands to manage local Docker environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if .env.local exists
check_env_file() {
    if [ ! -f "$PROJECT_DIR/.env.local" ]; then
        print_warning ".env.local not found. Creating from example..."
        cp "$PROJECT_DIR/.env.local.example" "$PROJECT_DIR/.env.local"
        print_success "Created .env.local - please review and update with your settings"
        print_info "Edit: nano .env.local or open .env.local in your editor"
        exit 0
    fi
}

# Function to start local development environment
start_local() {
    print_info "Starting local development environment..."
    check_env_file
    
    # Note: Don't export .env.local here - Docker Compose will load it automatically
    # Exporting multi-line values (like Firebase private key) causes shell errors
    
    docker-compose -f docker-compose.local.yml up -d
    
    print_success "Local environment started!"
    print_info "Services running:"
    echo "  📊 Frontend:  http://localhost:3000"
    echo "  🔧 Backend:   http://localhost:8000"
    echo "  🔴 Redis:     localhost:6379"
    echo "  🐘 Postgres:  localhost:5432"
    echo ""
    print_info "View logs: ./local-dev.sh logs"
    print_info "Stop all:  ./local-dev.sh stop"
}

# Function to start with rebuild
start_rebuild() {
    print_info "Starting local environment with rebuild..."
    check_env_file
    
    # Note: Don't export .env.local here - Docker Compose will load it automatically
    
    docker-compose -f docker-compose.local.yml up -d --build
    
    print_success "Local environment rebuilt and started!"
}

# Function to stop local environment
stop_local() {
    print_info "Stopping local development environment..."
    docker-compose -f docker-compose.local.yml down
    print_success "Local environment stopped!"
}

# Function to view logs
view_logs() {
    SERVICE=$1
    if [ -z "$SERVICE" ]; then
        print_info "Showing logs for all services (Ctrl+C to exit)..."
        docker-compose -f docker-compose.local.yml logs -f
    else
        print_info "Showing logs for $SERVICE (Ctrl+C to exit)..."
        docker-compose -f docker-compose.local.yml logs -f $SERVICE
    fi
}

# Function to show status
show_status() {
    print_info "Local development environment status:"
    docker-compose -f docker-compose.local.yml ps
}

# Function to run migrations
run_migrations() {
    print_info "Running database migrations..."
    docker-compose -f docker-compose.local.yml exec backend python manage.py migrate
    print_success "Migrations completed!"
}

# Function to create superuser
create_superuser() {
    print_info "Creating Django superuser..."
    docker-compose -f docker-compose.local.yml exec backend python manage.py createsuperuser
}

# Function to collect static files
collect_static() {
    print_info "Collecting static files..."
    docker-compose -f docker-compose.local.yml exec backend python manage.py collectstatic --noinput
    print_success "Static files collected!"
}

# Function to access Django shell
django_shell() {
    print_info "Opening Django shell..."
    docker-compose -f docker-compose.local.yml exec backend python manage.py shell
}

# Function to access database shell
db_shell() {
    print_info "Opening PostgreSQL shell..."
    docker-compose -f docker-compose.local.yml exec postgres psql -U postgres -d crypto_tracker_local
}

# Function to restart a service
restart_service() {
    SERVICE=$1
    if [ -z "$SERVICE" ]; then
        print_error "Please specify a service to restart"
        echo "Available services: backend, frontend, celery-worker, celery-beat, data-worker, calc-worker, redis, postgres"
        exit 1
    fi
    
    print_info "Restarting $SERVICE..."
    docker-compose -f docker-compose.local.yml restart $SERVICE
    print_success "$SERVICE restarted!"
}

# Function to clean up everything
cleanup() {
    print_warning "This will remove all local containers, volumes, and images!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cleaning up local development environment..."
        docker-compose -f docker-compose.local.yml down -v
        docker system prune -f
        print_success "Cleanup completed!"
    else
        print_info "Cleanup cancelled"
    fi
}

# Function to run tests
run_tests() {
    print_info "Running tests..."
    docker-compose -f docker-compose.local.yml exec backend python manage.py test
}

# Function to access backend container shell
backend_shell() {
    print_info "Opening backend container shell..."
    docker-compose -f docker-compose.local.yml exec backend sh
}

# Function to access frontend container shell
frontend_shell() {
    print_info "Opening frontend container shell..."
    docker-compose -f docker-compose.local.yml exec frontend sh
}

# Function to show help
show_help() {
    echo "🚀 Local Development Helper Script"
    echo ""
    echo "Usage: ./local-dev.sh [command]"
    echo ""
    echo "Available commands:"
    echo "  start           - Start local development environment"
    echo "  start:rebuild   - Start with rebuild (use after code changes)"
    echo "  stop            - Stop local development environment"
    echo "  restart <svc>   - Restart a specific service"
    echo "  status          - Show status of all services"
    echo "  logs [service]  - View logs (all services or specific one)"
    echo ""
    echo "Database commands:"
    echo "  migrate         - Run Django migrations"
    echo "  superuser       - Create Django superuser"
    echo "  dbshell         - Open PostgreSQL shell"
    echo ""
    echo "Utility commands:"
    echo "  static          - Collect static files"
    echo "  shell           - Open Django shell"
    echo "  backend-shell   - Access backend container shell"
    echo "  frontend-shell  - Access frontend container shell"
    echo "  test            - Run tests"
    echo "  cleanup         - Remove all containers and volumes"
    echo ""
    echo "Examples:"
    echo "  ./local-dev.sh start"
    echo "  ./local-dev.sh logs backend"
    echo "  ./local-dev.sh restart backend"
    echo "  ./local-dev.sh migrate"
}

# Main script logic
case "$1" in
    start)
        start_local
        ;;
    start:rebuild|rebuild)
        start_rebuild
        ;;
    stop)
        stop_local
        ;;
    restart)
        restart_service $2
        ;;
    status|ps)
        show_status
        ;;
    logs)
        view_logs $2
        ;;
    migrate)
        run_migrations
        ;;
    superuser)
        create_superuser
        ;;
    static)
        collect_static
        ;;
    shell)
        django_shell
        ;;
    dbshell|db)
        db_shell
        ;;
    backend-shell)
        backend_shell
        ;;
    frontend-shell)
        frontend_shell
        ;;
    test)
        run_tests
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
