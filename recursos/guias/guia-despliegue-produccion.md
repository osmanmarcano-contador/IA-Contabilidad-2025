1.2 Requisitos del Servidor
Especificaciones Mínimas
yamlServidor de Producción:
  CPU: 2 vCPU / 4 cores físicos
  RAM: 4GB mínimo, 8GB recomendado
  Almacenamiento: 50GB SSD
  Ancho de banda: 100 Mbps
  Sistema Operativo: Ubuntu 22.04 LTS / CentOS 8

Servidor de Desarrollo:
  CPU: 1 vCPU / 2 cores
  RAM: 2GB mínimo
  Almacenamiento: 20GB SSD
  Sistema Operativo: Ubuntu 22.04 LTS
Proveedores Cloud Recomendados (Costo-Efectivos)

DigitalOcean: Droplet de $12/mes (2GB RAM, 1 vCPU)
Vultr: Instancia de $10/mes (2GB RAM, 1 vCPU)
Linode: Nanode de $5/mes (1GB RAM, 1 vCPU) - Solo desarrollo
AWS EC2: t3.micro (Free tier 12 meses)
Google Cloud: e2-micro (Free tier permanente)


1.3 Configuración Inicial del Servidor
1.3.1 Actualización del Sistema
bash# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git vim htop

# CentOS/RHEL
sudo yum update -y
sudo yum install -y curl wget git vim htop
1.3.2 Instalación de Docker
bash# Instalación de Docker en Ubuntu
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalación
docker --version
docker-compose --version
1.3.3 Configuración de Firewall
bash# Ubuntu UFW
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# CentOS Firewalld
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

1.4 Estructura de Directorios
1.4.1 Crear Estructura Base
bash# Crear directorios del proyecto
sudo mkdir -p /opt/ia-contadores/{app,data,logs,backups,ssl}
sudo chown -R $USER:$USER /opt/ia-contadores

# Estructura detallada
mkdir -p /opt/ia-contadores/{
  app/{api,frontend,config},
  data/{postgres,uploads,exports},
  logs/{app,nginx,postgres},
  backups/{daily,weekly,monthly},
  ssl/certs
}
1.4.2 Estructura Final
/opt/ia-contadores/
├── app/
│   ├── api/                 # Código FastAPI
│   ├── frontend/            # Código Streamlit
│   ├── config/              # Archivos de configuración
│   └── docker-compose.yml   # Orquestación de contenedores
├── data/
│   ├── postgres/            # Datos PostgreSQL
│   ├── uploads/             # Archivos subidos
│   └── exports/             # Reportes generados
├── logs/
│   ├── app/                 # Logs de aplicación
│   ├── nginx/               # Logs de Nginx
│   └── postgres/            # Logs de base de datos
├── backups/
│   ├── daily/               # Respaldos diarios
│   ├── weekly/              # Respaldos semanales
│   └── monthly/             # Respaldos mensuales
└── ssl/
    └── certs/               # Certificados SSL

1.5 Configuración de Docker Compose
1.5.1 Archivo docker-compose.yml
yamlversion: '3.8'

services:
  # Base de datos PostgreSQL
  postgres:
    image: postgres:15-alpine
    container_name: ia-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ia_contadores
      POSTGRES_USER: contador_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - /opt/ia-contadores/data/postgres:/var/lib/postgresql/data
      - /opt/ia-contadores/logs/postgres:/var/log
    ports:
      - "5432:5432"
    networks:
      - ia-network

  # API FastAPI
  api:
    build: 
      context: ./app/api
      dockerfile: Dockerfile
    container_name: ia-api
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://contador_user:${DB_PASSWORD}@postgres:5432/ia_contadores
      - SECRET_KEY=${API_SECRET_KEY}
      - DEBUG=False
    volumes:
      - /opt/ia-contadores/data/uploads:/app/uploads
      - /opt/ia-contadores/data/exports:/app/exports
      - /opt/ia-contadores/logs/app:/app/logs
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    networks:
      - ia-network

  # Frontend Streamlit
  frontend:
    build:
      context: ./app/frontend
      dockerfile: Dockerfile
    container_name: ia-frontend
    restart: unless-stopped
    environment:
      - API_URL=http://api:8000
    ports:
      - "8501:8501"
    depends_on:
      - api
    networks:
      - ia-network

  # Proxy Nginx
  nginx:
    image: nginx:alpine
    container_name: ia-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf
      - /opt/ia-contadores/ssl/certs:/etc/ssl/certs
      - /opt/ia-contadores/logs/nginx:/var/log/nginx
    depends_on:
      - api
      - frontend
    networks:
      - ia-network

  # Redis Cache (Opcional)
  redis:
    image: redis:7-alpine
    container_name: ia-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - ia-network

networks:
  ia-network:
    driver: bridge

volumes:
  redis_data:
1.5.2 Archivo de Variables de Entorno (.env)
bash# .env - Variables de entorno
# IMPORTANTE: No subir este archivo a GitHub

# Base de datos
DB_PASSWORD=tu_password_super_seguro_aqui
POSTGRES_DB=ia_contadores
POSTGRES_USER=contador_user

# API
API_SECRET_KEY=tu_clave_secreta_jwt_muy_larga_y_segura
DEBUG=False
ENVIRONMENT=production

# URLs
API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:8501

# SSL
SSL_CERT_PATH=/opt/ia-contadores/ssl/certs/cert.pem
SSL_KEY_PATH=/opt/ia-contadores/ssl/certs/key.pem

# Backup
BACKUP_RETENTION_DAYS=30
BACKUP_S3_BUCKET=ia-contadores-backups

1.6 Configuración de Nginx
1.6.1 Archivo nginx.conf
nginxevents {
    worker_connections 1024;
}

http {
    upstream api_backend {
        server api:8000;
    }
    
    upstream frontend_backend {
        server frontend:8501;
    }

    # Configuración principal
    server {
        listen 80;
        server_name tu-dominio.com www.tu-dominio.com;
        
        # Redirección HTTP a HTTPS
        return 301 https://$server_name$request_uri;
    }

    # Configuración HTTPS
    server {
        listen 443 ssl http2;
        server_name tu-dominio.com www.tu-dominio.com;

        # Certificados SSL
        ssl_certificate /etc/ssl/certs/cert.pem;
        ssl_certificate_key /etc/ssl/certs/key.pem;
        
        # Configuración SSL
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Logs
        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;

        # Configuración general
        client_max_body_size 50M;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;

        # API Routes
        location /api/ {
            proxy_pass http://api_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Frontend Routes
        location / {
            proxy_pass http://frontend_backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support para Streamlit
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Archivos estáticos
        location /static/ {
            alias /opt/ia-contadores/app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Archivos de salud
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}

1.7 Scripts de Administración
1.7.1 Script de Despliegue (deploy.sh)
bash#!/bin/bash
# deploy.sh - Script de despliegue automatizado

set -e

echo "🚀 Iniciando despliegue de IA Contadores..."

# Variables
PROJECT_DIR="/opt/ia-contadores"
BACKUP_DIR="/opt/ia-contadores/backups/daily"
DATE=$(date +%Y%m%d_%H%M%S)

# Crear backup antes del despliegue
echo "📦 Creando backup..."
sudo -u postgres pg_dump ia_contadores > "$BACKUP_DIR/backup_$DATE.sql"

# Actualizar código desde Git
echo "📥 Actualizando código..."
cd $PROJECT_DIR
git pull origin main

# Construir nuevas imágenes
echo "🏗️ Construyendo imágenes Docker..."
docker-compose build --no-cache

# Detener servicios actuales
echo "⏹️ Deteniendo servicios..."
docker-compose down

# Iniciar servicios nuevos
echo "▶️ Iniciando servicios..."
docker-compose up -d

# Verificar estado
echo "🔍 Verificando estado de servicios..."
sleep 10
docker-compose ps

# Test de conectividad
echo "🧪 Probando conectividad..."
curl -f http://localhost:8000/health || echo "❌ API no responde"
curl -f http://localhost:8501/ || echo "❌ Frontend no responde"

echo "✅ Despliegue completado!"
1.7.2 Script de Backup (backup.sh)
bash#!/bin/bash
# backup.sh - Sistema de respaldos automático

set -e

# Variables
BACKUP_DIR="/opt/ia-contadores/backups"
DB_NAME="ia_contadores"
DB_USER="contador_user"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Función de backup de base de datos
backup_database() {
    echo "📦 Respaldando base de datos..."
    docker exec ia-postgres pg_dump -U $DB_USER $DB_NAME > "$BACKUP_DIR/daily/db_backup_$DATE.sql"
    
    # Comprimir backup
    gzip "$BACKUP_DIR/daily/db_backup_$DATE.sql"
    echo "✅ Backup de DB completado: db_backup_$DATE.sql.gz"
}

# Función de backup de archivos
backup_files() {
    echo "📁 Respaldando archivos de aplicación..."
    tar -czf "$BACKUP_DIR/daily/files_backup_$DATE.tar.gz" \
        -C /opt/ia-contadores \
        data/uploads data/exports app/config
    echo "✅ Backup de archivos completado: files_backup_$DATE.tar.gz"
}

# Función de limpieza de backups antiguos
cleanup_old_backups() {
    echo "🧹 Limpiando backups antiguos..."
    find "$BACKUP_DIR/daily" -name "*.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR/daily" -name "*.sql" -mtime +$RETENTION_DAYS -delete
    echo "✅ Limpieza completada"
}

# Ejecutar backups
backup_database
backup_files
cleanup_old_backups

echo "🎉 Proceso de backup completado - $DATE"
1.7.3 Script de Monitoreo (monitor.sh)
bash#!/bin/bash
# monitor.sh - Script de monitoreo de servicios

# Función de verificación de servicio
check_service() {
    local service_name=$1
    local url=$2
    local expected_status=$3
    
    echo "🔍 Verificando $service_name..."
    
    response=$(curl -s -o /dev/null -w "%{http_code}" $url || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        echo "✅ $service_name: OK ($response)"
        return 0
    else
        echo "❌ $service_name: FALLO ($response)"
        return 1
    fi
}

# Función de verificación de contenedores
check_containers() {
    echo "🐳 Verificando contenedores Docker..."
    
    containers=("ia-postgres" "ia-api" "ia-frontend" "ia-nginx")
    
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "$container"; then
            echo "✅ $container: Ejecutándose"
        else
            echo "❌ $container: No encontrado o detenido"
        fi
    done
}

# Función de verificación de recursos
check_resources() {
    echo "💻 Verificando recursos del sistema..."
    
    # CPU
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
    echo "🔥 CPU: ${cpu_usage}%"
    
    # Memoria
    memory_info=$(free -m | awk 'NR==2{printf "Memoria: %s/%s MB (%.2f%%)", $3,$2,$3*100/$2 }')
    echo "🧠 $memory_info"
    
    # Disco
    disk_usage=$(df -h /opt/ia-contadores | awk 'NR==2 {print $5}' | sed 's/%//')
    echo "💾 Disco: ${disk_usage}% usado"
    
    # Alertas
    if [ "$disk_usage" -gt 80 ]; then
        echo "⚠️ ALERTA: Uso de disco alto (${disk_usage}%)"
    fi
}

# Ejecutar verificaciones
echo "🚀 Iniciando monitoreo de sistema - $(date)"
echo "================================================"

check_containers
echo ""
check_service "API Health" "http://localhost:8000/health" "200"
check_service "Frontend" "http://localhost:8501/" "200"
check_service "Nginx" "http://localhost:80/" "301"
echo ""
check_resources

echo "================================================"
echo "✅ Monitoreo completado - $(date)"
