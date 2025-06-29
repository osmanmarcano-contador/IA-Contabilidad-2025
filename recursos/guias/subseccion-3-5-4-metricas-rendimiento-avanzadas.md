// middleware/advanced-metrics.js
const promClient = require('prom-client');
const os = require('os');
const process = require('process');
const EventEmitter = require('events');

class AdvancedMetricsCollector extends EventEmitter {
    constructor() {
        super();
        this.setupMetrics();
        this.setupCollectors();
    }

    setupMetrics() {
        // Métricas de respuesta HTTP avanzadas
        this.httpDuration = new promClient.Histogram({
            name: 'http_request_duration_advanced',
            help: 'Duración de requests HTTP con percentiles',
            labelNames: ['method', 'route', 'status_code', 'user_type'],
            buckets: [0.1, 0.5, 1, 2, 5, 10, 30]
        });

        // Métricas de base de datos
        this.dbQueryDuration = new promClient.Histogram({
            name: 'database_query_duration',
            help: 'Duración de consultas a base de datos',
            labelNames: ['operation', 'table', 'query_type'],
            buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5]
        });

        this.dbConnectionPool = new promClient.Gauge({
            name: 'database_connection_pool',
            help: 'Estado del pool de conexiones',
            labelNames: ['pool_name', 'status']
        });

        // Métricas de memoria detalladas
        this.memoryUsage = new promClient.Gauge({
            name: 'nodejs_memory_usage_detailed',
            help: 'Uso detallado de memoria Node.js',
            labelNames: ['type']
        });

        // Métricas de CPU por core
        this.cpuUsagePerCore = new promClient.Gauge({
            name: 'system_cpu_usage_per_core',
            help: 'Uso de CPU por core',
            labelNames: ['core']
        });

        // Métricas de aplicación específicas
        this.businessMetrics = new promClient.Counter({
            name: 'business_operations_total',
            help: 'Operaciones de negocio realizadas',
            labelNames: ['operation', 'result', 'user_segment']
        });

        // Métricas de cache
        this.cacheMetrics = new promClient.Counter({
            name: 'cache_operations_total',
            help: 'Operaciones de cache',
            labelNames: ['cache_name', 'operation', 'result']
        });

        // Métricas de red
        this.networkLatency = new promClient.Histogram({
            name: 'network_request_latency',
            help: 'Latencia de requests externos',
            labelNames: ['service', 'endpoint'],
            buckets: [0.1, 0.5, 1, 2, 5, 10, 30]
        });
    }

    setupCollectors() {
        // Collector de métricas del sistema cada 5 segundos
        setInterval(() => {
            this.collectSystemMetrics();
        }, 5000);

        // Collector de métricas de memoria cada 10 segundos
        setInterval(() => {
            this.collectMemoryMetrics();
        }, 10000);

        // Collector de métricas de GC
        this.setupGCMetrics();
    }

    collectSystemMetrics() {
        const cpus = os.cpus();
        cpus.forEach((cpu, index) => {
            const total = Object.values(cpu.times).reduce((acc, time) => acc + time, 0);
            const idle = cpu.times.idle;
            const usage = ((total - idle) / total) * 100;
            this.cpuUsagePerCore.set({ core: index.toString() }, usage);
        });

        // Métricas de load average
        const loadAvg = os.loadavg();
        promClient.register.getSingleMetric('nodejs_external_memory_bytes') || 
        new promClient.Gauge({
            name: 'system_load_average',
            help: 'Load average del sistema',
            labelNames: ['period']
        });
    }

    collectMemoryMetrics() {
        const memUsage = process.memoryUsage();
        
        this.memoryUsage.set({ type: 'rss' }, memUsage.rss);
        this.memoryUsage.set({ type: 'heap_used' }, memUsage.heapUsed);
        this.memoryUsage.set({ type: 'heap_total' }, memUsage.heapTotal);
        this.memoryUsage.set({ type: 'external' }, memUsage.external);
        this.memoryUsage.set({ type: 'array_buffers' }, memUsage.arrayBuffers);

        // Métricas del sistema
        const freeMem = os.freemem();
        const totalMem = os.totalmem();
        const usedMem = totalMem - freeMem;

        this.memoryUsage.set({ type: 'system_used' }, usedMem);
        this.memoryUsage.set({ type: 'system_free' }, freeMem);
        this.memoryUsage.set({ type: 'system_total' }, totalMem);
    }

    setupGCMetrics() {
        if (global.gc) {
            const gcStats = require('@nodejs/gc-stats');
            const gc = gcStats();

            gc.on('stats', (stats) => {
                const gcDuration = new promClient.Histogram({
                    name: 'nodejs_gc_duration_seconds',
                    help: 'Duración del Garbage Collection',
                    labelNames: ['gc_type']
                });

                let gcType;
                switch (stats.gctype) {
                    case 1: gcType = 'scavenge'; break;
                    case 2: gcType = 'mark_sweep_compact'; break;
                    case 4: gcType = 'incremental_marking'; break;
                    case 8: gcType = 'weak_processing'; break;
                    default: gcType = 'unknown';
                }

                gcDuration.observe({ gc_type: gcType }, stats.pause / 1000000);
            });
        }
    }

    // Middleware para métricas HTTP
    httpMetricsMiddleware() {
        return (req, res, next) => {
            const start = Date.now();
            
            res.on('finish', () => {
                const duration = (Date.now() - start) / 1000;
                const route = req.route ? req.route.path : req.path;
                const userType = req.user ? req.user.type : 'anonymous';

                this.httpDuration.observe({
                    method: req.method,
                    route: route,
                    status_code: res.statusCode.toString(),
                    user_type: userType
                }, duration);
            });

            next();
        };
    }

    // Métricas de base de datos
    trackDatabaseQuery(operation, table, queryType, duration) {
        this.dbQueryDuration.observe({
            operation,
            table,
            query_type: queryType
        }, duration);
    }

    // Métricas de negocio
    trackBusinessOperation(operation, result, userSegment = 'default') {
        this.businessMetrics.inc({
            operation,
            result,
            user_segment: userSegment
        });
    }

    // Métricas de cache
    trackCacheOperation(cacheName, operation, result) {
        this.cacheMetrics.inc({
            cache_name: cacheName,
            operation,
            result
        });
    }

    // Métricas de red
    trackNetworkRequest(service, endpoint, duration) {
        this.networkLatency.observe({
            service,
            endpoint
        }, duration);
    }
}

module.exports = AdvancedMetricsCollector;
// config/monitored-database.js
const { Pool } = require('pg');
const AdvancedMetricsCollector = require('../middleware/advanced-metrics');

class MonitoredDatabasePool {
    constructor(config, metricsCollector) {
        this.pool = new Pool(config);
        this.metrics = metricsCollector;
        this.setupPoolMonitoring();
    }

    setupPoolMonitoring() {
        // Monitorear estado del pool cada 30 segundos
        setInterval(() => {
            this.metrics.dbConnectionPool.set(
                { pool_name: 'main', status: 'total' }, 
                this.pool.totalCount
            );
            this.metrics.dbConnectionPool.set(
                { pool_name: 'main', status: 'idle' }, 
                this.pool.idleCount
            );
            this.metrics.dbConnectionPool.set(
                { pool_name: 'main', status: 'waiting' }, 
                this.pool.waitingCount
            );
        }, 30000);

        // Eventos del pool
        this.pool.on('connect', () => {
            this.metrics.trackBusinessOperation('db_connection', 'success');
        });

        this.pool.on('error', (err) => {
            this.metrics.trackBusinessOperation('db_connection', 'error');
            console.error('Database pool error:', err);
        });
    }

    async query(text, params, queryMetadata = {}) {
        const start = Date.now();
        const client = await this.pool.connect();
        
        try {
            const result = await client.query(text, params);
            const duration = (Date.now() - start) / 1000;
            
            this.metrics.trackDatabaseQuery(
                queryMetadata.operation || 'query',
                queryMetadata.table || 'unknown',
                queryMetadata.type || 'select',
                duration
            );

            return result;
        } catch (error) {
            const duration = (Date.now() - start) / 1000;
            this.metrics.trackDatabaseQuery(
                queryMetadata.operation || 'query',
                queryMetadata.table || 'unknown',
                'error',
                duration
            );
            throw error;
        } finally {
            client.release();
        }
    }
}

module.exports = MonitoredDatabasePool;
// utils/performance-profiler.js
const v8Profiler = require('v8-profiler-next');
const fs = require('fs').promises;
const path = require('path');

class PerformanceProfiler {
    constructor(metricsCollector) {
        this.metrics = metricsCollector;
        this.profiles = new Map();
        this.setupContinuousProfiling();
    }

    setupContinuousProfiling() {
        // Profiling cada 5 minutos por 30 segundos
        setInterval(() => {
            this.createCPUProfile('continuous', 30000);
        }, 5 * 60 * 1000);

        // Snapshot de heap cada 10 minutos
        setInterval(() => {
            this.createHeapSnapshot('scheduled');
        }, 10 * 60 * 1000);
    }

    async createCPUProfile(name, duration = 10000) {
        try {
            console.log(`Iniciando CPU profile: ${name}`);
            
            v8Profiler.startProfiling(name, true);
            
            setTimeout(async () => {
                const profile = v8Profiler.stopProfiling(name);
                await this.saveCPUProfile(profile, name);
                
                this.metrics.trackBusinessOperation('profiling', 'cpu_profile_created');
            }, duration);
            
        } catch (error) {
            console.error('Error creando CPU profile:', error);
            this.metrics.trackBusinessOperation('profiling', 'cpu_profile_error');
        }
    }

    async createHeapSnapshot(name) {
        try {
            console.log(`Creando heap snapshot: ${name}`);
            
            const snapshot = v8Profiler.takeSnapshot(name);
            await this.saveHeapSnapshot(snapshot, name);
            
            this.metrics.trackBusinessOperation('profiling', 'heap_snapshot_created');
            
        } catch (error) {
            console.error('Error creando heap snapshot:', error);
            this.metrics.trackBusinessOperation('profiling', 'heap_snapshot_error');
        }
    }

    async saveCPUProfile(profile, name) {
        const filename = `cpu-profile-${name}-${Date.now()}.cpuprofile`;
        const filepath = path.join('./logs/profiles', filename);
        
        const profileData = JSON.stringify(profile);
        await fs.writeFile(filepath, profileData);
        
        console.log(`CPU profile guardado: ${filepath}`);
        profile.delete();
    }

    async saveHeapSnapshot(snapshot, name) {
        const filename = `heap-snapshot-${name}-${Date.now()}.heapsnapshot`;
        const filepath = path.join('./logs/profiles', filename);
        
        const snapshotStream = fs.createWriteStream(filepath);
        
        return new Promise((resolve, reject) => {
            snapshot.export()
                .pipe(snapshotStream)
                .on('finish', () => {
                    snapshot.delete();
                    console.log(`Heap snapshot guardado: ${filepath}`);
                    resolve();
                })
                .on('error', reject);
        });
    }

    // Análisis de hot paths
    analyzeHotPaths() {
        const hotPaths = {
            routes: new Map(),
            functions: new Map(),
            queries: new Map()
        };

        // Esta información se recolectaría de los profiles
        return hotPaths;
    }
}

module.exports = PerformanceProfiler;
// middleware/user-experience-metrics.js
class UserExperienceMetrics {
    constructor(metricsCollector) {
        this.metrics = metricsCollector;
        this.userSessions = new Map();
        this.setupUserMetrics();
    }

    setupUserMetrics() {
        // Métricas de experiencia de usuario
        this.pageLoadTime = new (require('prom-client')).Histogram({
            name: 'user_page_load_time',
            help: 'Tiempo de carga de página percibido por el usuario',
            labelNames: ['page', 'user_agent', 'connection_type'],
            buckets: [0.5, 1, 2, 3, 5, 8, 10, 15, 20]
        });

        this.userInteractionTime = new (require('prom-client')).Histogram({
            name: 'user_interaction_response_time',
            help: 'Tiempo de respuesta a interacciones del usuario',
            labelNames: ['interaction_type', 'component'],
            buckets: [0.1, 0.25, 0.5, 1, 2, 5]
        });

        this.errorRate = new (require('prom-client')).Counter({
            name: 'user_errors_total',
            help: 'Errores experimentados por usuarios',
            labelNames: ['error_type', 'page', 'severity']
        });

        this.sessionMetrics = new (require('prom-client')).Summary({
            name: 'user_session_duration',
            help: 'Duración de sesiones de usuario',
            labelNames: ['user_type', 'exit_reason'],
            percentiles: [0.5, 0.9, 0.95, 0.99]
        });
    }

    // Middleware para capturar métricas del cliente
    clientMetricsMiddleware() {
        return (req, res, next) => {
            // Capturar métricas del header
            const userAgent = req.get('User-Agent') || 'unknown';
            const connectionType = req.get('Connection-Type') || 'unknown';
            
            if (req.body && req.body.metrics) {
                this.processClientMetrics(req.body.metrics, {
                    userAgent,
                    connectionType,
                    userId: req.user?.id
                });
            }

            next();
        };
    }

    processClientMetrics(clientMetrics, context) {
        // Procesar métricas de navegación
        if (clientMetrics.navigation) {
            const loadTime = clientMetrics.navigation.loadEventEnd - 
                           clientMetrics.navigation.navigationStart;
            
            this.pageLoadTime.observe({
                page: clientMetrics.page || 'unknown',
                user_agent: this.categorizeUserAgent(context.userAgent),
                connection_type: context.connectionType
            }, loadTime / 1000);
        }

        // Procesar métricas de interacción
        if (clientMetrics.interactions) {
            clientMetrics.interactions.forEach(interaction => {
                this.userInteractionTime.observe({
                    interaction_type: interaction.type,
                    component: interaction.component
                }, interaction.duration / 1000);
            });
        }

        // Procesar errores del cliente
        if (clientMetrics.errors) {
            clientMetrics.errors.forEach(error => {
                this.errorRate.inc({
                    error_type: error.type,
                    page: error.page,
                    severity: error.severity || 'medium'
                });
            });
        }
    }

    categorizeUserAgent(userAgent) {
        if (userAgent.includes('Mobile')) return 'mobile';
        if (userAgent.includes('Tablet')) return 'tablet';
        return 'desktop';
    }

    // Tracking de sesiones
    trackUserSession(userId, sessionData) {
        this.userSessions.set(userId, {
            startTime: Date.now(),
            ...sessionData
        });
    }

    endUserSession(userId, exitReason = 'normal') {
        const session = this.userSessions.get(userId);
        if (session) {
            const duration = (Date.now() - session.startTime) / 1000;
            
            this.sessionMetrics.observe({
                user_type: session.userType || 'regular',
                exit_reason: exitReason
            }, duration);

            this.userSessions.delete(userId);
        }
    }
}

module.exports = UserExperienceMetrics;
// utils/anomaly-detector.js
class AnomalyDetector {
    constructor(metricsCollector) {
        this.metrics = metricsCollector;
        this.baselines = new Map();
        this.setupAnomalyDetection();
    }

    setupAnomalyDetection() {
        // Análisis cada minuto
        setInterval(() => {
            this.detectAnomalies();
        }, 60000);

        // Actualizar baselines cada hora
        setInterval(() => {
            this.updateBaselines();
        }, 3600000);
    }

    async detectAnomalies() {
        const currentMetrics = await this.getCurrentMetrics();
        const anomalies = [];

        for (const [metricName, value] of currentMetrics) {
            const baseline = this.baselines.get(metricName);
            if (baseline && this.isAnomalous(value, baseline)) {
                anomalies.push({
                    metric: metricName,
                    current: value,
                    baseline: baseline,
                    severity: this.calculateSeverity(value, baseline),
                    timestamp: new Date()
                });
            }
        }

        if (anomalies.length > 0) {
            await this.handleAnomalies(anomalies);
        }
    }

    isAnomalous(value, baseline) {
        const threshold = baseline.stdDev * 2; // 2 desviaciones estándar
        return Math.abs(value - baseline.mean) > threshold;
    }

    calculateSeverity(value, baseline) {
        const deviation = Math.abs(value - baseline.mean) / baseline.stdDev;
        
        if (deviation > 3) return 'critical';
        if (deviation > 2.5) return 'high';
        if (deviation > 2) return 'medium';
        return 'low';
    }

    async handleAnomalies(anomalies) {
        for (const anomaly of anomalies) {
            console.warn(`Anomalía detectada: ${anomaly.metric}`, anomaly);
            
            // Registrar la anomalía como métrica
            this.metrics.trackBusinessOperation(
                'anomaly_detected', 
                anomaly.severity, 
                anomaly.metric
            );

            // Enviar alerta si es crítica
            if (anomaly.severity === 'critical') {
                await this.sendCriticalAlert(anomaly);
            }
        }
    }

    async sendCriticalAlert(anomaly) {
        // Implementar envío de alertas (email, Slack, etc.)
        console.error(`ALERTA CRÍTICA: ${anomaly.metric}`, anomaly);
    }

    async getCurrentMetrics() {
        // Obtener métricas actuales del registro de Prometheus
        const register = require('prom-client').register;
        const metrics = await register.getMetricsAsJSON();
        
        const currentMetrics = new Map();
        
        metrics.forEach(metric => {
            if (metric.values && metric.values.length > 0) {
                const value = metric.values[0].value;
                currentMetrics.set(metric.name, value);
            }
        });

        return currentMetrics;
    }

    updateBaselines() {
        // Actualizar baselines basado en datos históricos
        console.log('Actualizando baselines de métricas...');
        
        // Aquí implementarías la lógica para calcular medias y desviaciones
        // estándar basadas en datos históricos
    }
}

module.exports = AnomalyDetector;
// utils/system-resource-monitor.js
const os = require('os');
const fs = require('fs').promises;
const { execSync } = require('child_process');

class SystemResourceMonitor {
    constructor(metricsCollector) {
        this.metrics = metricsCollector;
        this.setupSystemMetrics();
    }

    setupSystemMetrics() {
        // Métricas de sistema cada 15 segundos
        setInterval(() => {
            this.collectSystemResources();
        }, 15000);

        // Métricas de disco cada minuto
        setInterval(() => {
            this.collectDiskMetrics();
        }, 60000);

        // Métricas de red cada 30 segundos
        setInterval(() => {
            this.collectNetworkMetrics();
        }, 30000);
    }

    async collectSystemResources() {
        try {
            // CPU detallado
            const cpus = os.cpus();
            let totalIdle = 0;
            let totalTick = 0;

            cpus.forEach(cpu => {
                for (const type in cpu.times) {
                    totalTick += cpu.times[type];
                }
                totalIdle += cpu.times.idle;
            });

            const idle = totalIdle / cpus.length;
            const total = totalTick / cpus.length;
            const usage = 100 - ~~(100 * idle / total);

            // Memoria del sistema
            const totalMem = os.totalmem();
            const freeMem = os.freemem();
            const usedMem = totalMem - freeMem;

            // Registrar métricas
            this.metrics.memoryUsage.set({ type: 'system_cpu_usage' }, usage);
            this.metrics.memoryUsage.set({ type: 'system_memory_used_percent' }, 
                (usedMem / totalMem) * 100);

            // Load average
            const loadAvg = os.loadavg();
            this.metrics.memoryUsage.set({ type: 'load_1m' }, loadAvg[0]);
            this.metrics.memoryUsage.set({ type: 'load_5m' }, loadAvg[1]);
            this.metrics.memoryUsage.set({ type: 'load_15m' }, loadAvg[2]);

        } catch (error) {
            console.error('Error collecting system resources:', error);
        }
    }

    async collectDiskMetrics() {
        try {
            // Uso de disco (solo en sistemas Unix)
            if (process.platform !== 'win32') {
                const diskUsage = execSync('df -h / | tail -1').toString();
                const parts = diskUsage.split(/\s+/);
                const usedPercent = parseInt(parts[4].replace('%', ''));
                
                this.metrics.memoryUsage.set({ type: 'disk_usage_percent' }, usedPercent);
            }

            // I/O de disco
            const stats = await fs.stat('./');
            this.metrics.trackBusinessOperation('disk_access', 'stat_success');

        } catch (error) {
            console.error('Error collecting disk metrics:', error);
            this.metrics.trackBusinessOperation('disk_access', 'stat_error');
        }
    }

    collectNetworkMetrics() {
        try {
            const networkInterfaces = os.networkInterfaces();
            
            Object.keys(networkInterfaces).forEach(interfaceName => {
                const interfaces = networkInterfaces[interfaceName];
                interfaces.forEach(iface => {
                    if (!iface.internal && iface.family === 'IPv4') {
                        // Aquí podrías implementar métricas más detalladas de red
                        this.metrics.trackBusinessOperation('network_interface', 'active', interfaceName);
                    }
                });
            });

        } catch (error) {
            console.error('Error collecting network metrics:', error);
        }
    }

    // Métricas de procesos
    getProcessMetrics() {
        return {
            pid: process.pid,
            uptime: process.uptime(),
            cwd: process.cwd(),
            version: process.version,
            arch: process.arch,
            platform: process.platform,
            memoryUsage: process.memoryUsage(),
            cpuUsage: process.cpuUsage()
        };
    }
}

module.exports = SystemResourceMonitor;
// config/advanced-metrics-setup.js
const AdvancedMetricsCollector = require('../middleware/advanced-metrics');
const PerformanceProfiler = require('../utils/performance-profiler');
const UserExperienceMetrics = require('../middleware/user-experience-metrics');
const AnomalyDetector = require('../utils/anomaly-detector');
const SystemResourceMonitor = require('../utils/system-resource-monitor');
const MonitoredDatabasePool = require('./monitored-database');

class MetricsOrchestrator {
    constructor(app, dbConfig) {
        this.app = app;
        this.metricsCollector = new AdvancedMetricsCollector();
        this.performanceProfiler = new PerformanceProfiler(this.metricsCollector);
        this.userMetrics = new UserExperienceMetrics(this.metricsCollector);
        this.anomalyDetector = new AnomalyDetector(this.metricsCollector);
        this.systemMonitor = new SystemResourceMonitor(this.metricsCollector);
        this.database = new MonitoredDatabasePool(dbConfig, this.metricsCollector);
        
        this.setupMiddleware();
        this.setupRoutes();
    }

    setupMiddleware() {
        // Middleware de métricas HTTP
        this.app.use(this.metricsCollector.httpMetricsMiddleware());
        
        // Middleware de métricas de usuario
        this.app.use(this.userMetrics.clientMetricsMiddleware());
    }

    setupRoutes() {
        // Endpoint para métricas de Prometheus
        this.app.get('/metrics', async (req, res) => {
            try {
                const register = require('prom-client').register;
                const metrics = await register.metrics();
                res.set('Content-Type', register.contentType);
                res.end(metrics);
            } catch (error) {
                res.status(500).end(error.toString());
            }
        });

        // Endpoint para métricas personalizadas
        this.app.get('/api/metrics/advanced', (req, res) => {
            res.json({
                system: this.systemMonitor.getProcessMetrics(),
                timestamp: new Date().toISOString(),
                uptime: process.uptime()
            });
        });

        // Endpoint para triggerar profiling manual
        this.app.post('/api/metrics/profile', (req, res) => {
            const { type, name, duration } = req.body;
            
            if (type === 'cpu') {
                this.performanceProfiler.createCPUProfile(name || 'manual', duration || 10000);
            } else if (type === 'heap') {
                this.performanceProfiler.createHeapSnapshot(name || 'manual');
            }
            
            res.json({ status: 'Profile initiated', type, name });
        });
    }

    // Métodos helper para usar en la aplicación
    trackBusinessMetric(operation, result, userSegment) {
        this.metricsCollector.trackBusinessOperation(operation, result, userSegment);
    }

    trackDatabaseQuery(operation, table, queryType, duration) {
        this.metricsCollector.trackDatabaseQuery(operation, table, queryType, duration);
    }

    trackCacheOperation(cacheName, operation, result) {
        this.metricsCollector.trackCacheOperation(cacheName, operation, result);
    }

    trackNetworkRequest(service, endpoint, duration) {
        this.metricsCollector.trackNetworkRequest(service, endpoint, duration);
    }
}

module.exports = MetricsOrchestrator;
// app.js - Ejemplo de integración
const express = require('express');
const MetricsOrchestrator = require('./config/advanced-metrics-setup');

const app = express();

// Configuración de base de datos
const dbConfig = {
    user: process.env.DB_USER,
    host: process.env.DB_HOST,
    database: process.env.DB_NAME,
    password: process.env.DB_PASSWORD,
    port: process.env.DB_PORT,
    max: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
};

// Inicializar métricas avanzadas
const metricsOrchestrator = new MetricsOrchestrator(app, dbConfig);

// Ejemplo de uso en rutas
app.get('/api/users/:id', async (req, res) => {
    const start = Date.now();
    
    try {
        // Simular consulta a base de datos
        const result = await metricsOrchestrator.database.query(
            'SELECT * FROM users WHERE id = $1',
            [req.params.id],
            {
                operation: 'select',
                table: 'users',
                type: 'single_row'
            }
        );

        // Tracking de operación de negocio
        metricsOrchestrator.trackBusinessMetric(
            'user_fetch',
            'success',
            req.user?.segment || 'anonymous'
        );

        res.json(result.rows[0]);
    } catch (error) {
        metricsOrchestrator.trackBusinessMetric('user_fetch', 'error');
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Ejemplo con cache
app.get('/api/dashboard', async (req, res) => {
    const cacheKey = `dashboard_${req.user.id}`;
    const start = Date.now();
    
    try {
        // Intentar obtener del cache
        let data = await getFromCache(cacheKey);
        
        if (data) {
            metricsOrchestrator.trackCacheOperation('dashboard', 'get', 'hit');
        } else {
            metricsOrchestrator.trackCacheOperation('dashboard', 'get', 'miss');
            
            // Obtener datos de la base de datos
            data = await getDashboardData(req.user.id);
            await setCache(cacheKey, data, 300); // 5 minutos
            
            metricsOrchestrator.trackCacheOperation('dashboard', 'set', 'success');
        }

        const duration = (Date.now() - start) / 1000;
        metricsOrchestrator.trackNetworkRequest('internal', '/api/dashboard', duration);

        res.json(data);
    } catch (error) {
        metricsOrchestrator.trackBusinessMetric('dashboard_load', 'error');
        res.status(500).json({ error: 'Failed to load dashboard' });
    }
});

module.exports = app;

// Funciones helper para cache (ejemplo)
async function getFromCache(key) {
    // Implementación de obtención de cache
    // Podría ser Redis, Memcached, etc.
    return null;
}

async function setCache(key, data, ttl) {
    // Implementación de establecimiento de cache
    return true;
}

async function getDashboardData(userId) {
    // Implementación de obtención de datos del dashboard
    return {
        user: userId,
        stats: {},
        lastUpdated: new Date()
    };
}
# docker-compose.yml - Servicios de monitoreo
version: '3.8'
services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    depends_on:
      - postgres
      - redis
    
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana-storage:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning

  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data

volumes:
  grafana-storage:
  postgres-data:
  redis-data:
  # monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'nodejs-app'
    static_configs:
      - targets: ['app:3000']
    metrics_path: '/metrics'
    scrape_interval: 10s
    scrape_timeout: 5s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
# monitoring/rules/app-alerts.yml
groups:
  - name: nodejs-app
    rules:
      - alert: HighResponseTime
        expr: histogram_quantile(0.9, http_request_duration_advanced) > 2
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Alto tiempo de respuesta detectado"
          description: "El percentil 90 del tiempo de respuesta es {{ $value }}s por más de 2 minutos"

      - alert: HighErrorRate
        expr: rate(http_request_duration_advanced{status_code=~"5.."}[5m]) > 0.1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Alta tasa de errores"
          description: "Tasa de errores 5xx: {{ $value }} por segundo"

      - alert: DatabaseSlowQueries
        expr: histogram_quantile(0.95, database_query_duration) > 1
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Consultas lentas en base de datos"
          description: "Percentil 95 de consultas: {{ $value }}s"

      - alert: HighMemoryUsage
        expr: (nodejs_memory_usage_detailed{type="heap_used"} / nodejs_memory_usage_detailed{type="heap_total"}) > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Alto uso de memoria"
          description: "Uso de heap: {{ $value }}%"

      - alert: CPUUsageHigh
        expr: system_cpu_usage_per_core > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Alto uso de CPU"
          description: "CPU core {{ $labels.core }}: {{ $value }}%"
// public/js/client-metrics.js
class ClientMetricsCollector {
    constructor(endpoint = '/api/metrics/client') {
        this.endpoint = endpoint;
        this.metrics = {
            navigation: null,
            interactions: [],
            errors: [],
            page: window.location.pathname
        };
        
        this.setupNavigationMetrics();
        this.setupInteractionMetrics();
        this.setupErrorMetrics();
        this.sendMetricsPeriodically();
    }

    setupNavigationMetrics() {
        if (window.performance && window.performance.navigation) {
            this.metrics.navigation = {
                navigationStart: performance.timing.navigationStart,
                loadEventEnd: performance.timing.loadEventEnd,
                domContentLoadedEventEnd: performance.timing.domContentLoadedEventEnd,
                connectTime: performance.timing.connectEnd - performance.timing.connectStart,
                dnsTime: performance.timing.domainLookupEnd - performance.timing.domainLookupStart,
                redirectTime: performance.timing.redirectEnd - performance.timing.redirectStart,
                responseTime: performance.timing.responseEnd - performance.timing.responseStart
            };
        }

        // Web Vitals
        this.measureWebVitals();
    }

    setupInteractionMetrics() {
        // Medir tiempo de respuesta a clicks
        document.addEventListener('click', (event) => {
            const start = performance.now();
            
            // Usar setTimeout para medir el tiempo hasta que se complete la interacción
            setTimeout(() => {
                const duration = performance.now() - start;
                
                this.metrics.interactions.push({
                    type: 'click',
                    component: event.target.tagName.toLowerCase(),
                    duration: duration,
                    timestamp: Date.now()
                });
            }, 0);
        });

        // Medir tiempo de respuesta a formularios
        document.addEventListener('submit', (event) => {
            const start = performance.now();
            
            event.target.addEventListener('load', () => {
                const duration = performance.now() - start;
                
                this.metrics.interactions.push({
                    type: 'form_submit',
                    component: 'form',
                    duration: duration,
                    timestamp: Date.now()
                });
            }, { once: true });
        });
    }

    setupErrorMetrics() {
        // Errores JavaScript
        window.addEventListener('error', (event) => {
            this.metrics.errors.push({
                type: 'javascript_error',
                message: event.message,
                filename: event.filename,
                line: event.lineno,
                column: event.colno,
                page: window.location.pathname,
                severity: 'high',
                timestamp: Date.now()
            });
        });

        // Promesas rechazadas
        window.addEventListener('unhandledrejection', (event) => {
            this.metrics.errors.push({
                type: 'unhandled_promise_rejection',
                message: event.reason.toString(),
                page: window.location.pathname,
                severity: 'medium',
                timestamp: Date.now()
            });
        });

        // Errores de recursos
        window.addEventListener('error', (event) => {
            if (event.target !== window) {
                this.metrics.errors.push({
                    type: 'resource_error',
                    resource: event.target.src || event.target.href,
                    page: window.location.pathname,
                    severity: 'low',
                    timestamp: Date.now()
                });
            }
        }, true);
    }

    measureWebVitals() {
        // Largest Contentful Paint (LCP)
        new PerformanceObserver((entryList) => {
            const entries = entryList.getEntries();
            const lastEntry = entries[entries.length - 1];
            
            this.metrics.webVitals = this.metrics.webVitals || {};
            this.metrics.webVitals.lcp = lastEntry.startTime;
        }).observe({ entryTypes: ['largest-contentful-paint'] });

        // First Input Delay (FID)
        new PerformanceObserver((entryList) => {
            const firstInput = entryList.getEntries()[0];
            
            this.metrics.webVitals = this.metrics.webVitals || {};
            this.metrics.webVitals.fid = firstInput.processingStart - firstInput.startTime;
        }).observe({ entryTypes: ['first-input'] });

        // Cumulative Layout Shift (CLS)
        let clsValue = 0;
        new PerformanceObserver((entryList) => {
            for (const entry of entryList.getEntries()) {
                if (!entry.hadRecentInput) {
                    clsValue += entry.value;
                }
            }
            
            this.metrics.webVitals = this.metrics.webVitals || {};
            this.metrics.webVitals.cls = clsValue;
        }).observe({ entryTypes: ['layout-shift'] });
    }

    sendMetricsPeriodically() {
        // Enviar métricas cada 30 segundos
        setInterval(() => {
            this.sendMetrics();
        }, 30000);

        // Enviar métricas antes de que se cierre la página
        window.addEventListener('beforeunload', () => {
            this.sendMetrics(true);
        });
    }

    sendMetrics(immediate = false) {
        if (this.hasMetricsToSend()) {
            const payload = {
                metrics: { ...this.metrics },
                url: window.location.href,
                userAgent: navigator.userAgent,
                timestamp: Date.now()
            };

            if (immediate && navigator.sendBeacon) {
                // Usar sendBeacon para envío confiable en unload
                navigator.sendBeacon(
                    this.endpoint,
                    JSON.stringify(payload)
                );
            } else {
                // Envío normal
                fetch(this.endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                }).catch(error => {
                    console.warn('Error enviando métricas:', error);
                });
            }

            // Limpiar métricas enviadas
            this.clearSentMetrics();
        }
    }

    hasMetricsToSend() {
        return this.metrics.interactions.length > 0 || 
               this.metrics.errors.length > 0 ||
               this.metrics.navigation !== null;
    }

    clearSentMetrics() {
        this.metrics.interactions = [];
        this.metrics.errors = [];
        this.metrics.navigation = null;
    }
}

// Inicializar collector cuando se carga la página
document.addEventListener('DOMContentLoaded', () => {
    window.clientMetrics = new ClientMetricsCollector();
});
// utils/advanced-logger.js
const winston = require('winston');
const DailyRotateFile = require('winston-daily-rotate-file');

class AdvancedLogger {
    constructor(metricsCollector) {
        this.metrics = metricsCollector;
        this.setupLogger();
        this.setupMetricsIntegration();
    }

    setupLogger() {
        // Configurar transportes
        const transports = [
            // Console para desarrollo
            new winston.transports.Console({
                format: winston.format.combine(
                    winston.format.colorize(),
                    winston.format.timestamp(),
                    winston.format.printf(({ timestamp, level, message, ...meta }) => {
                        return `${timestamp} [${level}]: ${message} ${Object.keys(meta).length ? JSON.stringify(meta, null, 2) : ''}`;
                    })
                )
            }),

            // Archivo para errores
            new DailyRotateFile({
                filename: 'logs/error-%DATE%.log',
                datePattern: 'YYYY-MM-DD',
                level: 'error',
                maxSize: '20m',
                maxFiles: '14d',
                format: winston.format.combine(
                    winston.format.timestamp(),
                    winston.format.json()
                )
            }),

            // Archivo para todos los logs
            new DailyRotateFile({
                filename: 'logs/combined-%DATE%.log',
                datePattern: 'YYYY-MM-DD',
                maxSize: '20m',
                maxFiles: '30d',
                format: winston.format.combine(
                    winston.format.timestamp(),
                    winston.format.json()
                )
            }),

            // Archivo para métricas de performance
            new DailyRotateFile({
                filename: 'logs/performance-%DATE%.log',
                datePattern: 'YYYY-MM-DD',
                level: 'info',
                maxSize: '50m',
                maxFiles: '7d',
                format: winston.format.combine(
                    winston.format.timestamp(),
                    winston.format.json()
                )
            })
        ];

        this.logger = winston.createLogger({
            level: process.env.LOG_LEVEL || 'info',
            transports
        });
    }

    setupMetricsIntegration() {
        // Interceptar logs para generar métricas
        const originalLog = this.logger.log.bind(this.logger);
        
        this.logger.log = (level, message, meta = {}) => {
            // Registrar métricas de logging
            this.metrics.trackBusinessOperation('log_generated', 'success', level);
            
            // Log original
            return originalLog(level, message, meta);
        };
    }

    // Métodos especializados
    logPerformance(operation, duration, metadata = {}) {
        this.logger.info('Performance metric', {
            type: 'performance',
            operation,
            duration,
            timestamp: Date.now(),
            ...metadata
        });
    }

    logError(error, context = {}) {
        this.logger.error('Application error', {
            type: 'error',
            error: {
                message: error.message,
                stack: error.stack,
                name: error.name
            },
            context,
            timestamp: Date.now()
        });

        this.metrics.trackBusinessOperation('error_logged', 'error', error.name);
    }

    logBusinessEvent(event, data = {}) {
        this.logger.info('Business event', {
            type: 'business_event',
            event,
            data,
            timestamp: Date.now()
        });

        this.metrics.trackBusinessOperation('business_event', 'logged', event);
    }

    logSecurityEvent(event, severity, details = {}) {
        this.logger.warn('Security event', {
            type: 'security',
            event,
            severity,
            details,
            timestamp: Date.now()
        });

        this.metrics.trackBusinessOperation('security_event', severity, event);
    }
}

module.exports = AdvancedLogger;
