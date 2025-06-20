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
