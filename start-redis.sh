#!/bin/bash
# Start Redis with proper persistence configuration for the Climate Chatbot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REDIS_CONF="$SCRIPT_DIR/redis.conf"
REDIS_PID_FILE="/var/run/redis/redis-server.pid"

echo "=================================================="
echo "Starting Redis for Climate Chatbot with Persistence"
echo "=================================================="

# Check if Redis is already running
if [ -f "$REDIS_PID_FILE" ] && ps -p $(cat "$REDIS_PID_FILE") > /dev/null 2>&1; then
    echo "✓ Redis is already running (PID: $(cat $REDIS_PID_FILE))"
    echo ""
    echo "Redis status:"
    redis-cli ping && echo "  Connection: OK"
    redis-cli dbsize | awk '{print "  Cached keys: " $1}'
    redis-cli CONFIG GET appendonly | grep -A1 appendonly | tail -1 | awk '{print "  AOF enabled: " $1}'
    echo ""
    exit 0
fi

# Ensure required directories exist
echo "Setting up Redis directories..."
sudo mkdir -p /var/lib/redis
sudo mkdir -p /var/log/redis
sudo mkdir -p /var/run/redis

# Set proper permissions
sudo chown -R redis:redis /var/lib/redis 2>/dev/null || sudo chown -R $(whoami):$(whoami) /var/lib/redis
sudo chown -R redis:redis /var/log/redis 2>/dev/null || sudo chown -R $(whoami):$(whoami) /var/log/redis
sudo chown -R redis:redis /var/run/redis 2>/dev/null || sudo chown -R $(whoami):$(whoami) /var/run/redis

echo "✓ Directories configured"

# Start Redis with our custom configuration
echo "Starting Redis server with persistence enabled..."
if [ -f "$REDIS_CONF" ]; then
    redis-server "$REDIS_CONF" --daemonize yes --pidfile "$REDIS_PID_FILE"
    echo "✓ Redis started with custom configuration"
else
    echo "⚠ Warning: redis.conf not found, starting with default + persistence"
    redis-server --daemonize yes --pidfile "$REDIS_PID_FILE" \
        --appendonly yes \
        --appendfsync everysec \
        --save 60 1 \
        --save 300 10 \
        --save 900 1 \
        --dir /var/lib/redis \
        --maxmemory 512mb \
        --maxmemory-policy allkeys-lru
fi

# Wait for Redis to start
sleep 2

# Verify Redis is running
echo ""
echo "Verifying Redis connection..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis is running and accepting connections"
    echo ""
    echo "Redis Configuration:"
    redis-cli CONFIG GET appendonly | grep -A1 appendonly | tail -1 | awk '{print "  AOF (Append Only File): " ($1 == "yes" ? "ENABLED ✓" : "DISABLED ✗")}'
    redis-cli CONFIG GET save | grep -A1 save | tail -1 | awk '{print "  RDB Snapshots: " $0}'
    redis-cli CONFIG GET dir | grep -A1 dir | tail -1 | awk '{print "  Data directory: " $0}'
    redis-cli CONFIG GET maxmemory | grep -A1 maxmemory | tail -1 | awk '{if($1=="0"){print "  Max memory: unlimited"}else{print "  Max memory: " $1/1024/1024 " MB"}}'
    echo ""
    redis-cli dbsize | awk '{print "Current cache entries: " $1}'
    echo ""
    echo "=================================================="
    echo "Redis is ready for the Climate Chatbot!"
    echo "Cache will persist across application restarts."
    echo "=================================================="
else
    echo "✗ Error: Redis failed to start"
    echo "Check logs at /var/log/redis/redis-server.log"
    exit 1
fi
