3.3 Monitoreo de Base de Datos
El monitoreo efectivo de la base de datos es crucial para mantener el rendimiento óptimo y detectar problemas antes de que afecten a los usuarios.
3.3.1 Configuración de Monitoreo Básico
Instalación de herramientas de monitoreo:
bash# Instalar herramientas de monitoreo para PostgreSQL
npm install pg-monitor pg-promise-monitor
npm install mysql-monitor --save-dev

# Para MongoDB
npm install mongoose-monitor mongodb-monitor
Configuración inicial del monitor:
javascript// config/database-monitor.js
const monitor = require('pg-monitor');

const dbMonitorConfig = {
  // Configuración de alertas
  slowQueryThreshold: 1000, // 1 segundo
  connectionPoolWarning: 80, // 80% del pool
  deadlockDetection: true,
  
  // Configuración de logs
  logQueries: process.env.NODE_ENV !== 'production',
  logConnections: true,
  logDisconnections: true,
  
  // Métricas a capturar
  metrics: {
    queryTime: true,
    connectionCount: true,
    errorRate: true,
    slowQueries: true
  }
};

module.exports = dbMonitorConfig;
3.3.2 Monitoreo de Consultas Lentas
Detector de consultas lentas:
javascript// middleware/slow-query-detector.js
const { logger } = require('../utils/logger');

class SlowQueryDetector {
  constructor(threshold = 1000) {
    this.threshold = threshold;
    this.slowQueries = [];
  }

  monitor(query, executionTime, params = {}) {
    if (executionTime > this.threshold) {
      const slowQuery = {
        query: query,
        executionTime: executionTime,
        timestamp: new Date(),
        params: params,
        stack: new Error().stack
      };

      this.slowQueries.push(slowQuery);
      this.logSlowQuery(slowQuery);
      this.alertSlowQuery(slowQuery);
    }
  }

  logSlowQuery(queryInfo) {
    logger.warn('Consulta lenta detectada', {
      query: queryInfo.query.substring(0, 100) + '...',
      executionTime: queryInfo.executionTime,
      timestamp: queryInfo.timestamp
    });
  }

  alertSlowQuery(queryInfo) {
    if (queryInfo.executionTime > this.threshold * 3) {
      logger.error('Consulta extremadamente lenta', {
        executionTime: queryInfo.executionTime,
        query: queryInfo.query
      });
      
      // Enviar alerta crítica
      this.sendCriticalAlert(queryInfo);
    }
  }

  sendCriticalAlert(queryInfo) {
    // Implementar envío de alertas (email, Slack, etc.)
    console.error('🚨 ALERTA CRÍTICA: Consulta muy lenta detectada');
  }

  getSlowQueriesReport() {
    return {
      totalSlowQueries: this.slowQueries.length,
      averageTime: this.calculateAverageTime(),
      worstQueries: this.getWorstQueries(5)
    };
  }

  calculateAverageTime() {
    if (this.slowQueries.length === 0) return 0;
    const total = this.slowQueries.reduce((sum, q) => sum + q.executionTime, 0);
    return total / this.slowQueries.length;
  }

  getWorstQueries(limit = 5) {
    return this.slowQueries
      .sort((a, b) => b.executionTime - a.executionTime)
      .slice(0, limit);
  }
}

module.exports = SlowQueryDetector;
3.3.3 Monitoreo de Conexiones Activas
Monitor de pool de conexiones:
javascript// monitors/connection-pool-monitor.js
const { logger } = require('../utils/logger');

class ConnectionPoolMonitor {
  constructor(pool, options = {}) {
    this.pool = pool;
    this.maxConnections = options.maxConnections || 20;
    this.warningThreshold = options.warningThreshold || 0.8;
    this.checkInterval = options.checkInterval || 30000; // 30 segundos
    
    this.startMonitoring();
  }

  startMonitoring() {
    setInterval(() => {
      this.checkConnectionHealth();
    }, this.checkInterval);
  }

  checkConnectionHealth() {
    const stats = this.getConnectionStats();
    
    // Log estadísticas
    logger.info('Estadísticas de conexiones BD', stats);
    
    // Verificar alertas
    this.checkAlerts(stats);
    
    return stats;
  }

  getConnectionStats() {
    return {
      totalConnections: this.pool.totalCount || 0,
      idleConnections: this.pool.idleCount || 0,
      activeConnections: (this.pool.totalCount || 0) - (this.pool.idleCount || 0),
      waitingCount: this.pool.waitingCount || 0,
      maxConnections: this.maxConnections,
      utilizationPercentage: ((this.pool.totalCount || 0) / this.maxConnections) * 100
    };
  }

  checkAlerts(stats) {
    // Alerta por alta utilización
    if (stats.utilizationPercentage > (this.warningThreshold * 100)) {
      logger.warn('Alta utilización del pool de conexiones', {
        utilization: `${stats.utilizationPercentage.toFixed(2)}%`,
        activeConnections: stats.activeConnections,
        maxConnections: stats.maxConnections
      });
    }

    // Alerta por conexiones en espera
    if (stats.waitingCount > 5) {
      logger.warn('Múltiples conexiones en espera', {
        waitingCount: stats.waitingCount,
        suggestion: 'Considerar aumentar el pool de conexiones'
      });
    }

    // Alerta crítica por pool saturado
    if (stats.utilizationPercentage >= 95) {
      logger.error('🚨 Pool de conexiones casi saturado', stats);
      this.handlePoolSaturation(stats);
    }
  }

  handlePoolSaturation(stats) {
    // Acciones de emergencia
    logger.error('Ejecutando acciones de emergencia para pool saturado');
    
    // Opcional: cerrar conexiones idle antigas
    this.cleanupIdleConnections();
  }

  cleanupIdleConnections() {
    // Implementar limpieza de conexiones idle
    logger.info('Limpiando conexiones idle antiguas');
  }

  generateDailyReport() {
    const stats = this.getConnectionStats();
    return {
      date: new Date(),
      peakConnections: stats.totalConnections,
      averageUtilization: stats.utilizationPercentage,
      totalWarnings: this.warningCount || 0,
      recommendations: this.generateRecommendations(stats)
    };
  }

  generateRecommendations(stats) {
    const recommendations = [];
    
    if (stats.utilizationPercentage > 70) {
      recommendations.push('Considerar aumentar el tamaño del pool de conexiones');
    }
    
    if (stats.waitingCount > 0) {
      recommendations.push('Optimizar consultas para reducir tiempo de conexión');
    }
    
    return recommendations;
  }
}

module.exports = ConnectionPoolMonitor;
3.3.4 Análisis de Índices y Optimización
Analizador de rendimiento de índices:
javascript// analyzers/index-performance-analyzer.js
const { logger } = require('../utils/logger');

class IndexPerformanceAnalyzer {
  constructor(database) {
    this.db = database;
    this.analysisResults = [];
  }

  async analyzeTableIndices(tableName) {
    try {
      const indices = await this.getTableIndices(tableName);
      const usage = await this.getIndexUsageStats(tableName);
      
      const analysis = {
        tableName,
        totalIndices: indices.length,
        unusedIndices: this.findUnusedIndices(indices, usage),
        missingIndices: await this.suggestMissingIndices(tableName),
        duplicateIndices: this.findDuplicateIndices(indices),
        timestamp: new Date()
      };

      this.analysisResults.push(analysis);
      this.logAnalysisResults(analysis);
      
      return analysis;
    } catch (error) {
      logger.error('Error analizando índices', { 
        tableName, 
        error: error.message 
      });
      throw error;
    }
  }

  async getTableIndices(tableName) {
    // Para PostgreSQL
    const query = `
      SELECT 
        indexname,
        indexdef,
        tablename
      FROM pg_indexes 
      WHERE tablename = $1
      AND schemaname = 'public'
    `;
    
    return await this.db.query(query, [tableName]);
  }

  async getIndexUsageStats(tableName) {
    // Obtener estadísticas de uso de índices
    const query = `
      SELECT 
        indexrelname as index_name,
        idx_tup_read,
        idx_tup_fetch,
        idx_scan
      FROM pg_stat_user_indexes 
      WHERE relname = $1
    `;
    
    return await this.db.query(query, [tableName]);
  }

  findUnusedIndices(indices, usage) {
    return usage
      .filter(stat => stat.idx_scan === 0)
      .map(stat => ({
        indexName: stat.index_name,
        recommendation: 'Considerar eliminar índice no utilizado'
      }));
  }

  async suggestMissingIndices(tableName) {
    // Analizar consultas lentas para sugerir índices
    const slowQueries = await this.getSlowQueriesForTable(tableName);
    const suggestions = [];

    for (const query of slowQueries) {
      const missingIndex = this.analyzeQueryForMissingIndex(query);
      if (missingIndex) {
        suggestions.push(missingIndex);
      }
    }

    return suggestions;
  }

  findDuplicateIndices(indices) {
    const duplicates = [];
    
    for (let i = 0; i < indices.length; i++) {
      for (let j = i + 1; j < indices.length; j++) {
        if (this.areIndicesSimilar(indices[i], indices[j])) {
          duplicates.push({
            index1: indices[i].indexname,
            index2: indices[j].indexname,
            recommendation: 'Considerar consolidar índices similares'
          });
        }
      }
    }
    
    return duplicates;
  }

  areIndicesSimilar(index1, index2) {
    // Lógica simplificada para detectar índices similares
    return index1.indexdef.includes(index2.indexdef.substring(0, 50));
  }

  logAnalysisResults(analysis) {
    logger.info('Análisis de índices completado', {
      tabla: analysis.tableName,
      totalIndices: analysis.totalIndices,
      indicesNoUsados: analysis.unusedIndices.length,
      indicesSugeridos: analysis.missingIndices.length,
      indicesDuplicados: analysis.duplicateIndices.length
    });

    // Log recomendaciones importantes
    if (analysis.unusedIndices.length > 0) {
      logger.warn('Índices no utilizados encontrados', {
        tabla: analysis.tableName,
        indices: analysis.unusedIndices.map(i => i.indexName)
      });
    }
  }

  generateOptimizationReport() {
    return {
      summary: {
        totalTablesAnalyzed: this.analysisResults.length,
        totalUnusedIndices: this.analysisResults.reduce((sum, r) => sum + r.unusedIndices.length, 0),
        totalSuggestedIndices: this.analysisResults.reduce((sum, r) => sum + r.missingIndices.length, 0)
      },
      recommendations: this.generateGlobalRecommendations(),
      detailsByTable: this.analysisResults
    };
  }

  generateGlobalRecommendations() {
    const recommendations = [];
    
    const totalUnused = this.analysisResults.reduce((sum, r) => sum + r.unusedIndices.length, 0);
    if (totalUnused > 0) {
      recommendations.push(`Eliminar ${totalUnused} índices no utilizados para mejorar rendimiento de escritura`);
    }
    
    const totalSuggested = this.analysisResults.reduce((sum, r) => sum + r.missingIndices.length, 0);
    if (totalSuggested > 0) {
      recommendations.push(`Considerar crear ${totalSuggested} índices sugeridos para mejorar consultas`);
    }
    
    return recommendations;
  }
}

module.exports = IndexPerformanceAnalyzer;
3.3.5 Dashboard de Métricas de Base de Datos
Recolector de métricas:
javascript// collectors/database-metrics-collector.js
const { logger } = require('../utils/logger');

class DatabaseMetricsCollector {
  constructor(database) {
    this.db = database;
    this.metrics = {
      queries: [],
      connections: [],
      performance: [],
      errors: []
    };
    
    this.startCollection();
  }

  startCollection() {
    // Recolectar métricas cada 30 segundos
    setInterval(() => {
      this.collectMetrics();
    }, 30000);
    
    // Generar reporte cada hora
    setInterval(() => {
      this.generateHourlyReport();
    }, 3600000);
  }

  async collectMetrics() {
    try {
      const timestamp = new Date();
      
      // Métricas de consultas
      const queryMetrics = await this.collectQueryMetrics();
      this.metrics.queries.push({ timestamp, ...queryMetrics });
      
      // Métricas de conexiones
      const connectionMetrics = await this.collectConnectionMetrics();
      this.metrics.connections.push({ timestamp, ...connectionMetrics });
      
      // Métricas de rendimiento
      const performanceMetrics = await this.collectPerformanceMetrics();
      this.metrics.performance.push({ timestamp, ...performanceMetrics });
      
      // Limpiar métricas antiguas (mantener solo últimas 24 horas)
      this.cleanupOldMetrics();
      
    } catch (error) {
      logger.error('Error recolectando métricas de BD', { error: error.message });
    }
  }

  async collectQueryMetrics() {
    // Para PostgreSQL
    const queryStats = await this.db.query(`
      SELECT 
        count(*) as total_queries,
        avg(mean_time) as avg_query_time,
        max(max_time) as max_query_time,
        sum(calls) as total_calls
      FROM pg_stat_statements
      WHERE query NOT LIKE '%pg_stat_statements%'
    `);

    return {
      totalQueries: queryStats[0]?.total_queries || 0,
      avgQueryTime: queryStats[0]?.avg_query_time || 0,
      maxQueryTime: queryStats[0]?.max_query_time || 0,
      totalCalls: queryStats[0]?.total_calls || 0
    };
  }

  async collectConnectionMetrics() {
    const connectionStats = await this.db.query(`
      SELECT 
        count(*) as active_connections,
        count(*) filter (where state = 'idle') as idle_connections,
        count(*) filter (where state = 'active') as running_connections
      FROM pg_stat_activity
      WHERE pid <> pg_backend_pid()
    `);

    return {
      activeConnections: connectionStats[0]?.active_connections || 0,
      idleConnections: connectionStats[0]?.idle_connections || 0,
      runningConnections: connectionStats[0]?.running_connections || 0
    };
  }

  async collectPerformanceMetrics() {
    const perfStats = await this.db.query(`
      SELECT 
        sum(heap_blks_read) as disk_reads,
        sum(heap_blks_hit) as cache_hits,
        round(
          sum(heap_blks_hit) * 100.0 / 
          nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2
        ) as cache_hit_ratio
      FROM pg_statio_user_tables
    `);

    return {
      diskReads: perfStats[0]?.disk_reads || 0,
      cacheHits: perfStats[0]?.cache_hits || 0,
      cacheHitRatio: perfStats[0]?.cache_hit_ratio || 0
    };
  }

  cleanupOldMetrics() {
    const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    
    Object.keys(this.metrics).forEach(key => {
      this.metrics[key] = this.metrics[key].filter(
        metric => metric.timestamp > twentyFourHoursAgo
      );
    });
  }

  generateHourlyReport() {
    const report = {
      timestamp: new Date(),
      summary: this.generateSummary(),
      alerts: this.checkAlerts(),
      recommendations: this.generateRecommendations()
    };

    logger.info('Reporte horario de BD', report.summary);
    
    if (report.alerts.length > 0) {
      logger.warn('Alertas de BD detectadas', { alerts: report.alerts });
    }

    return report;
  }

  generateSummary() {
    const lastHourMetrics = this.getLastHourMetrics();
    
    return {
      avgQueryTime: this.calculateAverage(lastHourMetrics.queries, 'avgQueryTime'),
      maxConnections: this.calculateMax(lastHourMetrics.connections, 'activeConnections'),
      avgCacheHitRatio: this.calculateAverage(lastHourMetrics.performance, 'cacheHitRatio'),
      totalQueries: this.calculateSum(lastHourMetrics.queries, 'totalQueries')
    };
  }

  getLastHourMetrics() {
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
    
    return {
      queries: this.metrics.queries.filter(m => m.timestamp > oneHourAgo),
      connections: this.metrics.connections.filter(m => m.timestamp > oneHourAgo),
      performance: this.metrics.performance.filter(m => m.timestamp > oneHourAgo)
    };
  }

  checkAlerts() {
    const alerts = [];
    const latest = this.getLatestMetrics();
    
    // Alerta por consultas lentas
    if (latest.query?.avgQueryTime > 1000) {
      alerts.push({
        type: 'SLOW_QUERIES',
        message: `Tiempo promedio de consulta alto: ${latest.query.avgQueryTime}ms`
      });
    }
    
    // Alerta por muchas conexiones
    if (latest.connection?.activeConnections > 50) {
      alerts.push({
        type: 'HIGH_CONNECTIONS',
        message: `Alto número de conexiones activas: ${latest.connection.activeConnections}`
      });
    }
    
    // Alerta por bajo cache hit ratio
    if (latest.performance?.cacheHitRatio < 90) {
      alerts.push({
        type: 'LOW_CACHE_HIT',
        message: `Bajo ratio de cache hit: ${latest.performance.cacheHitRatio}%`
      });
    }
    
    return alerts;
  }

  getLatestMetrics() {
    return {
      query: this.metrics.queries[this.metrics.queries.length - 1],
      connection: this.metrics.connections[this.metrics.connections.length - 1],
      performance: this.metrics.performance[this.metrics.performance.length - 1]
    };
  }

  // Métodos auxiliares para cálculos
  calculateAverage(metrics, field) {
    if (metrics.length === 0) return 0;
    const sum = metrics.reduce((acc, m) => acc + (m[field] || 0), 0);
    return sum / metrics.length;
  }

  calculateMax(metrics, field) {
    if (metrics.length === 0) return 0;
    return Math.max(...metrics.map(m => m[field] || 0));
  }

  calculateSum(metrics, field) {
    return metrics.reduce((acc, m) => acc + (m[field] || 0), 0);
  }
}

module.exports = DatabaseMetricsCollector;
3.3.6 Script de Inicialización
Configuración automática del monitoreo:
javascript// scripts/setup-database-monitoring.js
const SlowQueryDetector = require('../middleware/slow-query-detector');
const ConnectionPoolMonitor = require('../monitors/connection-pool-monitor');
const IndexPerformanceAnalyzer = require('../analyzers/index-performance-analyzer');
const DatabaseMetricsCollector = require('../collectors/database-metrics-collector');
const { logger } = require('../utils/logger');

class DatabaseMonitoringSetup {
  constructor(database, pool) {
    this.db = database;
    this.pool = pool;
    this.monitors = {};
  }

  async initializeMonitoring() {
    try {
      logger.info('Inicializando monitoreo de base de datos...');

      // Configurar detector de consultas lentas
      this.monitors.slowQueryDetector = new SlowQueryDetector(1000);
      
      // Configurar monitor de conexiones
      this.monitors.connectionMonitor = new ConnectionPoolMonitor(this.pool, {
        maxConnections: 20,
        warningThreshold: 0.8,
        checkInterval: 30000
      });
      
      // Configurar analizador de índices
      this.monitors.indexAnalyzer = new IndexPerformanceAnalyzer(this.db);
      
      // Configurar recolector de métricas
      this.monitors.metricsCollector = new DatabaseMetricsCollector(this.db);
      
      // Programar análisis periódicos
      this.schedulePeriodicAnalysis();
      
      logger.info('✅ Monitoreo de base de datos inicializado correctamente');
      
      return this.monitors;
      
    } catch (error) {
      logger.error('❌ Error inicializando monitoreo de BD', { 
        error: error.message 
      });
      throw error;
    }
  }

  schedulePeriodicAnalysis() {
    // Análisis de índices diario
    setInterval(async () => {
      try {
        logger.info('Ejecutando análisis diario de índices...');
        const tables = await this.getTableNames();
        
        for (const table of tables) {
          await this.monitors.indexAnalyzer.analyzeTableIndices(table);
        }
        
        const report = this.monitors.indexAnalyzer.generateOptimizationReport();
        logger.info('Análisis de índices completado', report.summary);
        
      } catch (error) {
        logger.error('Error en análisis periódico de índices', { 
          error: error.message 
        });
      }
    }, 24 * 60 * 60 * 1000); // 24 horas
  }

  async getTableNames() {
    const result = await this.db.query(`
      SELECT tablename 
      FROM pg_tables 
      WHERE schemaname = 'public'
      AND tablename NOT LIKE 'pg_%'
    `);
    
    return result.map(row => row.tablename);
  }

  getMonitoringStatus() {
    return {
      slowQueryDetector: !!this.monitors.slowQueryDetector,
      connectionMonitor: !!this.monitors.connectionMonitor,
      indexAnalyzer: !!this.monitors.indexAnalyzer,
      metricsCollector: !!this.monitors.metricsCollector,
      status: 'active',
      initializedAt: new Date()
    };
  }

  async generateFullReport() {
    const report = {
      timestamp: new Date(),
      slowQueries: this.monitors.slowQueryDetector?.getSlowQueriesReport(),
      connections: this.monitors.connectionMonitor?.generateDailyReport(),
      indexOptimization: this.monitors.indexAnalyzer?.generateOptimizationReport(),
      metrics: this.monitors.metricsCollector?.generateHourlyReport()
    };

    logger.info('Reporte completo de monitoreo BD generado', {
      slowQueries: report.slowQueries?.totalSlowQueries || 0,
      recommendations: report.indexOptimization?.recommendations?.length || 0
    });

    return report;
  }
}

module.exports = DatabaseMonitoringSetup;
