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
2.5.2 Configuración de Nginx con SSL
nginx# /etc/nginx/sites-available/contabilidad-ia
server {
    listen 80;
    server_name tu-dominio.com www.tu-dominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name tu-dominio.com www.tu-dominio.com;

    # Certificados SSL (usar Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;
    
    # Configuración SSL segura
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Headers de seguridad
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    
    # Configuración de proxy
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Archivos estáticos
    location /static {
        alias /opt/contabilidad-ia/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Limitar tamaño de upload
    client_max_body_size 10M;
    
    # Logging
    access_log /var/log/nginx/contabilidad-ia.access.log;
    error_log /var/log/nginx/contabilidad-ia.error.log;
}
Esta sección proporciona una base sólida de seguridad y configuración de base de datos específicamente adaptada para las aplicaciones contables con IA desarrolladas en los módulos del programa de entrenamiento.
