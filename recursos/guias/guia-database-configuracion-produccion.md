2.5 Variables de entorno y configuración segura
2.5.1 Archivo de Variables de Entorno
intento# .env.production - Variables de entorno para producción
# ¡NUNCA incluir este archivo en control de versiones!

# Base de datos
DB_HOST=localhost
DB_PORT=5432
DB_NAME=contabilidad_ia
DB_USER=app_user
DB_PASSWORD=SecurePassword123!
DB_SSL_MODE=require

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=RedisSecurePass2024!

# Seguridad
JWT_SECRET_KEY=your-super-secret-jwt-key-min-256-bits
ENCRYPTION_KEY=your-encryption-key-for-sensitive-data
FLASK_SECRET_KEY=your-flask-secret-key

# APIs externas (del Módulo 4)
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
NEWS_API_KEY=your-news-api-key
OPENSTREETMAP_API_KEY=your-osm-key

# Configuración de aplicación
FLASK_ENV=production
DEBUG=False
TESTING=False

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/contabilidad_ia.log

# Monitoreo
ENABLE_MONITORING=True
SECURITY_ALERT_EMAIL=admin@tuempresa.com
