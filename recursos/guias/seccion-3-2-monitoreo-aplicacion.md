3.2 Monitoreo de la aplicación
Métricas de rendimiento
El monitoreo efectivo de la aplicación es crucial para mantener un rendimiento óptimo y detectar problemas antes de que afecten a los usuarios.
Configuración de métricas básicas
javascript// metrics/appMetrics.js
const promClient = require('prom-client');

// Crear registro de métricas
const register = new promClient.Registry();

// Métricas de sistema
const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duración de peticiones HTTP',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.1, 0.5, 1, 2, 5]
});

const httpRequestsTotal = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total de peticiones HTTP',
  labelNames: ['method', 'route', 'status_code']
});

const activeConnections = new promClient.Gauge({
  name: 'active_connections',
  help: 'Conexiones activas actuales'
});

const memoryUsage = new promClient.Gauge({
  name: 'memory_usage_bytes',
  help: 'Uso de memoria en bytes',
  labelNames: ['type']
});

// Registrar métricas
register.registerMetric(httpRequestDuration);
register.registerMetric(httpRequestsTotal);
register.registerMetric(activeConnections);
register.registerMetric(memoryUsage);

// Métricas por defecto del sistema
promClient.collectDefaultMetrics({ register });

module.exports = {
  register,
  httpRequestDuration,
  httpRequestsTotal,
  activeConnections,
  memoryUsage
};
Middleware de métricas
javascript// middleware/metricsMiddleware.js
const { httpRequestDuration, httpRequestsTotal } = require('../metrics/appMetrics');

const metricsMiddleware = (req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    const route = req.route ? req.route.path : req.path;
    
    // Registrar duración de la petición
    httpRequestDuration
      .labels(req.method, route, res.statusCode)
      .observe(duration);
    
    // Incrementar contador de peticiones
    httpRequestsTotal
      .labels(req.method, route, res.statusCode)
      .inc();
  });
  
  next();
};

module.exports = metricsMiddleware;
Monitoreo de memoria y CPU
javascript// monitoring/systemMonitor.js
const { memoryUsage } = require('../metrics/appMetrics');
const logger = require('../config/logger');

class SystemMonitor {
  constructor() {
    this.startMonitoring();
  }

  startMonitoring() {
    // Monitorear memoria cada 30 segundos
    setInterval(() => {
      this.collectMemoryMetrics();
    }, 30000);

    // Monitorear CPU cada minuto
    setInterval(() => {
      this.collectCPUMetrics();
    }, 60000);
  }

  collectMemoryMetrics() {
    const memUsage = process.memoryUsage();
    
    memoryUsage.labels('rss').set(memUsage.rss);
    memoryUsage.labels('heapTotal').set(memUsage.heapTotal);
    memoryUsage.labels('heapUsed').set(memUsage.heapUsed);
    memoryUsage.labels('external').set(memUsage.external);

    // Alertar si el uso de memoria es alto
    const heapUsedMB = memUsage.heapUsed / 1024 / 1024;
    if (heapUsedMB > 500) {
      logger.warn('Alto uso de memoria detectado', {
        heapUsedMB,
        timestamp: new Date().toISOString()
      });
    }
  }

  collectCPUMetrics() {
    const cpuUsage = process.cpuUsage();
    const uptime = process.uptime();
    
    logger.info('CPU Usage', {
      user: cpuUsage.user / 1000000, // Convertir a segundos
      system: cpuUsage.system / 1000000,
      uptime: uptime
    });
  }
}

module.exports = SystemMonitor;
Controles de salud (Health Checks)
Endpoint de salud básico
javascript// routes/health.js
const express = require('express');
const router = express.Router();
const db = require('../config/database');
const logger = require('../config/logger');

// Health check básico
router.get('/health', async (req, res) => {
  const healthCheck = {
    status: 'OK',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    checks: {}
  };

  try {
    // Verificar base de datos
    await db.query('SELECT 1');
    healthCheck.checks.database = { status: 'OK', responseTime: 0 };
  } catch (error) {
    healthCheck.status = 'ERROR';
    healthCheck.checks.database = { 
      status: 'ERROR', 
      error: error.message 
    };
  }

  // Verificar memoria
  const memUsage = process.memoryUsage();
  const heapUsedMB = memUsage.heapUsed / 1024 / 1024;
  
  healthCheck.checks.memory = {
    status: heapUsedMB > 500 ? 'WARNING' : 'OK',
    heapUsedMB: Math.round(heapUsedMB),
    heapTotalMB: Math.round(memUsage.heapTotal / 1024 / 1024)
  };

  // Establecer código de respuesta
  const statusCode = healthCheck.status === 'OK' ? 200 : 503;
  
  res.status(statusCode).json(healthCheck);
});

// Health check detallado
router.get('/health/detailed', async (req, res) => {
  const detailedCheck = {
    status: 'OK',
    timestamp: new Date().toISOString(),
    version: process.env.APP_VERSION || '1.0.0',
    environment: process.env.NODE_ENV,
    uptime: process.uptime(),
    checks: {}
  };

  try {
    // Verificar base de datos con tiempo de respuesta
    const dbStart = Date.now();
    await db.query('SELECT NOW()');
    const dbResponseTime = Date.now() - dbStart;
    
    detailedCheck.checks.database = {
      status: 'OK',
      responseTime: dbResponseTime,
      connectionPool: {
        total: db.pool.totalCount,
        idle: db.pool.idleCount,
        waiting: db.pool.waitingCount
      }
    };
  } catch (error) {
    detailedCheck.status = 'ERROR';
    detailedCheck.checks.database = {
      status: 'ERROR',
      error: error.message
    };
  }

  // Verificar servicios externos
  try {
    // Ejemplo: verificar Redis si se usa
    if (process.env.REDIS_URL) {
      const redis = require('../config/redis');
      await redis.ping();
      detailedCheck.checks.redis = { status: 'OK' };
    }
  } catch (error) {
    detailedCheck.checks.redis = {
      status: 'ERROR',
      error: error.message
    };
  }

  // Métricas del sistema
  const memUsage = process.memoryUsage();
  detailedCheck.checks.system = {
    memory: {
      rss: Math.round(memUsage.rss / 1024 / 1024),
      heapTotal: Math.round(memUsage.heapTotal / 1024 / 1024),
      heapUsed: Math.round(memUsage.heapUsed / 1024 / 1024),
      external: Math.round(memUsage.external / 1024 / 1024)
    },
    cpu: process.cpuUsage(),
    pid: process.pid,
    platform: process.platform,
    nodeVersion: process.version
  };

  const statusCode = detailedCheck.status === 'OK' ? 200 : 503;
  res.status(statusCode).json(detailedCheck);
});

// Endpoint para métricas de Prometheus
router.get('/metrics', async (req, res) => {
  const { register } = require('../metrics/appMetrics');
  
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

module.exports = router;
Alertas automáticas
Sistema de alertas
javascript// monitoring/alerting.js
const logger = require('../config/logger');
const nodemailer = require('nodemailer');

class AlertingSystem {
  constructor() {
    this.transporter = nodemailer.createTransporter({
      host: process.env.SMTP_HOST,
      port: process.env.SMTP_PORT,
      secure: false,
      auth: {
        user: process.env.SMTP_USER,
        pass: process.env.SMTP_PASS
      }
    });

    this.alertThresholds = {
      memory: 512, // MB
      cpu: 80, // Porcentaje
      responseTime: 2000, // ms
      errorRate: 5 // Porcentaje
    };

    this.alertCooldown = new Map();
    this.cooldownPeriod = 5 * 60 * 1000; // 5 minutos
  }

  async sendAlert(type, message, severity = 'WARNING') {
    const alertKey = `${type}_${severity}`;
    
    // Verificar cooldown
    if (this.alertCooldown.has(alertKey)) {
      const lastAlert = this.alertCooldown.get(alertKey);
      if (Date.now() - lastAlert < this.cooldownPeriod) {
        return; // Evitar spam de alertas
      }
    }

    // Registrar alerta
    logger.error('Alert triggered', {
      type,
      message,
      severity,
      timestamp: new Date().toISOString()
    });

    // Enviar email si está configurado
    if (process.env.ALERT_EMAIL) {
      try {
        await this.transporter.sendMail({
          from: process.env.SMTP_FROM,
          to: process.env.ALERT_EMAIL,
          subject: `[${severity}] Alert: ${type}`,
          html: `
            <h3>Alert Triggered</h3>
            <p><strong>Type:</strong> ${type}</p>
            <p><strong>Severity:</strong> ${severity}</p>
            <p><strong>Message:</strong> ${message}</p>
            <p><strong>Time:</strong> ${new Date().toISOString()}</p>
            <p><strong>Server:</strong> ${process.env.NODE_ENV}</p>
          `
        });
      } catch (error) {
        logger.error('Failed to send alert email', error);
      }
    }

    // Establecer cooldown
    this.alertCooldown.set(alertKey, Date.now());
  }

  checkMemoryUsage() {
    const memUsage = process.memoryUsage();
    const heapUsedMB = memUsage.heapUsed / 1024 / 1024;

    if (heapUsedMB > this.alertThresholds.memory) {
      this.sendAlert(
        'HIGH_MEMORY_USAGE',
        `Memory usage: ${Math.round(heapUsedMB)}MB (threshold: ${this.alertThresholds.memory}MB)`,
        'WARNING'
      );
    }
  }

  checkResponseTime(responseTime, endpoint) {
    if (responseTime > this.alertThresholds.responseTime) {
      this.sendAlert(
        'SLOW_RESPONSE',
        `Slow response time: ${responseTime}ms on ${endpoint}`,
        'WARNING'
      );
    }
  }

  checkErrorRate(errorCount, totalRequests) {
    const errorRate = (errorCount / totalRequests) * 100;
    
    if (errorRate > this.alertThresholds.errorRate) {
      this.sendAlert(
        'HIGH_ERROR_RATE',
        `High error rate: ${errorRate.toFixed(2)}% (${errorCount}/${totalRequests})`,
        'CRITICAL'
      );
    }
  }

  startMonitoring() {
    // Verificar memoria cada minuto
    setInterval(() => {
      this.checkMemoryUsage();
    }, 60000);

    logger.info('Alerting system started');
  }
}

module.exports = AlertingSystem;
Integración con la aplicación
javascript// app.js (fragmento de integración)
const express = require('express');
const metricsMiddleware = require('./middleware/metricsMiddleware');
const healthRoutes = require('./routes/health');
const SystemMonitor = require('./monitoring/systemMonitor');
const AlertingSystem = require('./monitoring/alerting');

const app = express();

// Inicializar monitoreo
const systemMonitor = new SystemMonitor();
const alerting = new AlertingSystem();
alerting.startMonitoring();

// Middleware de métricas
app.use(metricsMiddleware);

// Rutas de salud
app.use('/api', healthRoutes);

// Middleware de manejo de errores con alertas
app.use((err, req, res, next) => {
  logger.error('Application error', {
    error: err.message,
    stack: err.stack,
    url: req.url,
    method: req.method
  });

  // Enviar alerta para errores críticos
  if (err.status >= 500) {
    alerting.sendAlert(
      'APPLICATION_ERROR',
      `Error 500 in ${req.method} ${req.url}: ${err.message}`,
      'CRITICAL'
    );
  }

  res.status(err.status || 500).json({
    error: process.env.NODE_ENV === 'production' 
      ? 'Internal Server Error' 
      : err.message
  });
});

module.exports = app;
Configuración de variables de entorno
bash# .env.example
# Configuración de alertas
ALERT_EMAIL=admin@tuempresa.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASS=tu-password-app
SMTP_FROM=noreply@tuempresa.com

# Métricas y monitoreo
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30000
Mejores prácticas para monitoreo
Métricas clave a monitorear

Métricas de aplicación:

Tiempo de respuesta promedio
Tasa de errores
Throughput (requests por segundo)
Disponibilidad del servicio


Métricas de sistema:

Uso de CPU
Uso de memoria
Uso de disco
Conexiones de red


Métricas de base de datos:

Tiempo de consulta
Conexiones activas
Bloqueos de tablas
Tamaño de la base de datos



Dashboard de monitoreo
javascript// monitoring/dashboard.js
const express = require('express');
const router = express.Router();
const { register } = require('../metrics/appMetrics');

router.get('/dashboard', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Monitoring Dashboard</title>
      <meta http-equiv="refresh" content="30">
      <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metric { margin: 10px 0; padding: 10px; border: 1px solid #ddd; }
        .status-ok { background-color: #d4edda; }
        .status-warning { background-color: #fff3cd; }
        .status-error { background-color: #f8d7da; }
      </style>
    </head>
    <body>
      <h1>Application Monitoring Dashboard</h1>
      <div id="metrics">
        <div class="metric status-ok">
          <h3>Application Status</h3>
          <p>Status: <strong>Running</strong></p>
          <p>Uptime: <strong>${Math.floor(process.uptime())} seconds</strong></p>
        </div>
        
        <div class="metric">
          <h3>Memory Usage</h3>
          <p>Heap Used: <strong>${Math.round(process.memoryUsage().heapUsed / 1024 / 1024)} MB</strong></p>
          <p>Heap Total: <strong>${Math.round(process.memoryUsage().heapTotal / 1024 / 1024)} MB</strong></p>
        </div>
        
        <div class="metric">
          <h3>Quick Actions</h3>
          <p><a href="/api/health">Health Check</a></p>
          <p><a href="/api/health/detailed">Detailed Health Check</a></p>
          <p><a href="/api/metrics">Prometheus Metrics</a></p>
        </div>
      </div>
    </body>
    </html>
  `);
});

module.exports = router;
Notas importantes:

Configurar umbrales de alerta apropiados para tu aplicación
Implementar cooldowns para evitar spam de alertas
Usar múltiples canales de notificación (email, Slack, etc.)
Monitorear tanto métricas técnicas como de negocio
Establecer SLAs claros y monitorear su cumplimiento
Implementar dashboards visuales para facilitar el monitoreo
Realizar pruebas regulares del sistema de alertas
