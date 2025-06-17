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
