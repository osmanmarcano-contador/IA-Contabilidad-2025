# Verificar versiones mínimas requeridas
node --version    # v18.0.0+
npm --version     # v8.0.0+
python --version  # v3.9.0+
docker --version  # v20.0.0+
git --version     # v2.30.0+
Hardware Mínimo

RAM: 8GB (16GB recomendado)
CPU: 4 núcleos (8 núcleos recomendado)
Almacenamiento: 20GB libres
Red: Conexión estable a internet


⚙️ Configuración del Entorno
1. Clonar el Repositorio
bash# Clonar el repositorio principal
git clone https://github.com/tu-usuario/IA-Contabilidad-2025.git

# Navegar al directorio
cd IA-Contabilidad-2025

# Verificar la estructura
ls -la
2. Configurar Git (si es necesario)
bash# Configurar usuario
git config --global user.name "Tu Nombre"
git config --global user.email "tu-email@ejemplo.com"

# Verificar configuración
git config --list
3. Crear Estructura de Desarrollo
bash# Crear directorios de desarrollo local
mkdir -p {logs,temp,backups,uploads}
mkdir -p data/{dev,test,prod}
mkdir -p config/{local,dev,prod}

# Establecer permisos (Linux/macOS)
chmod 755 logs temp backups uploads
chmod 750 data config

📦 Instalación de Dependencias
Backend (Python/Django)
bash# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt

# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt
Frontend (Node.js/React)
bash# Navegar al directorio frontend
cd frontend/

# Instalar dependencias
npm install

# Instalar dependencias de desarrollo
npm install --save-dev

# Verificar instalación
npm list --depth=0
Base de Datos
bash# PostgreSQL (recomendado)
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS (con Homebrew)
brew install postgresql

# Windows (descargar desde postgresql.org)
# Crear usuario y base de datos
sudo -u postgres createuser --interactive
sudo -u postgres createdb ia_contabilidad_dev

🗄️ Configuración de Base de Datos
1. PostgreSQL (Producción Recomendada)
sql-- Conectar a PostgreSQL
psql -U postgres

-- Crear base de datos
CREATE DATABASE ia_contabilidad_dev;

-- Crear usuario
CREATE USER ia_user WITH ENCRYPTED PASSWORD 'tu_password_seguro';

-- Otorgar permisos
GRANT ALL PRIVILEGES ON DATABASE ia_contabilidad_dev TO ia_user;

-- Configurar encoding
ALTER DATABASE ia_contabilidad_dev SET timezone TO 'UTC';
2. SQLite (Desarrollo Rápido)
python# En settings/local.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
3. Migrar Base de Datos
bash# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Cargar datos de prueba (opcional)
python manage.py loaddata fixtures/sample_data.json

🔐 Variables de Entorno
1. Crear Archivo .env
bash# Crear archivo de variables de entorno
touch .env

# Agregar al .gitignore
echo ".env" >> .gitignore
2. Configuración .env
bash# =================
# CONFIGURACIÓN GENERAL
# =================
DEBUG=True
ENVIRONMENT=development
SECRET_KEY=django-insecure-tu-clave-secreta-aqui-cambiar-en-produccion

# =================
# BASE DE DATOS
# =================
DB_ENGINE=django.db.backends.postgresql
DB_NAME=ia_contabilidad_dev
DB_USER=ia_user
DB_PASSWORD=tu_password_seguro
DB_HOST=localhost
DB_PORT=5432

# =================
# REDIS (CACHE)
# =================
REDIS_URL=redis://localhost:6379/1
CACHE_TTL=300

# =================
# CELERY (TAREAS ASÍNCRONAS)
# =================
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# =================
# ARCHIVOS Y MEDIA
# =================
MEDIA_ROOT=/ruta/completa/al/proyecto/media
STATIC_ROOT=/ruta/completa/al/proyecto/staticfiles
FILE_UPLOAD_MAX_MEMORY_SIZE=10485760

# =================
# EMAIL
# =================
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_USE_TLS=False

# =================
# LOGS
# =================
LOG_LEVEL=DEBUG
LOG_FILE=logs/app.log

# =================
# IA Y APIS EXTERNAS
# =================
OPENAI_API_KEY=tu_clave_openai_aqui
ANTHROPIC_API_KEY=tu_clave_anthropic_aqui
MAX_TOKENS=4000
TEMPERATURE=0.7

# =================
# SEGURIDAD
# =================
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

🐳 Despliegue con Docker
1. Archivo docker-compose.yml
yamlversion: '3.8'

services:
  # Base de Datos PostgreSQL
  db:
    image: postgres:15-alpine
    container_name: ia_contabilidad_db
    environment:
      POSTGRES_DB: ia_contabilidad_dev
      POSTGRES_USER: ia_user
      POSTGRES_PASSWORD: tu_password_seguro
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - ia_network

  # Redis para Cache y Celery
  redis:
    image: redis:7-alpine
    container_name: ia_contabilidad_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - ia_network

  # Backend Django
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: ia_contabilidad_backend
    env_file:
      - .env
    volumes:
      - .:/app
      - media_files:/app/media
      - static_files:/app/staticfiles
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    networks:
      - ia_network
    command: >
      sh -c "python manage.py migrate &&
             python manage.py collectstatic --noinput &&
             python manage.py runserver 0.0.0.0:8000"

  # Frontend React
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: ia_contabilidad_frontend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000/api
    depends_on:
      - backend
    networks:
      - ia_network

  # Celery Worker
  celery:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: ia_contabilidad_celery
    env_file:
      - .env
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    networks:
      - ia_network
    command: celery -A config worker -l info

  # Celery Beat (Tareas Programadas)
  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: ia_contabilidad_celery_beat
    env_file:
      - .env
    volumes:
      - .:/app
    depends_on:
      - db
      - redis
    networks:
      - ia_network
    command: celery -A config beat -l info

volumes:
  postgres_data:
  redis_data:
  media_files:
  static_files:

networks:
  ia_network:
    driver: bridge
2. Dockerfile.backend
dockerfileFROM python:3.11-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt requirements-dev.txt ./

# Instalar dependencias Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements-dev.txt

# Copiar código fuente
COPY . .

# Crear directorios necesarios
RUN mkdir -p logs media staticfiles temp

# Permisos
RUN chmod +x scripts/*.sh

# Puerto
EXPOSE 8000

# Comando por defecto
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
3. Comandos Docker
bash# Construir imágenes
docker-compose build

# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Ejecutar migraciones
docker-compose exec backend python manage.py migrate

# Crear superusuario
docker-compose exec backend python manage.py createsuperuser

# Detener servicios
docker-compose down

# Limpiar volúmenes (¡CUIDADO!)
docker-compose down -v

🔧 Despliegue Manual
1. Iniciar Backend
bash# Activar entorno virtual
source venv/bin/activate

# Variables de entorno
export $(cat .env | xargs)

# Iniciar servidor de desarrollo
python manage.py runserver localhost:8000

# O con gunicorn (más robusto)
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
2. Iniciar Frontend
bash# En otra terminal, navegar a frontend
cd frontend/

# Iniciar servidor de desarrollo
npm start

# O construir para producción
npm run build
serve -s build -l 3000
3. Servicios Adicionales
bash# Redis (en otra terminal)
redis-server

# Celery Worker (en otra terminal)
celery -A config worker -l info

# Celery Beat (en otra terminal)
celery -A config beat -l info

# Monitoring Celery (opcional)
celery -A config flower

✅ Verificación del Sistema
1. Health Check Script
bash#!/bin/bash
# scripts/health_check.sh

echo "🔍 Verificando estado del sistema..."

# Verificar Backend
echo "📡 Verificando Backend..."
curl -f http://localhost:8000/api/health/ || echo "❌ Backend no responde"

# Verificar Frontend
echo "🌐 Verificando Frontend..."
curl -f http://localhost:3000/ || echo "❌ Frontend no responde"

# Verificar Base de Datos
echo "🗄️ Verificando Base de Datos..."
python manage.py check --database default || echo "❌ BD no conecta"

# Verificar Redis
echo "📮 Verificando Redis..."
redis-cli ping || echo "❌ Redis no responde"

# Verificar Celery
echo "⚡ Verificando Celery..."
celery -A config inspect ping || echo "❌ Celery no responde"

echo "✅ Verificación completada"
2. Endpoints de Verificación
bash# Health checks disponibles
curl http://localhost:8000/api/health/
curl http://localhost:8000/api/health/db/
curl http://localhost:8000/api/health/cache/
curl http://localhost:8000/api/health/celery/

# Admin Django
open http://localhost:8000/admin/

# API Documentation
open http://localhost:8000/api/docs/

# Frontend
open http://localhost:3000/

🚨 Solución de Problemas
Problemas Comunes
Error: Port already in use
bash# Encontrar proceso usando el puerto
lsof -i :8000
netstat -tulpn | grep :8000

# Terminar proceso
kill -9 PID_DEL_PROCESO

# O cambiar puerto
python manage.py runserver 0.0.0.0:8001
Error: Database connection
bash# Verificar PostgreSQL
sudo systemctl status postgresql
sudo systemctl start postgresql

# Verificar credenciales
psql -U ia_user -d ia_contabilidad_dev -h localhost

# Resetear base de datos
python manage.py flush
python manage.py migrate
Error: Redis connection
bash# Verificar Redis
redis-cli ping

# Reiniciar Redis
sudo systemctl restart redis-server

# Limpiar cache
redis-cli flushall
Error: Node modules
bash# Limpiar e instalar
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
Error: Python dependencies
bash# Recrear entorno virtual
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Logs y Debugging
bash# Ver logs de la aplicación
tail -f logs/app.log

# Logs de Django
python manage.py shell
import logging
logger = logging.getLogger('django')

# Logs de Docker
docker-compose logs -f backend
docker-compose logs -f frontend

# Debug en Django
DEBUG=True python manage.py runserver --verbosity=2

🛠️ Scripts de Utilidades
1. Setup Script
bash#!/bin/bash
# scripts/setup_local.sh

set -e

echo "🚀 Configurando entorno local..."

# Verificar requisitos
command -v python3 >/dev/null 2>&1 || { echo "Python3 requerido"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js requerido"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker requerido"; exit 1; }

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configurar frontend
cd frontend && npm install && cd ..

# Crear estructura
mkdir -p {logs,temp,backups,uploads}
mkdir -p data/{dev,test,prod}

# Configurar variables de entorno
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️ Configurar variables en .env"
fi

# Iniciar servicios con Docker
docker-compose up -d db redis

# Esperar a que DB esté lista
sleep 10

# Migraciones
python manage.py migrate
python manage.py collectstatic --noinput

echo "✅ Configuración completada"
echo "📋 Siguiente: python manage.py runserver"
2. Reset Script
bash#!/bin/bash
# scripts/reset_local.sh

echo "🔄 Reseteando entorno local..."

# Detener servicios
docker-compose down
pkill -f "python manage.py runserver" || true
pkill -f "npm start" || true

# Limpiar base de datos
docker-compose down -v
python manage.py flush --noinput

# Limpiar cache
redis-cli flushall || true
rm -rf __pycache__ .pytest_cache

# Reinstalar dependencias
pip install -r requirements.txt
cd frontend && rm -rf node_modules && npm install && cd ..

# Migrar de nuevo
python manage.py migrate

echo "✅ Reset completado"
3. Backup Script
bash#!/bin/bash
# scripts/backup_local.sh

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "💾 Creando backup en $BACKUP_DIR..."

# Backup de base de datos
pg_dump ia_contabilidad_dev > $BACKUP_DIR/database.sql

# Backup de archivos media
cp -r media $BACKUP_DIR/

# Backup de configuración
cp .env $BACKUP_DIR/

echo "✅ Backup completado en $BACKUP_DIR"

📚 Recursos Adicionales
Documentación

Django Documentation
React Documentation
Docker Documentation
PostgreSQL Documentation

Herramientas de Desarrollo

IDE: VSCode, PyCharm, WebStorm
Database: pgAdmin, DBeaver
API Testing: Postman, Insomnia
Monitoring: Django Debug Toolbar

Comandos Útiles
bash# Django
python manage.py shell_plus
python manage.py show_urls
python manage.py dbshell

# Git
git status
git log --oneline
git branch -a

# Docker
docker system prune
docker images
docker ps -a

📝 Nota: Este documento debe actualizarse según evolucione el proyecto. Mantén siempre la documentación sincronizada con los cambios en el código.
🔄 Última actualización: Junio 2025 - Parte 4, Chat 1
