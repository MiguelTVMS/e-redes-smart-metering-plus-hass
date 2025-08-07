#!/bin/bash

# Home Assistant Debug Helper Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

show_help() {
    echo "Home Assistant Debug Helper"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Start Home Assistant with debug logging"
    echo "  stop      - Stop Home Assistant containers"
    echo "  restart   - Restart Home Assistant containers"
    echo "  logs      - Show live logs from Home Assistant"
    echo "  shell     - Open shell in Home Assistant container"
    echo "  clean     - Clean up containers and volumes"
    echo "  status    - Show container status"
    echo ""
}

start_hass() {
    echo "Starting Home Assistant with debug logging..."
    docker-compose up -d homeassistant
    echo "Home Assistant starting in background..."
    echo "Access it at: http://localhost:8123"
    echo "Run '$0 logs' to see live logs"
}

stop_hass() {
    echo "Stopping Home Assistant containers..."
    docker-compose down
}

restart_hass() {
    echo "Restarting Home Assistant..."
    docker-compose restart homeassistant
}

show_logs() {
    echo "Showing live logs (Ctrl+C to exit)..."
    docker-compose logs -f homeassistant
}

open_shell() {
    echo "Opening shell in Home Assistant container..."
    docker-compose exec homeassistant bash
}

clean_containers() {
    echo "Cleaning up containers and volumes..."
    docker-compose down -v
    echo "Removing any orphaned containers..."
    docker system prune -f
}

show_status() {
    echo "Container status:"
    docker-compose ps
    echo ""
    echo "Integration files:"
    ls -la custom_components/e_redes_smart_metering_plus/
}

case "${1:-help}" in
    start)
        start_hass
        ;;
    stop)
        stop_hass
        ;;
    restart)
        restart_hass
        ;;
    logs)
        show_logs
        ;;
    shell)
        open_shell
        ;;
    clean)
        clean_containers
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
