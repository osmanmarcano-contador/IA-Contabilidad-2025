Sección 2: Configuración de Base de Datos y Seguridad
2.1 Arquitectura de Base de Datos para Aplicaciones Contables con IA
2.1.1 Selección de Base de Datos según el Módulo
Para Aplicaciones del Módulo 2 (Python para Contadores):
yaml# docker-compose.yml - Stack básico
version: '3.8'
services:
  postgresql:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: contabilidad_ia
      POSTGRES_USER: contador_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
Para Aplicaciones del Módulo 3 (Machine Learning):
sql-- Estructura de tablas para análisis de fraudes
CREATE TABLE transacciones_contables (
    id SERIAL PRIMARY KEY,
    fecha_transaccion TIMESTAMP NOT NULL,
    cuenta_debito VARCHAR(20) NOT NULL,
    cuenta_credito VARCHAR(20) NOT NULL,
    monto DECIMAL(15,2) NOT NULL,
    descripcion TEXT,
    usuario_registro VARCHAR(50),
    features_ml JSONB, -- Características para ML
    anomaly_score DECIMAL(5,4), -- Score de detección de anomalías
    es_fraude BOOLEAN DEFAULT FALSE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_monto_positivo CHECK (monto > 0)
);

-- Índices para optimización de consultas ML
CREATE INDEX idx_transacciones_fecha ON transacciones_contables(fecha_transaccion);
CREATE INDEX idx_transacciones_anomaly ON transacciones_contables(anomaly_score);
CREATE INDEX idx_transacciones_features ON transacciones_contables USING GIN(features_ml);
2.1.2 Configuración de PostgreSQL para Cargas de Trabajo de IA
sql-- postgresql.conf - Optimizaciones para ML
-- Configuración de memoria
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 64MB
maintenance_work_mem = 256MB

-- Configuración para escrituras concurrentes
max_connections = 200
checkpoint_segments = 32
checkpoint_completion_target = 0.9

-- Extensiones necesarias para análisis
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
2.2 Configuración de Seguridad Multicapa
2.2.1 Seguridad a Nivel de Base de Datos
sql-- Creación de usuarios con privilegios mínimos
-- Usuario para aplicación web
CREATE USER app_user WITH PASSWORD 'secure_app_password_2024!';
GRANT CONNECT ON DATABASE contabilidad_ia TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Usuario para procesos de ML (solo lectura)
CREATE USER ml_user WITH PASSWORD 'secure_ml_password_2024!';
GRANT CONNECT ON DATABASE contabilidad_ia TO ml_user;
GRANT USAGE ON SCHEMA public TO ml_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ml_user;

-- Usuario para auditoría (solo lectura)
CREATE USER audit_user WITH PASSWORD 'secure_audit_password_2024!';
GRANT CONNECT ON DATABASE contabilidad_ia TO audit_user;
GRANT USAGE ON SCHEMA public TO audit_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO audit_user;
2.2.2 Encriptación de Datos Sensibles
python# utils/encryption.py - Utilidades de encriptación
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class DataEncryption:
    """Clase para encriptar datos sensibles de contabilidad"""
    
    def __init__(self, password: str = None):
        if password is None:
            password = os.environ.get('ENCRYPTION_KEY', 'default_key_change_in_production')
        
        self.key = self._generate_key(password.encode())
        self.cipher_suite = Fernet(self.key)
    
    def _generate_key(self, password: bytes) -> bytes:
        """Genera clave de encriptación desde password"""
        salt = b'salt_for_accounting_2024'  # En producción usar salt aleatorio
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encripta datos sensibles como números de cuenta"""
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Desencripta datos sensibles"""
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
        return decrypted_data.decode()

# Ejemplo de uso en modelos
from sqlalchemy import Column, String, Text
from sqlalchemy.ext.hybrid import hybrid_property

class CuentaBancaria(Base):
    __tablename__ = 'cuentas_bancarias'
    
    id = Column(Integer, primary_key=True)
    banco = Column(String(100), nullable=False)
    _numero_cuenta_encrypted = Column('numero_cuenta', Text, nullable=False)
    saldo_actual = Column(Numeric(15,2), default=0)
    
    encryption = DataEncryption()
    
    @hybrid_property
    def numero_cuenta(self):
        return self.encryption.decrypt_sensitive_data(self._numero_cuenta_encrypted)
    
    @numero_cuenta.setter
    def numero_cuenta(self, value):
        self._numero_cuenta_encrypted = self.encryption.encrypt_sensitive_data(value)
2.2.3 Configuración de Autenticación JWT
python# auth/jwt_manager.py - Gestión de tokens JWT
import jwt
import datetime
from typing import Dict, Optional
from functools import wraps
from flask import request, jsonify, current_app

class JWTManager:
    """Gestor de autenticación JWT para aplicaciones contables"""
    
    def __init__(self, secret_key: str, algorithm: str = 'HS256'):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiry_hours = 8  # Tokens expiran en 8 horas
    
    def generate_token(self, user_data: Dict) -> str:
        """Genera token JWT para usuario autenticado"""
        payload = {
            'user_id': user_data['id'],
            'email': user_data['email'],
            'role': user_data['role'],  # contador, auditor, admin
            'permissions': user_data.get('permissions', []),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=self.token_expiry_hours),
            'iat': datetime.datetime.utcnow(),
            'iss': 'contabilidad-ia-system'
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verifica y decodifica token JWT"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def token_required(self, roles_required: list = None):
        """Decorador para rutas que requieren autenticación"""
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                token = request.headers.get('Authorization')
                
                if not token:
                    return jsonify({'error': 'Token requerido'}), 401
                
                try:
                    # Remover 'Bearer ' del token
                    token = token.split(' ')[1] if ' ' in token else token
                    payload = self.verify_token(token)
                    
                    if not payload:
                        return jsonify({'error': 'Token inválido o expirado'}), 401
                    
                    # Verificar roles si se especificaron
                    if roles_required:
                        user_role = payload.get('role')
                        if user_role not in roles_required:
                            return jsonify({'error': 'Permisos insuficientes'}), 403
                    
                    # Agregar datos del usuario al contexto
                    request.current_user = payload
                    
                except Exception as e:
                    return jsonify({'error': 'Error procesando token'}), 401
                
                return f(*args, **kwargs)
            return wrapper
        return decorator

# Ejemplo de uso en rutas Flask
from flask import Blueprint

api_bp = Blueprint('api', __name__)
jwt_manager = JWTManager(os.environ.get('JWT_SECRET_KEY'))

@api_bp.route('/transacciones', methods=['GET'])
@jwt_manager.token_required(roles_required=['contador', 'auditor'])
def get_transacciones():
    """Endpoint protegido para obtener transacciones"""
    user_data = request.current_user
    # Solo mostrar transacciones del cliente del usuario
    return jsonify({'transacciones': []})
