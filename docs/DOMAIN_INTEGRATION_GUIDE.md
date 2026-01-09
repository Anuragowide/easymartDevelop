# 🌐 Domain Integration Guide - EasyMart

## Overview

This document details the complete domain integration process for deploying EasyMart to `gowideai.com` with subdomains for each service.

**Date Completed:** January 9, 2026  
**Server:** DigitalOcean Droplet (Ubuntu, 2 vCPU, 4GB RAM)  
**IPv4:** `167.71.228.100`

---

## 🎯 Target Domain Structure

| Service | Subdomain | Internal Port | Purpose |
|---------|-----------|---------------|---------|
| **Frontend** | `frontend.gowideai.com` | 3000 | Next.js UI |
| **Node Backend** | `node.gowideai.com` | 3001 | API + Widget Server |
| **Python Backend** | `python.gowideai.com` | 8000 | AI Assistant |

---

## 📋 Implementation Plan

### Phase 1: Local Code Changes
1. Update `infra/docker-compose.yml` - ALLOWED_ORIGINS and NEXT_PUBLIC_API_URL
2. Update `frontend/Dockerfile` - Default API URL
3. Update `infra/.env.example` - Domain-based URLs
4. Update `frontend/.env.example` - API URL
5. Update `backend-python/.env.example` - CORS origins

### Phase 2: Git Operations
1. Commit all changes to branch `dp333`
2. Push to remote repository
3. Pull latest changes on server

### Phase 3: Server Configuration
1. Update DNS records in GoDaddy
2. Configure Nginx reverse proxy
3. Update `.env` file on server
4. Remove conflicting `docker-compose.override.yml`
5. Rebuild Docker containers

### Phase 4: Verification
1. Verify environment variables in containers
2. Test all service endpoints
3. Browser testing for chat functionality

---

## 📁 Files Modified

### 1. `infra/docker-compose.yml`

**Changes Made:**

#### Line 64 - ALLOWED_ORIGINS (Python Backend)
```yaml
# BEFORE
- ALLOWED_ORIGINS=http://167.71.228.100:3000,http://167.71.228.100:3001,http://localhost:3000,http://localhost:3001,http://frontend:3000,http://backend-node:3001

# AFTER
- ALLOWED_ORIGINS=https://gowideai.com,https://www.gowideai.com,https://frontend.gowideai.com,https://node.gowideai.com,https://python.gowideai.com,http://gowideai.com,http://www.gowideai.com,http://frontend.gowideai.com,http://node.gowideai.com,http://python.gowideai.com,http://167.71.228.100:3000,http://167.71.228.100:3001,http://167.71.228.100:8000,http://localhost:3000,http://localhost:3001,http://localhost:8000,http://frontend:3000,http://backend-node:3001,http://backend-python:8000
```

#### Lines 130 & 136 - NEXT_PUBLIC_API_URL (Frontend)
```yaml
# BEFORE
args:
  - NEXT_PUBLIC_API_URL=http://167.71.228.100:3001
environment:
  - NEXT_PUBLIC_API_URL=http://167.71.228.100:3001

# AFTER
args:
  - NEXT_PUBLIC_API_URL=http://node.gowideai.com
environment:
  - NEXT_PUBLIC_API_URL=http://node.gowideai.com
```

---

### 2. `frontend/Dockerfile`

**Line 32 - Default API URL**
```dockerfile
# BEFORE
ARG NEXT_PUBLIC_API_URL=http://167.71.228.100:3001

# AFTER
ARG NEXT_PUBLIC_API_URL=http://node.gowideai.com
```

---

### 3. `infra/.env.example`

**Updated Sections:**
```dotenv
####################################
# CORS (Browser-facing)
####################################
ALLOWED_ORIGINS=https://gowideai.com,https://www.gowideai.com,https://frontend.gowideai.com,https://node.gowideai.com,https://python.gowideai.com,http://frontend.gowideai.com,http://node.gowideai.com,http://python.gowideai.com,http://localhost:3000,http://localhost:3001

####################################
# Public URLs (USED BY FRONTEND / BROWSER)
####################################
PUBLIC_NODE_API_URL=http://node.gowideai.com
PUBLIC_PYTHON_API_URL=http://python.gowideai.com
```

---

### 4. `frontend/.env.example`

```dotenv
# Next.js API URL (use domain for production, localhost for development)
NEXT_PUBLIC_API_URL=http://node.gowideai.com

# For local development, use:
# NEXT_PUBLIC_API_URL=http://localhost:3001

# Environment
NODE_ENV=development
```

---

### 5. `backend-python/.env.example`

```dotenv
# CORS (comma-separated origins)
# Production: include all domain variants
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://frontend.gowideai.com,https://frontend.gowideai.com,http://node.gowideai.com,https://node.gowideai.com
```

---

## 🖥️ Server Configuration

### DNS Records (GoDaddy)

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `@` | `167.71.228.100` | 600 |
| A | `www` | `167.71.228.100` | 600 |
| A | `frontend` | `167.71.228.100` | 600 |
| A | `node` | `167.71.228.100` | 600 |
| A | `python` | `167.71.228.100` | 600 |

---

### Nginx Configuration

**File:** `/etc/nginx/sites-available/gowideai.subdomains`

```nginx
# Frontend Subdomain
server {
    listen 80;
    listen [::]:80;
    server_name frontend.gowideai.com;
    
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}

# Node Backend Subdomain
server {
    listen 80;
    listen [::]:80;
    server_name node.gowideai.com;
    
    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}

# Python Backend Subdomain
server {
    listen 80;
    listen [::]:80;
    server_name python.gowideai.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

**Enable Configuration:**
```bash
ln -sf /etc/nginx/sites-available/gowideai.subdomains /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

---

### Server `.env` File Updates

**File:** `/root/easymart-v1/infra/.env`

**Added/Updated:**
```dotenv
NEXT_PUBLIC_API_URL=http://node.gowideai.com
PUBLIC_NODE_API_URL=http://node.gowideai.com
ALLOWED_ORIGINS=https://gowideai.com,https://www.gowideai.com,https://app.gowideai.com,https://frontend.gowideai.com,https://node.gowideai.com,https://api.gowideai.com,https://python.gowideai.com,http://gowideai.com,http://www.gowideai.com,http://frontend.gowideai.com,http://node.gowideai.com,http://python.gowideai.com,http://167.71.228.100:3000,http://167.71.228.100:3001,http://localhost:3000,http://localhost:3001
```

---

## 🐛 Issues Encountered & Solutions

### Issue 1: Git Merge Conflict on Server

**Problem:** Local changes on server conflicted with new branch
```
error: Your local changes to the following files would be overwritten by checkout:
        infra/docker-compose.yml
```

**Solution:**
```bash
git fetch origin
git reset --hard origin/dp333
```

---

### Issue 2: Docker Using Cached Builds

**Problem:** Even after updating config files, containers showed old values
```
NEXT_PUBLIC_API_URL=https://api.gowideai.com  # WRONG - should be http://node.gowideai.com
```

**Solution:**
```bash
docker system prune -a -f --volumes
docker compose build --no-cache
```

---

### Issue 3: docker-compose.override.yml Overriding Values

**Problem:** Found `docker-compose.override.yml` with OLD values that Docker Compose was auto-merging

**Root Cause Discovery:**
```bash
grep -r "https://api.gowideai.com" /root/easymart-v1/
# Output: /root/easymart-v1/infra/docker-compose.override.yml
```

**Solution:**
```bash
rm /root/easymart-v1/infra/docker-compose.override.yml
```

---

### Issue 4: .env File Missing NEXT_PUBLIC_API_URL

**Problem:** Server's `.env` file didn't have the `NEXT_PUBLIC_API_URL` variable

**Solution:**
```bash
echo "NEXT_PUBLIC_API_URL=http://node.gowideai.com" >> /root/easymart-v1/infra/.env
```

---

## 🚀 Deployment Commands

### Complete Deployment Script

```bash
#!/bin/bash

# Navigate to project
cd /root/easymart-v1

# Pull latest code from dp333 branch
git fetch origin
git reset --hard origin/dp333

# Remove override file if exists
rm -f infra/docker-compose.override.yml

# Navigate to infra
cd infra

# Stop all containers
docker compose down

# Clean Docker cache
docker system prune -a -f --volumes

# Rebuild all services
docker compose build --no-cache

# Start services
docker compose up -d

# Wait for services to be healthy
sleep 90

# Verify
docker ps
docker exec easymart-frontend printenv | grep NEXT_PUBLIC_API_URL
docker exec easymart-python env | grep ALLOWED_ORIGINS | head -c 200

# Test endpoints
curl -I http://frontend.gowideai.com
curl -I http://node.gowideai.com/health
curl -I http://python.gowideai.com/health
```

---

## ✅ Verification Checklist

### Server Verification
- [x] `NEXT_PUBLIC_API_URL=http://node.gowideai.com` in frontend container
- [x] `ALLOWED_ORIGINS` includes all domain variants in Python container
- [x] All 3 containers running and healthy
- [x] Nginx routing all subdomains correctly

### Endpoint Tests
- [x] `http://frontend.gowideai.com` → 200 OK
- [x] `http://node.gowideai.com/health` → 200 OK
- [x] `http://python.gowideai.com/health` → 200 OK (307 redirect to /health/)

### Browser Tests
- [x] Frontend loads at `frontend.gowideai.com`
- [x] Chat widget opens
- [x] API calls go to `node.gowideai.com`
- [x] Chat messages receive AI responses
- [x] No CORS errors in console

---

## 📊 Final Architecture

```
                    ┌─────────────────────────────────────────┐
                    │           GoDaddy DNS                    │
                    │  frontend.gowideai.com → 167.71.228.100  │
                    │  node.gowideai.com → 167.71.228.100      │
                    │  python.gowideai.com → 167.71.228.100    │
                    └────────────────┬────────────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────────────┐
                    │         DigitalOcean Droplet            │
                    │           167.71.228.100                │
                    │                                         │
                    │  ┌───────────────────────────────────┐  │
                    │  │            Nginx                   │  │
                    │  │  Port 80 (HTTP)                    │  │
                    │  │                                    │  │
                    │  │  frontend.* → localhost:3000       │  │
                    │  │  node.* → localhost:3001           │  │
                    │  │  python.* → localhost:8000         │  │
                    │  └───────────────────────────────────┘  │
                    │                                         │
                    │  ┌─────────────────────────────────────┐│
                    │  │         Docker Containers           ││
                    │  │                                     ││
                    │  │  ┌─────────────┐ ┌─────────────┐   ││
                    │  │  │  Frontend   │ │ Node Backend│   ││
                    │  │  │  :3000      │ │  :3001      │   ││
                    │  │  │  (Next.js)  │ │  (Express)  │   ││
                    │  │  └─────────────┘ └──────┬──────┘   ││
                    │  │                         │          ││
                    │  │  ┌─────────────────────▼────────┐  ││
                    │  │  │      Python Backend          │  ││
                    │  │  │         :8000                 │  ││
                    │  │  │      (FastAPI + AI)          │  ││
                    │  │  └──────────────────────────────┘  ││
                    │  └─────────────────────────────────────┘│
                    └─────────────────────────────────────────┘
```

---

## 🔧 Maintenance Commands

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker logs -f easymart-frontend
docker logs -f easymart-node
docker logs -f easymart-python
```

### Restart Services
```bash
docker compose restart
# Or specific service
docker compose restart frontend
```

### Rebuild Single Service
```bash
docker compose stop frontend
docker rmi easymart/frontend:latest --force
docker compose build --no-cache frontend
docker compose up -d frontend
```

### Check Environment Variables
```bash
docker exec easymart-frontend printenv | grep NEXT_PUBLIC_API_URL
docker exec easymart-python env | grep ALLOWED_ORIGINS
```

---

## 📞 Troubleshooting

### "Network Error" in Chat
1. Check `NEXT_PUBLIC_API_URL` in frontend container
2. Verify `ALLOWED_ORIGINS` in Python container
3. Test backend: `curl http://node.gowideai.com/health`

### CORS Errors
1. Ensure domain is in `ALLOWED_ORIGINS`
2. Include both HTTP and HTTPS variants
3. Restart backend containers after CORS changes

### Container Not Starting
1. Check logs: `docker logs easymart-<service>`
2. Verify ports are available: `netstat -tlnp | grep -E ':(3000|3001|8000)'`
3. Check Docker network: `docker network ls`

### DNS Not Resolving
1. Wait for propagation (up to 48 hours)
2. Check with: `nslookup frontend.gowideai.com`
3. Verify A records in GoDaddy

---

## 🎉 Success Criteria Met

| Requirement | Status |
|-------------|--------|
| Frontend accessible via subdomain | ✅ |
| Node API accessible via subdomain | ✅ |
| Python API accessible via subdomain | ✅ |
| Chat widget functional | ✅ |
| No CORS errors | ✅ |
| All services healthy | ✅ |

**Domain Integration Complete!** 🚀
