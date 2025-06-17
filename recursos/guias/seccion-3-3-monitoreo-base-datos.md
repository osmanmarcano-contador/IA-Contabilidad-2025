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
