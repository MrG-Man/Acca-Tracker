#!/bin/bash

# Football Predictions App Backup Script
# Usage: ./backup.sh [backup|restore|cleanup]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/data/backups"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_header() {
    echo -e "${BLUE}[STEP]${NC} $*"
}

# Create backup
create_backup() {
    log_header "Creating backup..."

    # Create backup directory with timestamp
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_NAME="backup_${TIMESTAMP}"
    BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

    # Create backup directory
    mkdir -p "$BACKUP_PATH"

    # Backup data directories
    DATA_DIRS=(
        "data/selections"
        "data/fixtures"
    )

    for dir in "${DATA_DIRS[@]}"; do
        if [ -d "$SCRIPT_DIR/$dir" ]; then
            log_info "Backing up $dir..."
            cp -r "$SCRIPT_DIR/$dir" "$BACKUP_PATH/"
        else
            log_warn "Directory $dir not found, skipping..."
        fi
    done

    # Create backup metadata
    cat > "$BACKUP_PATH/backup_metadata.json" << EOF
{
    "backup_date": "$(date -Iseconds)",
    "backup_name": "$BACKUP_NAME",
    "retention_days": $RETENTION_DAYS,
    "directories_backed_up": $(printf '%s\n' "${DATA_DIRS[@]}" | jq -R . | jq -s .),
    "total_size": "$(du -sh "$BACKUP_PATH" | cut -f1)",
    "file_count": "$(find "$BACKUP_PATH" -type f | wc -l)"
}
EOF

    # Compress backup
    log_info "Compressing backup..."
    cd "$BACKUP_DIR"
    tar -czf "${BACKUP_NAME}.tar.gz" -C "$BACKUP_NAME" .
    rm -rf "$BACKUP_NAME"

    BACKUP_SIZE=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)
    log_info "✅ Backup created: ${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})"
}

# List backups
list_backups() {
    log_header "Available backups:"

    if [ ! -d "$BACKUP_DIR" ]; then
        log_warn "No backup directory found"
        return
    fi

    echo
    printf "%-20s %-10s %-15s %-s\n" "BACKUP NAME" "SIZE" "CREATED" "LOCATION"
    echo "────────────────────────────────────────────────────────────────"

    for backup in "$BACKUP_DIR"/*.tar.gz; do
        if [ -f "$backup" ]; then
            BACKUP_NAME=$(basename "$backup" .tar.gz)
            SIZE=$(du -sh "$backup" | cut -f1)
            CREATED=$(stat -c %y "$backup" | cut -d'.' -f1)

            printf "%-20s %-10s %-15s %-s\n" "$BACKUP_NAME" "$SIZE" "$CREATED" "$backup"
        fi
    done

    if [ ! -f "$BACKUP_DIR"/*.tar.gz ]; then
        log_info "No backups found"
    fi
}

# Restore backup
restore_backup() {
    local backup_name="$1"

    if [ -z "$backup_name" ]; then
        log_error "Please specify backup name to restore"
        log_info "Available backups:"
        list_backups
        exit 1
    fi

    BACKUP_FILE="$BACKUP_DIR/${backup_name}.tar.gz"

    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "Backup file not found: $BACKUP_FILE"
        log_info "Available backups:"
        list_backups
        exit 1
    fi

    log_header "Restoring backup: $backup_name"
    log_warn "This will overwrite current data. Continue? (y/N)"
    read -r confirm

    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled"
        exit 0
    fi

    # Create temporary directory for extraction
    TEMP_DIR=$(mktemp -d)

    # Extract backup
    log_info "Extracting backup..."
    tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

    # Restore data directories
    DATA_DIRS=(
        "data/selections"
        "data/fixtures"
    )

    for dir in "${DATA_DIRS[@]}"; do
        if [ -d "$TEMP_DIR/$dir" ]; then
            log_info "Restoring $dir..."
            rm -rf "$SCRIPT_DIR/$dir"
            cp -r "$TEMP_DIR/$dir" "$SCRIPT_DIR/"
        fi
    done

    # Cleanup
    rm -rf "$TEMP_DIR"

    log_info "✅ Backup restored successfully"
}

# Cleanup old backups
cleanup_backups() {
    log_header "Cleaning up old backups (older than $RETENTION_DAYS days)..."

    if [ ! -d "$BACKUP_DIR" ]; then
        log_warn "No backup directory found"
        return
    fi

    CUT_OFF_DATE=$(date -d "$RETENTION_DAYS days ago" +%s)
    REMOVED_COUNT=0

    for backup in "$BACKUP_DIR"/*.tar.gz; do
        if [ -f "$backup" ]; then
            BACKUP_DATE=$(stat -c %Y "$backup")

            if [ "$BACKUP_DATE" -lt "$CUT_OFF_DATE" ]; then
                log_info "Removing old backup: $(basename "$backup")"
                rm -f "$backup"
                ((REMOVED_COUNT++))
            fi
        fi
    done

    log_info "✅ Cleanup completed. Removed $REMOVED_COUNT old backups"
}

# Show usage
usage() {
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  backup    Create a new backup"
    echo "  list      List available backups"
    echo "  restore   Restore from backup (requires backup name)"
    echo "  cleanup   Remove backups older than retention period"
    echo
    echo "Examples:"
    echo "  $0 backup"
    echo "  $0 restore backup_20231201_120000"
    echo "  $0 list"
    echo "  $0 cleanup"
}

# Main logic
main() {
    local command="$1"

    case "$command" in
        "backup")
            create_backup
            ;;
        "list")
            list_backups
            ;;
        "restore")
            restore_backup "$2"
            ;;
        "cleanup")
            cleanup_backups
            ;;
        "")
            usage
            exit 1
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"