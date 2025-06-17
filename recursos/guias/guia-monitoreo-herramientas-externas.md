3.4 Herramientas de Monitoreo Externo
3.4.1 Configuración de PM2 para Monitoreo
PM2 proporciona herramientas integradas de monitoreo que permiten supervisar el estado de las aplicaciones Node.js en tiempo real.
Configuración Básica de PM2
javascript// ecosystem.config.js
module.exports = {
  apps: [{
    name: 'production-app',
    script: 'app.js',
    instances: 'max',
    exec_mode: 'cluster',
    
    // Configuración de monitoreo
    monitoring: true,
    pmx: true,
    
    // Configuración de logs
    log_file: './logs/combined.log',
    out_file: './logs/out.log',
    error_file: './logs/error.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    
    // Configuración de memoria y CPU
    max_memory_restart: '500M',
    min_uptime: '10s',
    max_restarts: 3,
    
    // Variables de entorno
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    
    // Configuración de reinicio automático
    watch: false,
    ignore_watch: ['node_modules', 'logs'],
    
    // Configuración de clustering
    instance_var: 'INSTANCE_ID'
  }]
};
Comandos de Monitoreo PM2
bash# Monitoreo en tiempo real
pm2 monit

# Estado detallado de procesos
pm2 status

# Logs en tiempo real
pm2 logs

# Métricas de sistema
pm2 describe <app-name>

# Reinicio automático por memoria
pm2 start ecosystem.config.js --max-memory-restart 500M

# Configuración de alertas
pm2 install pm2-server-monit
3.4.2 Integración con New Relic
New Relic proporciona monitoreo avanzado de aplicaciones con métricas detalladas de rendimiento.
Instalación y Configuración
bash# Instalación del agente New Relic
npm install newrelic --save
javascript// newrelic.js (archivo de configuración)
'use strict';

exports.config = {
  app_name: ['Production App'],
  license_key: process.env.NEW_RELIC_LICENSE_KEY,
  
  // Configuración de logging
  logging: {
    level: 'info',
    filepath: './logs/newrelic_agent.log'
  },
  
  // Configuración específica de Node.js
  node: {
    environment_variables: {
      NODE_ENV: 'production'
    }
  },
  
  // Configuración de transacciones
  transaction_tracer: {
    enabled: true,
    transaction_threshold: 'apdex_f',
    record_sql: 'obfuscated',
    explain_threshold: 500
  },
  
  // Configuración de errores
  error_collector: {
    enabled: true,
    ignore_status_codes: [404]
  },
  
  // Configuración de browser monitoring
  browser_monitoring: {
    enable: true
  },
  
  // Configuración de base de datos
  database: {
    record_sql: 'obfuscated',
    explain_threshold: 500
  }
};
javascript// app.js - Importar New Relic al inicio
require('newrelic');
const express = require('express');
const app = express();

// Middleware para métricas personalizadas
const newrelic = require('newrelic');

app.use((req, res, next) => {
  // Agregar atributos personalizados
  newrelic.addCustomAttribute('requestPath', req.path);
  newrelic.addCustomAttribute('userAgent', req.get('User-Agent'));
  next();
});

// Instrumentación de errores personalizados
app.use((err, req, res, next) => {
  newrelic.noticeError(err);
  res.status(500).json({ error: 'Internal Server Error' });
});
3.4.3 Configuración con DataDog
DataDog ofrece monitoreo completo de infraestructura y aplicaciones con dashboards personalizables.
Instalación del Agente DataDog
bash# Instalación del cliente DataDog
npm install dd-trace --save
javascript// tracer.js - Configuración de DataDog
const tracer = require('dd-trace').init({
  service: 'production-app',
  env: 'production',
  version: '1.0.0',
  
  // Configuración de muestreo
  sampleRate: 1.0,
  
  // Configuración de logs
  logInjection: true,
  
  // Configuración de métricas
  metrics: true,
  
  // Configuración de profiling
  profiling: true
});

module.exports = tracer;
javascript// app.js - Importar DataDog tracer
require('./tracer');
const express = require('express');
const app = express();

// Middleware para métricas personalizadas
const StatsD = require('node-statsd');
const stats = new StatsD({
  host: process.env.DATADOG_HOST || 'localhost',
  port: process.env.DATADOG_PORT || 8125
});

// Middleware de métricas de solicitudes
app.use((req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = Date.now() - start;
    stats.timing('request.duration', duration, [`method:${req.method}`, `route:${req.route?.path || 'unknown'}`]);
    stats.increment('request.count', 1, [`status:${res.statusCode}`, `method:${req.method}`]);
  });
  
  next();
});

// Métricas de base de datos
const db = require('./database');
db.on('query', (query) => {
  stats.timing('database.query.duration', query.duration);
  stats.increment('database.query.count');
});
3.4.4 Implementación con Grafana y Prometheus
Grafana y Prometheus proporcionan una solución de código abierto para monitoreo y visualización de métricas.
Configuración de Prometheus Metrics
bash# Instalación de cliente Prometheus
npm install prom-client --save
javascript// metrics.js - Configuración de métricas Prometheus
const client = require('prom-client');

// Crear registro de métricas
const register = new client.Registry();

// Métricas por defecto del sistema
client.collectDefaultMetrics({
  register,
  timeout: 10000,
  gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5]
});

// Métricas personalizadas
const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.1, 0.3, 0.5, 0.7, 1, 3, 5, 7, 10]
});

const httpRequestsTotal = new client.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code']
});

const activeConnections = new client.Gauge({
  name: 'active_connections',
  help: 'Number of active connections'
});

const databaseQueryDuration = new client.Histogram({
  name: 'database_query_duration_seconds',
  help: 'Duration of database queries in seconds',
  labelNames: ['query_type', 'table'],
  buckets: [0.01, 0.05, 0.1, 0.2, 0.5, 1, 2, 5]
});

// Registrar métricas
register.registerMetric(httpRequestDuration);
register.registerMetric(httpRequestsTotal);
register.registerMetric(activeConnections);
register.registerMetric(databaseQueryDuration);

module.exports = {
  register,
  httpRequestDuration,
  httpRequestsTotal,
  activeConnections,
  databaseQueryDuration
};
javascript// app.js - Implementación de métricas
const express = require('express');
const { register, httpRequestDuration, httpRequestsTotal, activeConnections } = require('./metrics');

const app = express();

// Middleware de métricas
app.use((req, res, next) => {
  const start = Date.now();
  
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    const route = req.route?.path || req.path;
    
    httpRequestDuration
      .labels(req.method, route, res.statusCode.toString())
      .observe(duration);
    
    httpRequestsTotal
      .labels(req.method, route, res.statusCode.toString())
      .inc();
  });
  
  next();
});

// Endpoint de métricas para Prometheus
app.get('/metrics', async (req, res) => {
  try {
    res.set('Content-Type', register.contentType);
    const metrics = await register.metrics();
    res.end(metrics);
  } catch (error) {
    res.status(500).end(error);
  }
});

// Seguimiento de conexiones activas
let connections = 0;
app.use((req, res, next) => {
  connections++;
  activeConnections.set(connections);
  
  res.on('finish', () => {
    connections--;
    activeConnections.set(connections);
  });
  
  next();
});
Configuración de Prometheus Server
yaml# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'node-app'
    static_configs:
      - targets: ['localhost:3000']
    scrape_interval: 5s
    metrics_path: /metrics

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
Configuración de Alertas
yaml# alert_rules.yml
groups:
- name: node_app_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status_code=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"

  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High response time detected"
      description: "95th percentile response time is {{ $value }} seconds"

  - alert: DatabaseSlowQueries
    expr: histogram_quantile(0.95, rate(database_query_duration_seconds_bucket[5m])) > 2
    for: 3m
    labels:
      severity: warning
    annotations:
      summary: "Slow database queries detected"
      description: "95th percentile query time is {{ $value }} seconds"
    3.4.5 Dashboard de Grafana
json{
  "dashboard": {
    "title": "Node.js Application Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{route}}"
          }
        ]
      },
      {
        "title": "Response Time (95th percentile)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status_code=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      },
      {
        "title": "Active Connections",
        "type": "singlestat",
        "targets": [
          {
            "expr": "active_connections",
            "legendFormat": "Connections"
          }
        ]
      }
    ]
  }
}
3.4.6 Script de Configuración Automatizada
bash#!/bin/bash
# setup-monitoring.sh

echo "=== Configurando Herramientas de Monitoreo ==="

# Instalar dependencias
echo "Instalando dependencias de monitoreo..."
npm install newrelic dd-trace prom-client node-statsd --save

# Crear directorio de configuración
mkdir -p config/monitoring
mkdir -p logs

# Copiar archivos de configuración
cp templates/newrelic.js ./
cp templates/tracer.js ./
cp templates/metrics.js ./

# Configurar PM2
echo "Configurando PM2..."
pm2 install pm2-server-monit

# Crear archivo de configuración de Prometheus
cat > prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'node-app'
    static_configs:
      - targets: ['localhost:3000']
    metrics_path: /metrics
EOF

echo "=== Configuración de monitoreo completada ==="
echo "No olvides configurar las variables de entorno:"
echo "- NEW_RELIC_LICENSE_KEY"
echo "- DATADOG_API_KEY"
echo "- DATADOG_HOST"
3.4.7 Variables de Entorno para Monitoreo
bash# .env.monitoring
# New Relic
NEW_RELIC_LICENSE_KEY=your_license_key_here
NEW_RELIC_APP_NAME=Production App

# DataDog
DD_API_KEY=your_datadog_api_key
DD_SERVICE=production-app
DD_ENV=production
DD_VERSION=1.0.0
DATADOG_HOST=localhost
DATADOG_PORT=8125

# Prometheus
PROMETHEUS_PORT=9090
METRICS_ENDPOINT=/metrics

# General monitoring
MONITORING_ENABLED=true
LOG_LEVEL=info
ALERT_EMAIL=admin@yourcompany.com
⚠️ IMPORTANTE: Nunca incluyas las claves de API reales en el control de versiones. Utiliza variables de entorno o servicios de gestión de secretos.
