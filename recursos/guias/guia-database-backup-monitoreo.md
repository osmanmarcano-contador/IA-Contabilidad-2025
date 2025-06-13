2.3 Configuración de Respaldo y Recuperación
2.3.1 Scripts de Respaldo Automatizado
intento#!/bin/bash
# scripts/backup_database.sh - Respaldo automático de base de datos

set -e

# Configuración
DB_NAME="contabilidad_ia"
DB_USER="postgres"
BACKUP_DIR="/opt/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Crear directorio de respaldo si no existe
mkdir -p $BACKUP_DIR

# Función de logging
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a $BACKUP_DIR/backup.log
}

# Respaldo completo
log "Iniciando respaldo de base de datos: $DB_NAME"

pg_dump \
  --host=$DB_HOST \
  --port=$DB_PORT \
  --username=$DB_USER \
  --dbname=$DB_NAME \
  --verbose \
  --clean \
  --no-owner \
  --no-privileges \
  --format=custom \
  --file=$BACKUP_DIR/backup_${DB_NAME}_${DATE}.dump

if [ $? -eq 0 ]; then
    log "Respaldo completado exitosamente: backup_${DB_NAME}_${DATE}.dump"
    
    # Comprimir respaldo
    gzip $BACKUP_DIR/backup_${DB_NAME}_${DATE}.dump
    log "Respaldo comprimido: backup_${DB_NAME}_${DATE}.dump.gz"
    
    # Limpiar respaldos antiguos
    find $BACKUP_DIR -name "backup_${DB_NAME}_*.dump.gz" -mtime +$RETENTION_DAYS -delete
    log "Respaldos antiguos eliminados (>${RETENTION_DAYS} días)"
    
else
    log "ERROR: Falló el respaldo de la base de datos"
    exit 1
fi
2.3.2 Script de Restauración
intento#!/bin/bash
# scripts/restore_database.sh - Restauración de base de datos

set -e

BACKUP_FILE=$1
DB_NAME="contabilidad_ia"
DB_USER="postgres"

if [ -z "$BACKUP_FILE" ]; then
    echo "Uso: $0 <archivo_respaldo>"
    exit 1
fi

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Iniciando restauración desde: $BACKUP_FILE"

# Verificar si el archivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    log "ERROR: Archivo de respaldo no encontrado: $BACKUP_FILE"
    exit 1
fi

# Descomprimir si es necesario
if [[ "$BACKUP_FILE" == *.gz ]]; then
    log "Descomprimiendo archivo..."
    UNCOMPRESSED_FILE="${BACKUP_FILE%.gz}"
    gunzip -c "$BACKUP_FILE" > "$UNCOMPRESSED_FILE"
    BACKUP_FILE="$UNCOMPRESSED_FILE"
fi

# Crear base de datos temporal para verificación
DB_TEMP="${DB_NAME}_restore_test"

log "Creando base de datos temporal: $DB_TEMP"
createdb --host=$DB_HOST --port=$DB_PORT --username=$DB_USER $DB_TEMP

# Restaurar en base temporal
log "Restaurando en base de datos temporal..."
pg_restore \
  --host=$DB_HOST \
  --port=$DB_PORT \
  --username=$DB_USER \
  --dbname=$DB_TEMP \
  --verbose \
  --clean \
  --if-exists \
  $BACKUP_FILE

if [ $? -eq 0 ]; then
    log "Restauración en base temporal exitosa"
    
    # Verificar integridad
    TABLES_COUNT=$(psql --host=$DB_HOST --port=$DB_PORT --username=$DB_USER --dbname=$DB_TEMP --tuples-only --command="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    
    if [ "$TABLES_COUNT" -gt 0 ]; then
        log "Verificación de integridad exitosa ($TABLES_COUNT tablas restauradas)"
        
        # Confirmar restauración en base principal
        read -p "¿Proceder con restauración en base principal? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log "Restaurando en base de datos principal..."
            dropdb --host=$DB_HOST --port=$DB_PORT --username=$DB_USER --if-exists $DB_NAME
            createdb --host=$DB_HOST --port=$DB_PORT --username=$DB_USER $DB_NAME
            
            pg_restore \
              --host=$DB_HOST \
              --port=$DB_PORT \
              --username=$DB_USER \
              --dbname=$DB_NAME \
              --verbose \
              $BACKUP_FILE
            
            log "Restauración completada exitosamente"
        fi
    fi
    
    # Limpiar base temporal
    dropdb --host=$DB_HOST --port=$DB_PORT --username=$DB_USER $DB_TEMP
    
else
    log "ERROR: Falló la restauración"
    dropdb --host=$DB_HOST --port=$DB_PORT --username=$DB_USER --if-exists $DB_TEMP
    exit 1
fi
2.4 Monitoreo y Auditoría de Seguridad
2.4.1 Sistema de Auditoría de Accesos
SQL-- Tabla de auditoría para transacciones contables
CREATE TABLE auditoria_transacciones (
    id SERIAL PRIMARY KEY,
    tabla_afectada VARCHAR(50) NOT NULL,
    registro_id INTEGER,
    operacion VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    usuario VARCHAR(50) NOT NULL,
    ip_address INET,
    datos_anteriores JSONB,
    datos_nuevos JSONB,
    timestamp_operacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100)
);

-- Función de trigger para auditoría
CREATE OR REPLACE FUNCTION fn_auditoria_transacciones()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO auditoria_transacciones (
            tabla_afectada, registro_id, operacion, usuario, 
            datos_anteriores, timestamp_operacion
        ) VALUES (
            TG_TABLE_NAME, OLD.id, TG_OP, current_user,
            row_to_json(OLD), CURRENT_TIMESTAMP
        );
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO auditoria_transacciones (
            tabla_afectada, registro_id, operacion, usuario,
            datos_anteriores, datos_nuevos, timestamp_operacion
        ) VALUES (
            TG_TABLE_NAME, NEW.id, TG_OP, current_user,
            row_to_json(OLD), row_to_json(NEW), CURRENT_TIMESTAMP
        );
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO auditoria_transacciones (
            tabla_afectada, registro_id, operacion, usuario,
            datos_nuevos, timestamp_operacion
        ) VALUES (
            TG_TABLE_NAME, NEW.id, TG_OP, current_user,
            row_to_json(NEW), CURRENT_TIMESTAMP
        );
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Crear triggers en tablas críticas
CREATE TRIGGER tr_auditoria_transacciones_contables
    AFTER INSERT OR UPDATE OR DELETE ON transacciones_contables
    FOR EACH ROW EXECUTE FUNCTION fn_auditoria_transacciones();
2.4.2 Monitoreo de rendimiento y seguridad
pitón# monitoring/security_monitor.py - Monitor de seguridad
import psutil
import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from typing import Dict, List

class SecurityMonitor:
    """Monitor de seguridad para aplicaciones contables"""
    
    def __init__(self, db_session, alert_threshold: Dict = None):
        self.db_session = db_session
        self.alert_threshold = alert_threshold or {
            'failed_logins_per_hour': 10,
            'large_queries_per_minute': 5,
            'cpu_usage_percent': 80,
            'memory_usage_percent': 85,
            'disk_usage_percent': 90
        }
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Configura logger para eventos de seguridad"""
        logger = logging.getLogger('security_monitor')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/var/log/security_monitor.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def check_failed_logins(self) -> List[Dict]:
        """Verifica intentos de login fallidos"""
        query = text("""
            SELECT ip_address, COUNT(*) as failed_attempts,
                   MAX(timestamp_operacion) as last_attempt
            FROM auditoria_transacciones 
            WHERE operacion = 'FAILED_LOGIN'
              AND timestamp_operacion > :time_threshold
            GROUP BY ip_address
            HAVING COUNT(*) > :threshold
            ORDER BY failed_attempts DESC
        """)
        
        time_threshold = datetime.now() - timedelta(hours=1)
        result = self.db_session.execute(
            query, 
            {
                'time_threshold': time_threshold,
                'threshold': self.alert_threshold['failed_logins_per_hour']
            }
        )
        
        suspicious_ips = result.fetchall()
        
        if suspicious_ips:
            self.logger.warning(
                f"IPs sospechosas detectadas: {len(suspicious_ips)} IPs con múltiples intentos fallidos"
            )
        
        return [dict(row) for row in suspicious_ips]
    
    def check_system_resources(self) -> Dict:
        """Verifica recursos del sistema"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        alerts = []
        
        if cpu_percent > self.alert_threshold['cpu_usage_percent']:
            alerts.append(f"CPU usage high: {cpu_percent}%")
            self.logger.warning(f"High CPU usage detected: {cpu_percent}%")
        
        if memory.percent > self.alert_threshold['memory_usage_percent']:
            alerts.append(f"Memory usage high: {memory.percent}%")
            self.logger.warning(f"High memory usage detected: {memory.percent}%")
        
        if (disk.used / disk.total * 100) > self.alert_threshold['disk_usage_percent']:
            disk_percent = disk.used / disk.total * 100
            alerts.append(f"Disk usage high: {disk_percent:.1f}%")
            self.logger.warning(f"High disk usage detected: {disk_percent:.1f}%")
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.used / disk.total * 100,
            'alerts': alerts
        }
    
    def check_large_queries(self) -> List[Dict]:
        """Verifica consultas que consumen muchos recursos"""
        query = text("""
            SELECT query, calls, total_time, mean_time, rows
            FROM pg_stat_statements 
            WHERE total_time > 1000  -- Consultas que toman más de 1 segundo
              AND calls > 1
            ORDER BY total_time DESC
            LIMIT 10
        """)
        
        try:
            result = self.db_session.execute(query)
            slow_queries = result.fetchall()
            
            if slow_queries:
                self.logger.info(f"Detectadas {len(slow_queries)} consultas lentas")
            
            return [dict(row) for row in slow_queries]
        
        except Exception as e:
            self.logger.error(f"Error checking slow queries: {e}")
            return []
    
    def generate_security_report(self) -> Dict:
        """Genera reporte completo de seguridad"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'failed_logins': self.check_failed_logins(),
            'system_resources': self.check_system_resources(),
            'slow_queries': self.check_large_queries()
        }
        
        # Log del reporte
        self.logger.info(f"Security report generated: {len(report['failed_logins'])} suspicious IPs, "
                        f"{len(report['system_resources']['alerts'])} system alerts, "
                        f"{len(report['slow_queries'])} slow queries")
        
        return report

# Script de monitoreo continuo
if __name__ == "__main__":
    from database import get_db_session
    import time
    
    monitor = SecurityMonitor(get_db_session())
    
    while True:
        try:
            report = monitor.generate_security_report()
            
            # Aquí se podría enviar alertas por email/Slack si hay problemas críticos
            critical_alerts = []
            critical_alerts.extend(report['system_resources']['alerts'])
            
            if len(report['failed_logins']) > 0:
                critical_alerts.append(f"{len(report['failed_logins'])} IPs sospechosas")
            
            if critical_alerts:
                print(f"ALERTA CRÍTICA: {'; '.join(critical_alerts)}")
            
            # Esperar 5 minutos antes del siguiente chequeo
            time.sleep(300)
            
        except KeyboardInterrupt:
            print("Monitoreo detenido por usuario")
            break
        except Exception as e:
            print(f"Error en monitoreo: {e}")
            time.sleep(60)  # Esperar 1 minuto en caso de error
