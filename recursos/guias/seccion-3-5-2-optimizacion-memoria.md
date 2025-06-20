3.5.2 Optimización de Memoria
La optimización de memoria es crucial para mantener el rendimiento óptimo de aplicaciones Node.js en producción. Una gestión inadecuada de la memoria puede resultar en memory leaks, degradación del rendimiento y caídas inesperadas del sistema.
Análisis del Uso de Memoria
Herramientas de Análisis Integradas:
javascript// memory-analyzer.js
const v8 = require('v8');
const fs = require('fs');
const path = require('path');

class MemoryAnalyzer {
    constructor() {
        this.snapshots = [];
        this.memoryThreshold = 512 * 1024 * 1024; // 512MB
        this.gcThreshold = 0.8; // 80% de uso de memoria
    }

    // Obtener estadísticas de memoria detalladas
    getMemoryStats() {
        const memUsage = process.memoryUsage();
        const heapStats = v8.getHeapStatistics();
        
        return {
            rss: this.formatBytes(memUsage.rss),
            heapUsed: this.formatBytes(memUsage.heapUsed),
            heapTotal: this.formatBytes(memUsage.heapTotal),
            external: this.formatBytes(memUsage.external),
            arrayBuffers: this.formatBytes(memUsage.arrayBuffers),
            heapSizeLimit: this.formatBytes(heapStats.heap_size_limit),
            totalHeapSize: this.formatBytes(heapStats.total_heap_size),
            usedHeapSize: this.formatBytes(heapStats.used_heap_size),
            totalAvailableSize: this.formatBytes(heapStats.total_available_size),
            mallocedMemory: this.formatBytes(heapStats.malloced_memory),
            peakMallocedMemory: this.formatBytes(heapStats.peak_malloced_memory),
            timestamp: new Date().toISOString()
        };
    }

    // Crear heap snapshot
    createHeapSnapshot(filename) {
        const snapshotPath = path.join(__dirname, 'snapshots', `${filename}.heapsnapshot`);
        
        try {
            // Asegurar que el directorio existe
            if (!fs.existsSync(path.dirname(snapshotPath))) {
                fs.mkdirSync(path.dirname(snapshotPath), { recursive: true });
            }

            const snapshot = v8.writeHeapSnapshot(snapshotPath);
            console.log(`Heap snapshot creado: ${snapshot}`);
            
            this.snapshots.push({
                filename: snapshot,
                timestamp: new Date().toISOString(),
                memoryStats: this.getMemoryStats()
            });

            return snapshot;
        } catch (error) {
            console.error('Error creando heap snapshot:', error);
            throw error;
        }
    }

    // Monitoreo continuo de memoria
    startMemoryMonitoring(interval = 30000) {
        setInterval(() => {
            const stats = this.getMemoryStats();
            const heapUsedMB = this.parseBytes(stats.heapUsed);
            const heapTotalMB = this.parseBytes(stats.heapTotal);
            const usagePercent = (heapUsedMB / heapTotalMB) * 100;

            console.log(`[MEMORY] Heap: ${stats.heapUsed}/${stats.heapTotal} (${usagePercent.toFixed(2)}%)`);
            console.log(`[MEMORY] RSS: ${stats.rss}, External: ${stats.external}`);

            // Alerta si el uso de memoria es alto
            if (usagePercent > this.gcThreshold * 100) {
                console.warn(`⚠️  Alto uso de memoria detectado: ${usagePercent.toFixed(2)}%`);
                this.triggerGarbageCollection();
            }

            // Crear snapshot automático si se excede el umbral
            if (heapUsedMB > this.memoryThreshold / (1024 * 1024)) {
                const snapshotName = `auto-snapshot-${Date.now()}`;
                this.createHeapSnapshot(snapshotName);
            }
        }, interval);
    }

    // Forzar garbage collection
    triggerGarbageCollection() {
        if (global.gc) {
            console.log('🗑️  Ejecutando garbage collection manual...');
            const before = process.memoryUsage().heapUsed;
            global.gc();
            const after = process.memoryUsage().heapUsed;
            const freed = before - after;
            console.log(`✅ Memoria liberada: ${this.formatBytes(freed)}`);
        } else {
            console.warn('Garbage collection manual no disponible. Ejecute con --expose-gc');
        }
    }

    // Formatear bytes a formato legible
    formatBytes(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    // Parsear string de bytes a número
    parseBytes(bytesString) {
        const match = bytesString.match(/^([\d.]+)\s*(\w+)$/);
        if (!match) return 0;
        
        const value = parseFloat(match[1]);
        const unit = match[2].toUpperCase();
        
        const multipliers = {
            'BYTES': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024
        };
        
        return value * (multipliers[unit] || 1);
    }

    // Generar reporte de memoria
    generateMemoryReport() {
        const stats = this.getMemoryStats();
        const report = {
            timestamp: new Date().toISOString(),
            memoryUsage: stats,
            snapshots: this.snapshots.slice(-5), // Últimos 5 snapshots
            recommendations: this.getOptimizationRecommendations(stats)
        };

        const reportPath = path.join(__dirname, 'reports', `memory-report-${Date.now()}.json`);
        
        try {
            if (!fs.existsSync(path.dirname(reportPath))) {
                fs.mkdirSync(path.dirname(reportPath), { recursive: true });
            }
            
            fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
            console.log(`📊 Reporte de memoria generado: ${reportPath}`);
            return reportPath;
        } catch (error) {
            console.error('Error generando reporte de memoria:', error);
            throw error;
        }
    }

    // Obtener recomendaciones de optimización
    getOptimizationRecommendations(stats) {
        const recommendations = [];
        const heapUsedMB = this.parseBytes(stats.heapUsed);
        const heapTotalMB = this.parseBytes(stats.heapTotal);
        const usagePercent = (heapUsedMB / heapTotalMB) * 100;

        if (usagePercent > 90) {
            recommendations.push({
                level: 'critical',
                message: 'Uso de memoria crítico (>90%). Considere optimizar el código o aumentar la memoria disponible.',
                action: 'Revisar memory leaks y optimizar estructuras de datos'
            });
        } else if (usagePercent > 70) {
            recommendations.push({
                level: 'warning',
                message: 'Uso de memoria alto (>70%). Monitorear de cerca.',
                action: 'Analizar patrones de uso y considerar optimizaciones'
            });
        }

        if (this.parseBytes(stats.external) > 100 * 1024 * 1024) { // 100MB
            recommendations.push({
                level: 'info',
                message: 'Alto uso de memoria externa detectado.',
                action: 'Revisar buffers y recursos externos'
            });
        }

        return recommendations;
    }
}

module.exports = MemoryAnalyzer;
Optimización de Estructuras de Datos
Gestión Eficiente de Objetos y Arrays:
javascript// data-optimization.js
class DataOptimizer {
    constructor() {
        this.cache = new Map();
        this.weakCache = new WeakMap();
        this.objectPool = new Map();
    }

    // Pool de objetos para reutilización
    createObjectPool(className, createFn, resetFn, initialSize = 10) {
        const pool = [];
        
        for (let i = 0; i < initialSize; i++) {
            pool.push(createFn());
        }
        
        this.objectPool.set(className, {
            pool,
            createFn,
            resetFn,
            inUse: new Set()
        });
        
        return {
            acquire: () => this.acquireObject(className),
            release: (obj) => this.releaseObject(className, obj),
            getStats: () => ({
                available: pool.length,
                inUse: this.objectPool.get(className).inUse.size
            })
        };
    }

    acquireObject(className) {
        const poolData = this.objectPool.get(className);
        if (!poolData) {
            throw new Error(`Object pool '${className}' no existe`);
        }

        let obj;
        if (poolData.pool.length > 0) {
            obj = poolData.pool.pop();
        } else {
            obj = poolData.createFn();
            console.log(`🔄 Creando nuevo objeto ${className} (pool agotado)`);
        }

        poolData.inUse.add(obj);
        return obj;
    }

    releaseObject(className, obj) {
        const poolData = this.objectPool.get(className);
        if (!poolData || !poolData.inUse.has(obj)) {
            return false;
        }

        poolData.inUse.delete(obj);
        poolData.resetFn(obj);
        poolData.pool.push(obj);
        return true;
    }

    // Optimización de arrays grandes
    optimizeArrayOperations() {
        return {
            // Filtrado eficiente para arrays grandes
            efficientFilter: (arr, predicate, chunkSize = 10000) => {
                if (arr.length <= chunkSize) {
                    return arr.filter(predicate);
                }

                const result = [];
                for (let i = 0; i < arr.length; i += chunkSize) {
                    const chunk = arr.slice(i, i + chunkSize);
                    result.push(...chunk.filter(predicate));
                    
                    // Permitir que el event loop procese otras tareas
                    if (i % (chunkSize * 10) === 0) {
                        await new Promise(resolve => setImmediate(resolve));
                    }
                }
                return result;
            },

            // Mapeo eficiente para arrays grandes
            efficientMap: async (arr, mapper, chunkSize = 10000) => {
                if (arr.length <= chunkSize) {
                    return arr.map(mapper);
                }

                const result = [];
                for (let i = 0; i < arr.length; i += chunkSize) {
                    const chunk = arr.slice(i, i + chunkSize);
                    result.push(...chunk.map(mapper));
                    
                    // Permitir que el event loop procese otras tareas
                    if (i % (chunkSize * 10) === 0) {
                        await new Promise(resolve => setImmediate(resolve));
                    }
                }
                return result;
            },

            // Reducción eficiente para arrays grandes
            efficientReduce: async (arr, reducer, initialValue, chunkSize = 10000) => {
                if (arr.length <= chunkSize) {
                    return arr.reduce(reducer, initialValue);
                }

                let accumulator = initialValue;
                for (let i = 0; i < arr.length; i += chunkSize) {
                    const chunk = arr.slice(i, i + chunkSize);
                    accumulator = chunk.reduce(reducer, accumulator);
                    
                    // Permitir que el event loop procese otras tareas
                    if (i % (chunkSize * 10) === 0) {
                        await new Promise(resolve => setImmediate(resolve));
                    }
                }
                return accumulator;
            }
        };
    }

    // Cache con límite de tamaño
    createLimitedCache(maxSize = 1000, ttl = 3600000) { // 1 hora por defecto
        const cache = new Map();
        const timeouts = new Map();

        return {
            set: (key, value) => {
                // Eliminar el más antiguo si se alcanza el límite
                if (cache.size >= maxSize) {
                    const firstKey = cache.keys().next().value;
                    this.clearCacheItem(cache, timeouts, firstKey);
                }

                // Limpiar timeout existente
                if (timeouts.has(key)) {
                    clearTimeout(timeouts.get(key));
                }

                cache.set(key, value);

                // Configurar timeout para TTL
                if (ttl > 0) {
                    const timeout = setTimeout(() => {
                        this.clearCacheItem(cache, timeouts, key);
                    }, ttl);
                    timeouts.set(key, timeout);
                }
            },

            get: (key) => cache.get(key),
            has: (key) => cache.has(key),
            delete: (key) => this.clearCacheItem(cache, timeouts, key),
            clear: () => {
                timeouts.forEach(timeout => clearTimeout(timeout));
                cache.clear();
                timeouts.clear();
            },
            size: () => cache.size,
            stats: () => ({
                size: cache.size,
                maxSize: maxSize,
                utilization: (cache.size / maxSize * 100).toFixed(2) + '%'
            })
        };
    }

    clearCacheItem(cache, timeouts, key) {
        if (timeouts.has(key)) {
            clearTimeout(timeouts.get(key));
            timeouts.delete(key);
        }
        return cache.delete(key);
    }

    // Optimización de strings
    optimizeStringOperations() {
        return {
            // StringBuilder para concatenación eficiente
            StringBuilder: class {
                constructor() {
                    this.parts = [];
                }

                append(str) {
                    this.parts.push(str);
                    return this;
                }

                toString() {
                    return this.parts.join('');
                }

                clear() {
                    this.parts.length = 0;
                    return this;
                }

                length() {
                    return this.parts.reduce((total, part) => total + part.length, 0);
                }
            },

            // Intern strings para evitar duplicados
            stringInterner: (() => {
                const internedStrings = new Map();
                
                return {
                    intern: (str) => {
                        if (internedStrings.has(str)) {
                            return internedStrings.get(str);
                        }
                        internedStrings.set(str, str);
                        return str;
                    },
                    clear: () => internedStrings.clear(),
                    size: () => internedStrings.size
                };
            })()
        };
    }
}

module.exports = DataOptimizer;
Detección y Prevención de Memory Leaks
Sistema de Detección de Fugas de Memoria:
javascript// memory-leak-detector.js
const EventEmitter = require('events');

class MemoryLeakDetector extends EventEmitter {
    constructor(options = {}) {
        super();
        this.options = {
            checkInterval: options.checkInterval || 60000, // 1 minuto
            maxHeapGrowth: options.maxHeapGrowth || 50 * 1024 * 1024, // 50MB
            maxSamples: options.maxSamples || 10,
            alertThreshold: options.alertThreshold || 3,
            ...options
        };
        
        this.samples = [];
        this.listeners = new Map();
        this.timers = new Set();
        this.intervals = new Set();
        this.isMonitoring = false;
    }

    startMonitoring() {
        if (this.isMonitoring) {
            return;
        }

        this.isMonitoring = true;
        console.log('🔍 Iniciando detección de memory leaks...');

        // Monitorear crecimiento de heap
        this.heapMonitor = setInterval(() => {
            this.checkHeapGrowth();
        }, this.options.checkInterval);

        // Monitorear event listeners
        this.listenerMonitor = setInterval(() => {
            this.checkEventListeners();
        }, this.options.checkInterval * 2);

        // Monitorear timers
        this.timerMonitor = setInterval(() => {
            this.checkTimers();
        }, this.options.checkInterval * 3);
    }

    stopMonitoring() {
        if (!this.isMonitoring) {
            return;
        }

        this.isMonitoring = false;
        clearInterval(this.heapMonitor);
        clearInterval(this.listenerMonitor);
        clearInterval(this.timerMonitor);
        
        console.log('⏹️  Detección de memory leaks detenida');
    }

    checkHeapGrowth() {
        const memUsage = process.memoryUsage();
        const sample = {
            timestamp: Date.now(),
            heapUsed: memUsage.heapUsed,
            heapTotal: memUsage.heapTotal,
            rss: memUsage.rss,
            external: memUsage.external
        };

        this.samples.push(sample);

        // Mantener solo las últimas muestras
        if (this.samples.length > this.options.maxSamples) {
            this.samples.shift();
        }

        // Analizar tendencia de crecimiento
        if (this.samples.length >= this.options.alertThreshold) {
            this.analyzeHeapTrend();
        }
    }

    analyzeHeapTrend() {
        const recentSamples = this.samples.slice(-this.options.alertThreshold);
        const oldestSample = recentSamples[0];
        const newestSample = recentSamples[recentSamples.length - 1];
        
        const heapGrowth = newestSample.heapUsed - oldestSample.heapUsed;
        const timeSpan = newestSample.timestamp - oldestSample.timestamp;
        const growthRate = heapGrowth / (timeSpan / 1000); // bytes per second

        if (heapGrowth > this.options.maxHeapGrowth) {
            const leak = {
                type: 'heap_growth',
                growth: heapGrowth,
                growthRate: growthRate,
                timeSpan: timeSpan,
                samples: recentSamples,
                severity: this.calculateSeverity(heapGrowth, growthRate)
            };

            this.emit('memoryLeak', leak);
            console.warn(`🚨 Posible memory leak detectado: ${this.formatBytes(heapGrowth)} en ${timeSpan/1000}s`);
        }
    }

    checkEventListeners() {
        const currentListeners = new Map();
        
        // Obtener listeners del process
        const processListeners = process.eventNames();
        processListeners.forEach(event => {
            const count = process.listenerCount(event);
            currentListeners.set(`process.${event}`, count);
        });

        // Comparar con estado anterior
        this.listeners.forEach((prevCount, event) => {
            const currentCount = currentListeners.get(event) || 0;
            const growth = currentCount - prevCount;
            
            if (growth > 10) { // Más de 10 listeners nuevos
                const leak = {
                    type: 'event_listeners',
                    event: event,
                    growth: growth,
                    currentCount: currentCount,
                    previousCount: prevCount,
                    severity: growth > 50 ? 'high' : growth > 20 ? 'medium' : 'low'
                };

                this.emit('memoryLeak', leak);
                console.warn(`🚨 Crecimiento de event listeners: ${event} (+${growth})`);
            }
        });

        this.listeners = currentListeners;
    }

    checkTimers() {
        // Esta función requiere instrumentación adicional
        // En producción, se podría usar async_hooks para rastrear timers
        const activeHandles = process._getActiveHandles();
        const activeRequests = process._getActiveRequests();
        
        if (activeHandles.length > 100) {
            console.warn(`⚠️  Muchos handles activos: ${activeHandles.length}`);
        }
        
        if (activeRequests.length > 50) {
            console.warn(`⚠️  Muchas requests activas: ${activeRequests.length}`);
        }
    }

    calculateSeverity(heapGrowth, growthRate) {
        const growthMB = heapGrowth / (1024 * 1024);
        const rateMBps = growthRate / (1024 * 1024);
        
        if (growthMB > 100 || rateMBps > 5) {
            return 'critical';
        } else if (growthMB > 50 || rateMBps > 2) {
            return 'high';
        } else if (growthMB > 20 || rateMBps > 1) {
            return 'medium';
        } else {
            return 'low';
        }
    }

    formatBytes(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    // Instrumentar función para detectar leaks
    instrumentFunction(fn, name) {
        const detector = this;
        
        return function(...args) {
            const beforeHeap = process.memoryUsage().heapUsed;
            const result = fn.apply(this, args);
            
            // Si es una promesa, esperar a que se resuelva
            if (result && typeof result.then === 'function') {
                return result.then(value => {
                    detector.checkFunctionMemoryUsage(name, beforeHeap);
                    return value;
                }).catch(error => {
                    detector.checkFunctionMemoryUsage(name, beforeHeap);
                    throw error;
                });
            } else {
                detector.checkFunctionMemoryUsage(name, beforeHeap);
                return result;
            }
        };
    }

    checkFunctionMemoryUsage(functionName, beforeHeap) {
        setImmediate(() => {
            const afterHeap = process.memoryUsage().heapUsed;
            const memoryDelta = afterHeap - beforeHeap;
            
            if (memoryDelta > 10 * 1024 * 1024) { // 10MB
                console.warn(`⚠️  Función ${functionName} aumentó memoria en ${this.formatBytes(memoryDelta)}`);
            }
        });
    }

    generateLeakReport() {
        return {
            timestamp: new Date().toISOString(),
            isMonitoring: this.isMonitoring,
            samples: this.samples,
            currentMemory: process.memoryUsage(),
            listeners: Object.fromEntries(this.listeners),
            activeHandles: process._getActiveHandles().length,
            activeRequests: process._getActiveRequests().length,
            recommendations: this.getLeakRecommendations()
        };
    }

    getLeakRecommendations() {
        const recommendations = [];
        const currentMem = process.memoryUsage();
        
        if (currentMem.heapUsed > 500 * 1024 * 1024) { // 500MB
            recommendations.push({
                type: 'high_memory_usage',
                message: 'Uso de memoria alto. Considere crear heap snapshots para análisis.',
                action: 'Ejecutar análisis de heap con Chrome DevTools'
            });
        }
        
        if (this.listeners.size > 50) {
            recommendations.push({
                type: 'many_listeners',
                message: 'Muchos event listeners activos.',
                action: 'Revisar que los listeners se eliminen correctamente'
            });
        }
        
        return recommendations;
    }
}

module.exports = MemoryLeakDetector;
Configuración de Límites de Memoria
Configuración de Node.js y V8:
javascript// memory-limits.js
class MemoryLimitsManager {
    constructor() {
        this.defaultLimits = {
            maxOldSpaceSize: 4096, // 4GB
            maxSemiSpaceSize: 256,  // 256MB
            maxExecutableSize: 256  // 256MB
        };
    }

    // Configurar límites de memoria para V8
    configureV8Limits(options = {}) {
        const limits = { ...this.defaultLimits, ...options };
        
        console.log('⚙️  Configurando límites de memoria V8:');
        console.log(`   - Max Old Space Size: ${limits.maxOldSpaceSize}MB`);
        console.log(`   - Max Semi Space Size: ${limits.maxSemiSpaceSize}MB`);
        console.log(`   - Max Executable Size: ${limits.maxExecutableSize}MB`);

        // Estos límites deben configurarse al iniciar Node.js
        // Ejemplo: node --max-old-space-size=4096 --max-semi-space-size=256 app.js
        
        return {
            nodeFlags: [
                `--max-old-space-size=${limits.maxOldSpaceSize}`,
                `--max-semi-space-size=${limits.maxSemiSpaceSize}`,
                `--max-executable-size=${limits.maxExecutableSize}`,
                '--optimize-for-size',
                '--gc-interval=100'
            ],
            limits
        };
    }

    // Monitorear límites de memoria
    monitorMemoryLimits() {
        const heapStats = require('v8').getHeapStatistics();
        const memUsage = process.memoryUsage();
        
        const limits = {
            heapSizeLimit: heapStats.heap_size_limit,
            totalHeapSize: heapStats.total_heap_size,
            usedHeapSize: heapStats.used_heap_size,
            totalAvailableSize: heapStats.total_available_size
        };

        const usage = {
            heapUsagePercent: (memUsage.heapUsed / limits.heapSizeLimit * 100).toFixed(2),
            totalUsagePercent: (heapStats.total_heap_size / limits.heapSizeLimit * 100).toFixed(2),
            availableMemory: limits.totalAvailableSize,
            criticalLevel: memUsage.heapUsed > (limits.heapSizeLimit * 0.9)
        };

        if (usage.criticalLevel) {
            console.error(`🚨 CRÍTICO: Uso de memoria cerca del límite (${usage.heapUsagePercent}%)`);
            this.handleCriticalMemoryUsage();
        }

        return { limits, usage, memUsage };
    }

    // Manejar uso crítico de memoria
    handleCriticalMemoryUsage() {
        console.log('🚨 Ejecutando acciones de emergencia por memoria crítica...');
        
        // Limpiar caches
        if (global.gc) {
            global.gc();
            console.log('✅ Garbage collection ejecutado');
        }
        
        // Emitir evento para que la aplicación pueda tomar acciones
        process.emit('criticalMemoryUsage', this.monitorMemoryLimits());
        
        // En casos extremos, considerar restart graceful
        if (process.memoryUsage().heapUsed > (require('v8').getHeapStatistics().heap_size_limit * 0.95)) {
            console.error('🚨 Memoria extremadamente crítica. Considere reinicio de aplicación.');
            process.emit('extremeMemoryUsage');
        }
    }

    // Configurar alertas de memoria
    setupMemoryAlerts(thresholds = {}) {
        const config = {
            warning: thresholds.warning || 70,  // 70%
            critical: thresholds.critical || 85, // 85%
            extreme: thresholds.extreme || 95    // 95%
        };

        setInterval(() => {
            const stats = this.monitorMemoryLimits();
            const usagePercent = parseFloat(stats.usage.heapUsagePercent);

            if (usagePercent >= config.extreme) {
                console.error(`🚨 EXTREMO: Uso de memoria ${usagePercent}%`);
                this.handleCriticalMemoryUsage();
            } else if (usagePercent >= config.critical) {
                console.error(`🚨 CRÍTICO: Uso de memoria ${usagePercent}%`);
            } else if (usagePercent >= config.warning) {
                console.warn(`⚠️  ADVERTENCIA: Uso de memoria ${usagePercent}%`);
            }
        }, 30000); // Verificar cada 30 segundos
    }

    // Optimizar configuración de garbage collection
    optimizeGarbageCollection() {
        const gcConfig = {
            // Configuraciones recomendadas para producción
            nodeFlags: [
                '--gc-interval=100',           // Intervalo de GC
                '--optimize-for-size',         // Optimizar para tamaño
                '--always-compact',            // Siempre compactar
                '--trace-gc',                  // Rastrear GC (solo para debugging)
                '--trace-gc-verbose'           // GC verbose (solo para debugging)
            ],
            
            // Configuración de generaciones
            generations: {
                young: {
                    maxSize: '64MB',
                    description: 'Objetos de corta duración'
                },
                old: {
                    maxSize: '4GB',
                    description: 'Objetos de larga duración'
                }
            }
        };

        console.log('🗑️  Configuración de Garbage Collection optimizada');
        return gcConfig;
    }

    // Generar script de inicio optimizado
    generateOptimizedStartScript(appFile = 'app.js', options = {}) {
        const limits = this.configureV8Limits(options);
        const gcConfig = this.optimizeGarbageCollection();
        
        const flags = [
            ...limits.nodeFlags,
            ...gcConfig.nodeFlags.filter(flag => !flag.includes('trace')) // Remover traces para producción
        ];

        const script = `#!/bin/bash
# Script de inicio optimizado para memoria
# Generado automáticamente

export NODE_ENV=production
export UV_THREADPOOL_SIZE=16

# Configuración de memoria optimizada
node ${flags.join(' ')} ${appFile}
`;

        console.log('📝 Script de inicio optimizado generado:');
        console.log(script);
        
        return {
            script,
            flags,
            recommendations: [
                'Usar --expose-gc en desarrollo para testing manual de GC',
                'Monitorear regularmente el uso de memoria en producción',
                'Ajustar límites según el hardware disponible',
                'Considerar clustering para aplicaciones de alta carga'
            ]
        };
    }
}
