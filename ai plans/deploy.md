# Orbis Deployment Plan

## Target Environment
- **Server**: Ubuntu 24.04.3 LTS (1 CPU, 2GB RAM, 50GB disk)
- **Web Server**: Apache2 (reverse proxy, already serving other sites)
- **Domain**: orbis.zumgugger.ch
- **SSL**: HTTPS via Certbot/Let's Encrypt
- **Container**: Docker + docker-compose (already installed)
- **Database**: SQLite (single user, can migrate to PostgreSQL later)

## Prerequisites Checklist
- [x] Ubuntu version: 24.04.3 LTS
- [x] Root/sudo access confirmed
- [x] Docker + docker-compose installed
- [x] Apache2 serving other sites
- [x] Other Docker containers running (Rails app)
- [ ] DNS pointing to server (user to configure)
- [x] SSL approach: Certbot
- [x] Secrets: .env file (simpler than Docker secrets for single-node)
- [x] Deployment: GitHub Actions CI/CD
- [x] Code transfer: git clone

---

## Phase 1: Refactoring for Production

### 1.1 Environment Configuration
- [ ] Ensure `settings.py` reads from environment variables
- [ ] Add production config validation
- [ ] Update `GOOGLE_REDIRECT_URI` for production domain

### 1.2 Production Requirements
- [ ] Add `gunicorn` to requirements.txt (WSGI server)
- [ ] Verify all dependencies are pinned

### 1.3 Security Hardening
- [ ] Ensure `SECRET_KEY` is required in production
- [ ] Disable debug mode in production
- [ ] Add security headers middleware

---

## Phase 2: Docker Setup

### 2.1 Dockerfile
```dockerfile
# To be created: /Orbis/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application
COPY . .

# Create non-root user
RUN useradd -m orbis && chown -R orbis:orbis /app
USER orbis

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:create_app()"]
```

### 2.2 docker-compose.yml
```yaml
# To be created: /Orbis/docker-compose.yml
version: '3.8'

services:
  orbis:
    build: .
    container_name: orbis
    restart: unless-stopped
    ports:
      - "127.0.0.1:5001:5000"  # Only expose to localhost for Apache proxy
    volumes:
      - ./instance:/app/instance          # SQLite DB persistence
      - ./uploads:/app/uploads            # File uploads
      - ./db_backups:/app/db_backups      # Backups
    env_file:
      - .env.production
    environment:
      - ORBIS_CONFIG=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 2.3 .env.production Template
```bash
# To be created on server (NOT in git)
SECRET_KEY=<generate-secure-key>
DATABASE_URL=sqlite:///instance/orbis.db
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>
DEFAULT_TIMEZONE=Europe/Zurich
ORBIS_CONFIG=production
```

---

## Phase 3: Apache2 Configuration

### 3.1 Virtual Host Configuration
```apache
# /etc/apache2/sites-available/orbis.zumgugger.ch.conf

<VirtualHost *:80>
    ServerName orbis.zumgugger.ch

    # Redirect all HTTP to HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</VirtualHost>

<VirtualHost *:443>
    ServerName orbis.zumgugger.ch

    # SSL Configuration (Let's Encrypt)
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/orbis.zumgugger.ch/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/orbis.zumgugger.ch/privkey.pem

    # Security Headers
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"

    # Proxy to Docker container
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:5001/
    ProxyPassReverse / http://127.0.0.1:5001/

    # WebSocket support (if needed later)
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) ws://127.0.0.1:5001/$1 [P,L]

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/orbis_error.log
    CustomLog ${APACHE_LOG_DIR}/orbis_access.log combined
</VirtualHost>
```

### 3.2 Required Apache Modules
```bash
sudo a2enmod proxy proxy_http ssl rewrite headers
```

---

## Phase 4: Deployment Steps

### 4.1 Server Preparation (one-time)
```bash
# 1. Install Docker (if not present)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# 2. Install docker-compose
sudo apt install docker-compose

# 3. Create app directory
sudo mkdir -p /opt/orbis
sudo chown $USER:$USER /opt/orbis

# 4. Clone repository
cd /opt/orbis
git clone https://github.com/Zumgugger/Orbis.git .

# 5. Create production .env
cp .env.example .env.production
nano .env.production  # Edit with production values

# 6. Setup SSL with Let's Encrypt
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d orbis.zumgugger.ch

# 7. Enable Apache site
sudo cp apache/orbis.conf /etc/apache2/sites-available/orbis.zumgugger.ch.conf
sudo a2ensite orbis.zumgugger.ch
sudo systemctl reload apache2
```

### 4.2 Initial Deployment
```bash
cd /opt/orbis

# Build and start
docker-compose up -d --build

# Run migrations
docker-compose exec orbis alembic upgrade head

# Check logs
docker-compose logs -f
```

### 4.3 Update Deployment (subsequent updates)
```bash
cd /opt/orbis
git pull
docker-compose up -d --build
docker-compose exec orbis alembic upgrade head
```

---

## Phase 5: Google OAuth Update

### 5.1 Add Production Redirect URI
In Google Cloud Console (glass-world-209910):
1. Go to APIs & Services > Credentials
2. Edit your OAuth 2.0 Client
3. Add Authorized redirect URI:
   - `https://orbis.zumgugger.ch/auth/callback`

---

## Phase 6: Backup Strategy

### 6.1 Automated Database Backup
```bash
# Add to crontab: daily backup at 3 AM
0 3 * * * docker-compose -f /opt/orbis/docker-compose.yml exec -T orbis \
    cp /app/instance/orbis.db /app/db_backups/orbis_$(date +\%Y\%m\%d).db
```

### 6.2 Keep Last 7 Days
```bash
# Cleanup old backups
find /opt/orbis/db_backups -name "*.db" -mtime +7 -delete
```

---

## Files to Create

1. [x] `Dockerfile` ✅ Created
2. [x] `docker-compose.yml` ✅ Created
3. [x] `.dockerignore` ✅ Created
4. [x] `.env.example` ✅ Updated
5. [x] `apache/orbis.zumgugger.ch.conf` ✅ Created
6. [x] `.github/workflows/deploy.yml` ✅ Created (CI/CD)
7. [x] `scripts/server-setup.sh` ✅ Created

---

## Quick Start Deployment Guide

### Step 1: Configure DNS (do this first!)
Add an A record in your DNS provider:
```
orbis.zumgugger.ch  →  185.66.108.95
```

### Step 2: Commit and push deployment files
```bash
# On your local machine
cd /mnt/e/Programmierenab24/Orbis
git add -A
git commit -m "chore: Add Docker deployment configuration"
git push
```

### Step 3: Initial server setup
```bash
# SSH to server
ssh root@zumgugger.ch

# Clone and setup
cd /opt
git clone https://github.com/Zumgugger/Orbis.git orbis
cd orbis

# Run setup script
bash scripts/server-setup.sh

# Edit production environment
nano .env.production
# Fill in:
# - GOOGLE_CLIENT_ID (from your .env file)
# - GOOGLE_CLIENT_SECRET (from your .env file)

# Build and start
docker-compose up -d --build

# Run migrations
docker-compose exec orbis alembic upgrade head

# Check it's running
docker-compose ps
docker-compose logs
```

### Step 4: Get SSL certificate (after DNS propagates)
```bash
# On server
certbot --apache -d orbis.zumgugger.ch
a2ensite orbis.zumgugger.ch
systemctl reload apache2
```

### Step 5: Update Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials?project=glass-world-209910)
2. Edit your OAuth 2.0 Client
3. Add redirect URI: `https://orbis.zumgugger.ch/auth/callback`

### Step 6: Setup GitHub Actions (for auto-deploy)
1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add these secrets:
   - `SERVER_HOST`: `zumgugger.ch`
   - `SERVER_USER`: `root`
   - `SERVER_SSH_KEY`: (your SSH private key)

To generate SSH key for GitHub Actions:
```bash
# On server
ssh-keygen -t ed25519 -f /root/.ssh/github_deploy -N ""
cat /root/.ssh/github_deploy.pub >> /root/.ssh/authorized_keys
cat /root/.ssh/github_deploy  # Copy this to SERVER_SSH_KEY secret
```

---

## Checklist Before Go-Live

- [ ] DNS configured for orbis.zumgugger.ch
- [ ] SSL certificate obtained
- [ ] Google OAuth redirect URI updated
- [ ] Production SECRET_KEY generated (auto by setup script)
- [ ] Database migrated
- [ ] Test login flow works
- [ ] Test calendar sync works
- [ ] GitHub Actions secrets configured

---

## Rollback Plan

If deployment fails:
```bash
# Stop container
docker-compose down

# Restore previous version
git checkout <previous-commit>
docker-compose up -d --build
```

---

## Useful Commands

```bash
# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Shell into container
docker-compose exec orbis bash

# Check database
docker-compose exec orbis python -c "from app import create_app; from models import User; app=create_app(); ctx=app.app_context(); ctx.push(); print(User.query.all())"

# Backup database
docker-compose exec orbis cp /app/instance/orbis.db /app/db_backups/manual_backup.db
```
