#!/bin/bash
# Orbis Initial Server Setup Script
# Run this on the server as root: bash scripts/server-setup.sh

set -e

echo "=========================================="
echo "Orbis Server Setup"
echo "=========================================="

# Variables
APP_DIR="/opt/orbis"
DOMAIN="orbis.zumgugger.ch"

# 1. Create app directory
echo "[1/7] Creating app directory..."
mkdir -p $APP_DIR
cd $APP_DIR

# 2. Clone repository
echo "[2/7] Cloning repository..."
if [ -d ".git" ]; then
    echo "Repository already exists, pulling latest..."
    git pull origin main
else
    git clone https://github.com/Zumgugger/Orbis.git .
fi

# 3. Create .env.production
echo "[3/7] Setting up environment file..."
if [ ! -f ".env.production" ]; then
    cp .env.example .env.production

    # Generate secure secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/your-secret-key-here-change-this-in-production/$SECRET_KEY/" .env.production

    # Set production mode
    sed -i "s/ORBIS_CONFIG=development/ORBIS_CONFIG=production/" .env.production
    sed -i "s/DEVELOPMENT_MODE=True/DEVELOPMENT_MODE=False/" .env.production

    echo ""
    echo "⚠️  IMPORTANT: Edit .env.production with your Google OAuth credentials!"
    echo "    nano $APP_DIR/.env.production"
    echo ""
else
    echo ".env.production already exists, skipping..."
fi

# 4. Enable Apache modules
echo "[4/7] Enabling Apache modules..."
a2enmod proxy proxy_http ssl rewrite headers

# 5. Setup Apache virtual host
echo "[5/7] Setting up Apache virtual host..."
cp apache/orbis.zumgugger.ch.conf /etc/apache2/sites-available/

# 6. Get SSL certificate (if DNS is ready)
echo "[6/7] SSL Certificate..."
echo "Checking if DNS is ready..."
if host $DOMAIN > /dev/null 2>&1; then
    echo "DNS is ready. Getting SSL certificate..."
    certbot --apache -d $DOMAIN --non-interactive --agree-tos --email admin@zumgugger.ch
    a2ensite $DOMAIN
else
    echo "⚠️  DNS not ready yet. Run this after DNS is configured:"
    echo "    certbot --apache -d $DOMAIN"
    echo "    a2ensite $DOMAIN"
fi

# 7. Reload Apache
echo "[7/7] Reloading Apache..."
systemctl reload apache2

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Configure DNS: Add A record for $DOMAIN pointing to $(curl -s ifconfig.me)"
echo "2. Edit credentials: nano $APP_DIR/.env.production"
echo "3. Add Google OAuth redirect URI: https://$DOMAIN/auth/callback"
echo "4. Start the app: cd $APP_DIR && docker-compose up -d --build"
echo "5. Run migrations: docker-compose exec orbis alembic upgrade head"
echo ""
