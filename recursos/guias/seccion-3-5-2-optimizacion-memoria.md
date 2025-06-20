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
Estrategias de Streaming y Buffers
Manejo Eficiente de Streams y Buffers:
javascript// stream-optimization.js
const { Transform, Readable, Writable } = require('stream');
const { pipeline } = require('stream/promises');

class StreamOptimizer {
    constructor() {
        this.defaultBufferSize = 64 * 1024; // 64KB
        this.maxBufferSize = 1024 * 1024;   // 1MB
    }

    // Stream de transformación con control de memoria
    createMemoryEfficientTransform(transformFn, options = {}) {
        const bufferSize = options.bufferSize || this.defaultBufferSize;
        let processedChunks = 0;
        let totalBytes = 0;

        return new Transform({
            objectMode: options.objectMode || false,
            highWaterMark: bufferSize,
            
            transform(chunk, encoding, callback) {
                try {
                    processedChunks++;
                    totalBytes += chunk.length || 0;
                    
                    // Monitorear uso de memoria cada 1000 chunks
                    if (processedChunks % 1000 === 0) {
                        const memUsage = process.memoryUsage();
                        console.log(`📊 Stream procesado: ${processedChunks} chunks, ${totalBytes} bytes, Heap: ${(memUsage.heapUsed / 1024 / 1024).toFixed(2)}MB`);
                        
                        // Forzar GC si es necesario
                        if (memUsage.heapUsed > 500 * 1024 * 1024 && global.gc) {
                            global.gc();
                        }
                    }
                    
                    const result = transformFn(chunk, encoding);
                    callback(null, result);
                } catch (error) {
                    callback(error);
                }
            },

            flush(callback) {
                console.log(`✅ Stream completado: ${processedChunks} chunks, ${totalBytes} bytes procesados`);
                callback();
            }
        });
    }

    // Procesamiento de archivos grandes con streaming
    async processLargeFile(inputPath, outputPath, processorFn, options = {}) {
        const fs = require('fs');
        const path = require('path');
        
        try {
            const stats = fs.statSync(inputPath);
            console.log(`📁 Procesando archivo: ${path.basename(inputPath)} (${(stats.size / 1024 / 1024).toFixed(2)}MB)`);
            
            const readStream = fs.createReadStream(inputPath, {
                highWaterMark: options.bufferSize || this.defaultBufferSize
            });
            
            const transformStream = this.createMemoryEfficientTransform(processorFn, options);
            
            const writeStream = fs.createWriteStream(outputPath, {
                highWaterMark: options.bufferSize || this.defaultBufferSize
            });

            // Usar pipeline para manejo automático de errores y cleanup
            await pipeline(readStream, transformStream, writeStream);
            
            console.log(`✅ Archivo procesado exitosamente: ${outputPath}`);
            return { success: true, inputSize: stats.size };
            
        } catch (error) {
            console.error(`❌ Error procesando archivo: ${error.message}`);
            throw error;
        }
    }

    // Buffer pool para reutilización
    createBufferPool(bufferSize = this.defaultBufferSize, poolSize = 10) {
        const pool = [];
        const inUse = new Set();
        
        // Inicializar pool
        for (let i = 0; i < poolSize; i++) {
            pool.push(Buffer.allocUnsafe(bufferSize));
        }
        
        return {
            acquire: () => {
                let buffer;
                if (pool.length > 0) {
                    buffer = pool.pop();
                } else {
                    buffer = Buffer.allocUnsafe(bufferSize);
                    console.log(`🔄 Creando nuevo buffer (pool agotado)`);
                }
                
                inUse.add(buffer);
                buffer.fill(0); // Limpiar buffer
                return buffer;
            },
            
            release: (buffer) => {
                if (inUse.has(buffer)) {
                    inUse.delete(buffer);
                    pool.push(buffer);
                    return true;
                }
                return false;
            },
            
            stats: () => ({
                available: pool.length,
                inUse: inUse.size,
                total: pool.length + inUse.size
            })
        };
    }

    // Stream de lectura con backpressure control
    createBackpressureControlledStream(dataSource, options = {}) {
        let index = 0;
        const batchSize = options.batchSize || 100;
        const maxMemoryUsage = options.maxMemoryUsage || 100 * 1024 * 1024; // 100MB
        
        return new Readable({
            objectMode: true,
            highWaterMark: options.highWaterMark || 16,
            
            read() {
                // Verificar uso de memoria antes de continuar
                const memUsage = process.memoryUsage();
                if (memUsage.heapUsed > maxMemoryUsage) {
                    console.log(`⏸️  Pausando stream por alto uso de memoria: ${(memUsage.heapUsed / 1024 / 1024).toFixed(2)}MB`);
                    
                    // Pausar brevemente para permitir GC
                    setTimeout(() => {
                        this._continueReading();
                    }, 100);
                    return;
                }
                
                this._continueReading();
            },
            
            _continueReading() {
                try {
                    const batch = dataSource.slice(index, index + batchSize);
                    
                    if (batch.length === 0) {
                        this.push(null); // Fin del stream
                        return;
                    }
                    
                    index += batch.length;
                    this.push(batch);
                    
                } catch (error) {
                    this.destroy(error);
                }
            }
        });
    }

    // Análisis de uso de memoria en streams
    createMemoryAnalysisStream() {
        let chunkCount = 0;
        let byteCount = 0;
        const memorySnapshots = [];
        
        return new Transform({
            objectMode: false,
            
            transform(chunk, encoding, callback) {
                chunkCount++;
                byteCount += chunk.length;
                
                // Tomar snapshot de memoria cada 100 chunks
                if (chunkCount % 100 === 0) {
                    const memUsage = process.memoryUsage();
                    memorySnapshots.push({
                        chunk: chunkCount,
                        bytes: byteCount,
                        heapUsed: memUsage.heapUsed,
                        heapTotal: memUsage.heapTotal,
                        timestamp: Date.now()
                    });
                    
                    // Mantener solo los últimos 10 snapshots
                    if (memorySnapshots.length > 10) {
                        memorySnapshots.shift();
                    }
                    
                    // Detectar crecimiento anómalo
                    if (memorySnapshots.length > 1) {
                        const current = memorySnapshots[memorySnapshots.length - 1];
                        const previous = memorySnapshots[memorySnapshots.length - 2];
                        const growth = current.heapUsed - previous.heapUsed;
                        
                        if (growth > 10 * 1024 * 1024) { // 10MB de crecimiento
                            console.warn(`⚠️  Crecimiento de memoria detectado: ${(growth / 1024 / 1024).toFixed(2)}MB`);
                        }
                    }
                }
                
                callback(null, chunk);
            },
            
            flush(callback) {
                console.log(`📊 Análisis de memoria del stream completado:`);
                console.log(`   - Chunks procesados: ${chunkCount}`);
                console.log(`   - Bytes procesados: ${byteCount}`);
                console.log(`   - Snapshots de memoria: ${memorySnapshots.length}`);
                
                if (memorySnapshots.length > 0) {
                    const lastSnapshot = memorySnapshots[memorySnapshots.length - 1];
                    console.log(`   - Memoria final: ${(lastSnapshot.heapUsed / 1024 / 1024).toFixed(2)}MB`);
                }
                
                callback();
            }
        });
    }
}

module.exports = StreamOptimizer;
Implementación Práctica
Configuración de Optimización de Memoria en Express:
javascript// app-memory-optimization.js
const express = require('express');
const MemoryAnalyzer = require('./memory-analyzer');
const DataOptimizer = require('./data-optimization');
const MemoryLeakDetector = require('./memory-leak-detector');
const MemoryLimitsManager = require('./memory-limits');
const StreamOptimizer = require('./stream-optimization');

class OptimizedExpressApp {
    constructor() {
        this.app = express();
        this.memoryAnalyzer = new MemoryAnalyzer();
        this.dataOptimizer = new DataOptimizer();
        this.leakDetector = new MemoryLeakDetector();
        this.limitsManager = new MemoryLimitsManager();
        this.streamOptimizer = new StreamOptimizer();
        
        this.setupMemoryOptimization();
    }

    setupMemoryOptimization() {
        // Configurar límites de memoria
        this.limitsManager.setupMemoryAlerts({
            warning: 70,
            critical: 85,
            extreme: 95
        });

        // Iniciar detección de memory leaks
        this.leakDetector.startMonitoring();

        // Iniciar monitoreo de memoria
        this.memoryAnalyzer.startMemoryMonitoring(30000); // cada 30 segundos

        // Configurar middleware de optimización
        this.setupOptimizationMiddleware();

        // Configurar endpoints de monitoreo
        this.setupMonitoringEndpoints();

        // Configurar manejo de eventos críticos
        this.setupCriticalEventHandlers();
    }

    setupOptimizationMiddleware() {
        // Middleware para comprimir respuestas
        const compression = require('compression');
        this.app.use(compression({
            threshold: 1024,
            level: 6,
            memLevel: 8
        }));

        // Middleware para límite de tamaño de request
        this.app.use(express.json({ 
            limit: '10mb',
            verify: (req, res, buf) => {
                // Monitorear tamaño de requests
                if (buf.length > 5 * 1024 * 1024) { // 5MB
                    console.warn(`⚠️  Request grande recibido: ${(buf.length / 1024 / 1024).toFixed(2)}MB`);
                }
            }
        }));

        // Middleware de monitoreo de memoria por request
        this.app.use((req, res, next) => {
            const startMemory = process.memoryUsage().heapUsed;
            const startTime = Date.now();

            res.on('finish', () => {
                const endMemory = process.memoryUsage().heapUsed;
                const endTime = Date.now();
                const memoryDelta = endMemory - startMemory;
                const duration = endTime - startTime;

                // Log requests que consumen mucha memoria
                if (memoryDelta > 10 * 1024 * 1024) { // 10MB
                    console.warn(`⚠️  Request con alto uso de memoria: ${req.method} ${req.path}`);
                    console.warn(`   - Memoria: ${(memoryDelta / 1024 / 1024).toFixed(2)}MB`);
                    console.warn(`   - Duración: ${duration}ms`);
                }
            });

            next();
        });
    }

    setupMonitoringEndpoints() {
        // Endpoint para estadísticas de memoria
        this.app.get('/health/memory', (req, res) => {
            const stats = this.memoryAnalyzer.getMemoryStats();
            const limits = this.limitsManager.monitorMemoryLimits();
            const leakReport = this.leakDetector.generateLeakReport();

            res.json({
                status: 'ok',
                timestamp: new Date().toISOString(),
                memory: stats,
                limits: limits,
                leaks: leakReport,
                recommendations: this.getOptimizationRecommendations()
            });
        });

        // Endpoint para crear heap snapshot
        this.app.post('/admin/heap-snapshot', (req, res) => {
            try {
                const filename = `manual-snapshot-${Date.now()}`;
                const snapshotPath = this.memoryAnalyzer.createHeapSnapshot(filename);
                
                res.json({
                    success: true,
                    snapshot: snapshotPath,
                    message: 'Heap snapshot creado exitosamente'
                });
            } catch (error) {
                res.status(500).json({
                    success: false,
                    error: error.message
                });
            }
        });

        // Endpoint para forzar garbage collection
        this.app.post('/admin/gc', (req, res) => {
            if (global.gc) {
                const before = process.memoryUsage();
                global.gc();
                const after = process.memoryUsage();
                
                res.json({
                    success: true,
                    before: before,
                    after: after,
                    freed: before.heapUsed - after.heapUsed
                });
            } else {
                res.status(400).json({
                    success: false,
                    message: 'Garbage collection no disponible. Ejecute con --expose-gc'
                });
            }
        });
    }

    setupCriticalEventHandlers() {
        // Manejar memoria crítica
        process.on('criticalMemoryUsage', (stats) => {
            console.error('🚨 MEMORIA CRÍTICA - Tomando acciones de emergencia');
            
            // Crear heap snapshot para análisis
            const filename = `critical-snapshot-${Date.now()}`;
            this.memoryAnalyzer.createHeapSnapshot(filename);
            
            // Limpiar caches si existen
            if (this.clearCaches) {
                this.clearCaches();
            }
        });

        // Manejar memoria extrema
        process.on('extremeMemoryUsage', () => {
            console.error('🚨 MEMORIA EXTREMA - Preparando para reinicio graceful');
            
            // Implementar reinicio graceful aquí
            // Por ejemplo, dejar de aceptar nuevas conexiones
            // y esperar a que terminen las existentes
        });

        // Manejar detección de memory leaks
        this.leakDetector.on('memoryLeak', (leak) => {
            console.error(`🚨 Memory leak detectado: ${leak.type}`);
            console.error(`   Detalles:`, leak);
            
            // Enviar alerta (email, Slack, etc.)
            this.sendMemoryLeakAlert(leak);
        });
    }

    getOptimizationRecommendations() {
        const memStats = this.memoryAnalyzer.getMemoryStats();
        const recommendations = [];

        const heapUsedMB = this.memoryAnalyzer.parseBytes(memStats.heapUsed);
        
        if (heapUsedMB > 1000) { // 1GB
            recommendations.push({
                priority: 'high',
                message: 'Considere implementar clustering para distribuir carga de memoria',
                action: 'cluster'
            });
        }

        if (heapUsedMB > 500) { // 500MB
            recommendations.push({
                priority: 'medium',
                message: 'Revisar implementación de caches y object pooling',
                action: 'cache_optimization'
            });
        }

        return recommendations;
    }

    sendMemoryLeakAlert(leak) {
        // Implementar envío de alertas
        // Ejemplo: enviar email, notificación Slack, etc.
        console.log('📧 Enviando alerta de memory leak...');
    }

    clearCaches() {
        // Implementar limpieza de caches de la aplicación
        console.log('🧹 Limpiando caches de aplicación...');
    }

    start(port = 3000) {
        this.app.listen(port, () => {
            console.log(`🚀 Aplicación optimizada iniciada en puerto ${port}`);
            console.log(`📊 Monitoreo de memoria activo`);
            console.log(`🔍 Detección de memory leaks activa`);
        });
    }
}

module.exports = OptimizedExpressApp;

// Ejemplo de uso
if (require.main === module) {
    const app = new OptimizedExpressApp();
    app.start();
}
Mejores Prácticas de Optimización de Memoria
Recomendaciones Generales:

Gestión de Referencias

Evitar referencias circulares
Utilizar WeakMap y WeakSet para referencias débiles
Limpiar event listeners cuando no se necesiten


Optimización de Estructuras de Datos

Utilizar object pooling para objetos reutilizables
Implementar caches con límites de tamaño y TTL
Usar streaming para procesar datos grandes


Monitoreo Continuo

Implementar alertas de memoria
Crear heap snapshots regulares
Monitorear tendencias de crecimiento


Configuración de Producción

Ajustar límites de memoria V8
Configurar garbage collection
Utilizar clustering para distribuir carga



Esta subsección proporciona herramientas completas para optimizar el uso de memoria en aplicaciones Node.js, desde el análisis detallado hasta la implementación de estrategias de prevención y recuperación.
