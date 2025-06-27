Configuración del Sistema de Benchmarking
Instalación de Herramientas de Benchmarking:
bash

# Instalar herramientas de benchmarking
npm install --save-dev artillery clinic autocannon
npm install --save-dev benchmark load-test
npm install --save-dev memwatch-next heapdump
# Para benchmarking de base de datos
npm install --save-dev pg-benchmark mysql-benchmark

Configuración de Infrastructure as Code para Benchmarks:
javascript

// config/benchmark.js
const config = {
  development: {
    benchmark: {
      enabled: true,
      logLevel: 'info',
      outputDir: './benchmark-reports',
      database: {
        connectionLimit: 10,
        acquireTimeout: 60000,
        timeout: 60000
      }
    }
  },
  
  staging: {
    benchmark: {
      enabled: true,
      logLevel: 'warn',
      outputDir: './benchmark-reports',
      database: {
        connectionLimit: 50,
        acquireTimeout: 30000,
        timeout: 30000
      }
    }
  },
  
  production: {
    benchmark: {
      enabled: false, // Solo en casos específicos
      logLevel: 'error',
      outputDir: './benchmark-reports',
      database: {
        connectionLimit: 100,
        acquireTimeout: 15000,
        timeout: 15000
      }
    }
  }
};

module.exports = config[process.env.NODE_ENV || 'development'];

Sistema de Benchmarking Integral
Clase Principal de Benchmarking:
javascript

// utils/benchmark/BenchmarkManager.js
const EventEmitter = require('events');
const fs = require('fs').promises;
const path = require('path');
const { performance } = require('perf_hooks');
const clinic = require('clinic');
const autocannon = require('autocannon');

class BenchmarkManager extends EventEmitter {
  constructor(config = {}) {
    super();
    this.config = {
      outputDir: './benchmark-reports',
      iterations: 1000,
      concurrency: 10,
      warmupIterations: 100,
      timeout: 30000,
      ...config
    };
    
    this.results = new Map();
    this.isRunning = false;
  }

  // Benchmark de rendimiento de funciones
  async benchmarkFunction(name, fn, options = {}) {
    const opts = { ...this.config, ...options };
    const results = {
      name,
      iterations: opts.iterations,
      startTime: Date.now(),
      samples: [],
      memory: [],
      cpu: []
    };

    console.log(`🚀 Iniciando benchmark: ${name}`);
    
    // Calentamiento
    for (let i = 0; i < opts.warmupIterations; i++) {
      await fn();
    }

    // Medición principal
    for (let i = 0; i < opts.iterations; i++) {
      const memBefore = process.memoryUsage();
      const cpuBefore = process.cpuUsage();
      const startTime = performance.now();
      
      try {
        await fn();
        
        const endTime = performance.now();
        const memAfter = process.memoryUsage();
        const cpuAfter = process.cpuUsage(cpuBefore);
        
        results.samples.push(endTime - startTime);
        results.memory.push({
          heapUsed: memAfter.heapUsed - memBefore.heapUsed,
          heapTotal: memAfter.heapTotal - memBefore.heapTotal,
          external: memAfter.external - memBefore.external
        });
        results.cpu.push({
          user: cpuAfter.user,
          system: cpuAfter.system
        });
        
      } catch (error) {
        console.error(`Error en iteración ${i}:`, error);
      }
      
      // Mostrar progreso cada 100 iteraciones
      if ((i + 1) % 100 === 0) {
        console.log(`Progreso: ${i + 1}/${opts.iterations}`);
      }
    }

    results.endTime = Date.now();
    results.statistics = this.calculateStatistics(results.samples);
    results.memoryStats = this.calculateMemoryStats(results.memory);
    results.cpuStats = this.calculateCpuStats(results.cpu);

    this.results.set(name, results);
    await this.saveResults(name, results);
    
    console.log(`✅ Benchmark completado: ${name}`);
    this.emit('benchmarkComplete', { name, results });
    
    return results;
  }

  // Benchmark de carga HTTP
  async benchmarkHTTP(name, options = {}) {
    const opts = {
      url: 'http://localhost:3000',
      connections: 10,
      duration: 10,
      ...options
    };

    console.log(`🌐 Iniciando benchmark HTTP: ${name}`);
    
    return new Promise((resolve, reject) => {
      const instance = autocannon(opts, (err, result) => {
        if (err) {
          reject(err);
          return;
        }

        const processedResult = {
          name,
          url: opts.url,
          connections: opts.connections,
          duration: opts.duration,
          requests: {
            total: result.requests.total,
            average: result.requests.average,
            mean: result.requests.mean,
            stddev: result.requests.stddev,
            min: result.requests.min,
            max: result.requests.max
          },
          latency: {
            average: result.latency.average,
            mean: result.latency.mean,
            stddev: result.latency.stddev,
            min: result.latency.min,
            max: result.latency.max
          },
          throughput: {
            average: result.throughput.average,
            mean: result.throughput.mean,
            stddev: result.throughput.stddev,
            min: result.throughput.min,
            max: result.throughput.max
          },
          errors: result.errors,
          timeouts: result.timeouts
        };

        this.results.set(name, processedResult);
        this.saveResults(name, processedResult);
        
        console.log(`✅ Benchmark HTTP completado: ${name}`);
        this.emit('httpBenchmarkComplete', { name, results: processedResult });
        
        resolve(processedResult);
      });

      // Manejar eventos de progreso
      instance.on('response', () => {
        // Opcional: mostrar progreso en tiempo real
      });
    });
  }

  // Benchmark de base de datos
  async benchmarkDatabase(name, queries, connectionPool) {
    const results = {
      name,
      queries: queries.length,
      startTime: Date.now(),
      queryResults: []
    };

    console.log(`🗄️ Iniciando benchmark de base de datos: ${name}`);

    for (const [index, query] of queries.entries()) {
      const queryResult = {
        index,
        query: query.sql || query,
        iterations: query.iterations || 100,
        samples: []
      };

      for (let i = 0; i < queryResult.iterations; i++) {
        const startTime = performance.now();
        
        try {
          await connectionPool.query(query.sql || query, query.params || []);
          const endTime = performance.now();
          queryResult.samples.push(endTime - startTime);
        } catch (error) {
          console.error(`Error en query ${index}, iteración ${i}:`, error);
          queryResult.samples.push(null);
        }
      }

      queryResult.statistics = this.calculateStatistics(
        queryResult.samples.filter(s => s !== null)
      );
      
      results.queryResults.push(queryResult);
      console.log(`Query ${index + 1}/${queries.length} completada`);
    }

    results.endTime = Date.now();
    this.results.set(name, results);
    await this.saveResults(name, results);
    
    console.log(`✅ Benchmark de base de datos completado: ${name}`);
    this.emit('databaseBenchmarkComplete', { name, results });
    
    return results;
  }

  // Benchmark de memoria y recursos
  async benchmarkResources(name, fn, options = {}) {
    const opts = { duration: 10000, interval: 100, ...options };
    const results = {
      name,
      duration: opts.duration,
      samples: [],
      startTime: Date.now()
    };

    console.log(`📊 Iniciando benchmark de recursos: ${name}`);
    
    const interval = setInterval(() => {
      const memUsage = process.memoryUsage();
      const cpuUsage = process.cpuUsage();
      
      results.samples.push({
        timestamp: Date.now(),
        memory: memUsage,
        cpu: cpuUsage
      });
    }, opts.interval);

    // Ejecutar función bajo monitoreo
    const startTime = performance.now();
    await fn();
    const endTime = performance.now();
    
    clearInterval(interval);
    
    results.endTime = Date.now();
    results.executionTime = endTime - startTime;
    results.resourceStats = this.calculateResourceStats(results.samples);
    
    this.results.set(name, results);
    await this.saveResults(name, results);
    
    console.log(`✅ Benchmark de recursos completado: ${name}`);
    this.emit('resourceBenchmarkComplete', { name, results });
    
    return results;
  }

  // Cálculo de estadísticas
  calculateStatistics(samples) {
    if (!samples || samples.length === 0) return null;
    
    const sorted = [...samples].sort((a, b) => a - b);
    const sum = samples.reduce((a, b) => a + b, 0);
    const mean = sum / samples.length;
    
    const variance = samples.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / samples.length;
    const stddev = Math.sqrt(variance);
    
    return {
      count: samples.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      mean: mean,
      median: sorted[Math.floor(sorted.length / 2)],
      p95: sorted[Math.floor(sorted.length * 0.95)],
      p99: sorted[Math.floor(sorted.length * 0.99)],
      stddev: stddev,
      variance: variance
    };
  }

  calculateMemoryStats(memoryData) {
    if (!memoryData || memoryData.length === 0) return null;
    
    const heapUsed = memoryData.map(m => m.heapUsed);
    const heapTotal = memoryData.map(m => m.heapTotal);
    const external = memoryData.map(m => m.external);
    
    return {
      heapUsed: this.calculateStatistics(heapUsed),
      heapTotal: this.calculateStatistics(heapTotal),
      external: this.calculateStatistics(external)
    };
  }

  calculateCpuStats(cpuData) {
    if (!cpuData || cpuData.length === 0) return null;
    
    const user = cpuData.map(c => c.user);
    const system = cpuData.map(c => c.system);
    
    return {
      user: this.calculateStatistics(user),
      system: this.calculateStatistics(system)
    };
  }

  calculateResourceStats(samples) {
    if (!samples || samples.length === 0) return null;
    
    const memoryData = samples.map(s => s.memory.heapUsed);
    const timestamps = samples.map(s => s.timestamp);
    
    return {
      memory: this.calculateStatistics(memoryData),
      sampleCount: samples.length,
      duration: timestamps[timestamps.length - 1] - timestamps[0]
    };
  }

  // Guardar resultados
  async saveResults(name, results) {
    try {
      await fs.mkdir(this.config.outputDir, { recursive: true });
      
      const filename = `${name.replace(/\s+/g, '-').toLowerCase()}-${Date.now()}.json`;
      const filepath = path.join(this.config.outputDir, filename);
      
      await fs.writeFile(filepath, JSON.stringify(results, null, 2));
      
      // Generar reporte HTML
      await this.generateHTMLReport(name, results);
      
    } catch (error) {
      console.error('Error guardando resultados:', error);
    }
  }

  // Generar reporte HTML
  async generateHTMLReport(name, results) {
    const html = `
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Benchmark: ${name}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .stat-item { background: #f9f9f9; padding: 10px; border-radius: 3px; }
        .stat-value { font-size: 1.2em; font-weight: bold; color: #2c3e50; }
        .chart { width: 100%; height: 300px; border: 1px solid #ccc; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Reporte de Benchmark: ${name}</h1>
        <p>Generado: ${new Date().toLocaleString()}</p>
    </div>
    
    <div class="section">
        <h2>Resumen Ejecutivo</h2>
        <div class="stats">
            ${this.generateStatsHTML(results)}
        </div>
    </div>
    
    <div class="section">
        <h2>Datos Detallados</h2>
        <pre>${JSON.stringify(results, null, 2)}</pre>
    </div>
</body>
</html>`;

    const filename = `${name.replace(/\s+/g, '-').toLowerCase()}-${Date.now()}.html`;
    const filepath = path.join(this.config.outputDir, filename);
    
    await fs.writeFile(filepath, html);
  }

  generateStatsHTML(results) {
    let html = '';
    
    if (results.statistics) {
      html += `
        <div class="stat-item">
          <div>Tiempo Promedio</div>
          <div class="stat-value">${results.statistics.mean.toFixed(2)} ms</div>
        </div>
        <div class="stat-item">
          <div>Tiempo Mínimo</div>
          <div class="stat-value">${results.statistics.min.toFixed(2)} ms</div>
        </div>
        <div class="stat-item">
          <div>Tiempo Máximo</div>
          <div class="stat-value">${results.statistics.max.toFixed(2)} ms</div>
        </div>
        <div class="stat-item">
          <div>Percentil 95</div>
          <div class="stat-value">${results.statistics.p95.toFixed(2)} ms</div>
        </div>
      `;
    }
    
    if (results.requests) {
      html += `
        <div class="stat-item">
          <div>Requests Totales</div>
          <div class="stat-value">${results.requests.total}</div>
        </div>
        <div class="stat-item">
          <div>Requests/seg</div>
          <div class="stat-value">${results.requests.average.toFixed(2)}</div>
        </div>
      `;
    }
    
    return html;
  }

  // Comparar resultados
  compareResults(name1, name2) {
    const result1 = this.results.get(name1);
    const result2 = this.results.get(name2);
    
    if (!result1 || !result2) {
      throw new Error('Uno o ambos resultados no existen');
    }
    
    const comparison = {
      name1,
      name2,
      comparison: {},
      improvement: {}
    };
    
    if (result1.statistics && result2.statistics) {
      comparison.comparison.mean = {
        result1: result1.statistics.mean,
        result2: result2.statistics.mean,
        difference: result2.statistics.mean - result1.statistics.mean,
        percentChange: ((result2.statistics.mean - result1.statistics.mean) / result1.statistics.mean) * 100
      };
      
      comparison.improvement.faster = result1.statistics.mean < result2.statistics.mean ? name1 : name2;
      comparison.improvement.speedup = Math.abs(comparison.comparison.mean.percentChange);
    }
    
    return comparison;
  }

  // Generar suite de benchmarks
  async runBenchmarkSuite(suite) {
    console.log(`🧪 Ejecutando suite de benchmarks: ${suite.name}`);
    const suiteResults = {
      name: suite.name,
      startTime: Date.now(),
      benchmarks: []
    };
    
    for (const benchmark of suite.benchmarks) {
      try {
        let result;
        
        switch (benchmark.type) {
          case 'function':
            result = await this.benchmarkFunction(benchmark.name, benchmark.fn, benchmark.options);
            break;
          case 'http':
            result = await this.benchmarkHTTP(benchmark.name, benchmark.options);
            break;
          case 'database':
            result = await this.benchmarkDatabase(benchmark.name, benchmark.queries, benchmark.pool);
            break;
          case 'resources':
            result = await this.benchmarkResources(benchmark.name, benchmark.fn, benchmark.options);
            break;
          default:
            throw new Error(`Tipo de benchmark no soportado: ${benchmark.type}`);
        }
        
        suiteResults.benchmarks.push(result);
        
      } catch (error) {
        console.error(`Error ejecutando benchmark ${benchmark.name}:`, error);
        suiteResults.benchmarks.push({
          name: benchmark.name,
          error: error.message
        });
      }
    }
    
    suiteResults.endTime = Date.now();
    suiteResults.duration = suiteResults.endTime - suiteResults.startTime;
    
    await this.saveResults(`suite-${suite.name}`, suiteResults);
    
    console.log(`✅ Suite de benchmarks completada: ${suite.name}`);
    this.emit('suiteComplete', { suite: suite.name, results: suiteResults });
    
    return suiteResults;
  }

  // Limpiar resultados antiguos
  async cleanOldResults(maxAge = 7 * 24 * 60 * 60 * 1000) { // 7 días por defecto
    try {
      const files = await fs.readdir(this.config.outputDir);
      const now = Date.now();
      
      for (const file of files) {
        const filepath = path.join(this.config.outputDir, file);
        const stats = await fs.stat(filepath);
        
        if (now - stats.mtime.getTime() > maxAge) {
          await fs.unlink(filepath);
          console.log(`🗑️ Archivo de benchmark eliminado: ${file}`);
        }
      }
    } catch (error) {
      console.error('Error limpiando archivos antiguos:', error);
    }
  }
}

module.exports = BenchmarkManager;

Configuración de Benchmarks Específicos
Benchmarks para Rutas de API:
javascript

// tests/benchmarks/api-benchmarks.js
const BenchmarkManager = require('../../utils/benchmark/BenchmarkManager');
const app = require('../../app');
const request = require('supertest');

class APIBenchmarks {
  constructor() {
    this.benchmarkManager = new BenchmarkManager({
      outputDir: './benchmark-reports/api',
      iterations: 500,
      concurrency: 20
    });
  }

  async runAllBenchmarks() {
    const suite = {
      name: 'API-Performance-Suite',
      benchmarks: [
        {
          type: 'function',
          name: 'GET-Users-List',
          fn: () => request(app).get('/api/users'),
          options: { iterations: 1000 }
        },
        {
          type: 'function',
          name: 'POST-User-Creation',
          fn: () => request(app)
            .post('/api/users')
            .send({
              name: 'Test User',
              email: `test${Date.now()}@example.com`
            })
        },
        {
          type: 'function',
          name: 'GET-User-Profile',
          fn: () => request(app).get('/api/users/1')
        },
        {
          type: 'http',
          name: 'Load-Test-Homepage',
          options: {
            url: 'http://localhost:3000',
            connections: 50,
            duration: 30
          }
        }
      ]
    };

    return await this.benchmarkManager.runBenchmarkSuite(suite);
  }

  async benchmarkAuthenticationFlow() {
    return await this.benchmarkManager.benchmarkFunction(
      'Authentication-Flow',
      async () => {
        // Login
        const loginResponse = await request(app)
          .post('/api/auth/login')
          .send({
            email: 'test@example.com',
            password: 'password123'
          });

        const token = loginResponse.body.token;

        // Authenticated request
        await request(app)
          .get('/api/profile')
          .set('Authorization', `Bearer ${token}`);
      },
      { iterations: 200 }
    );
  }
}

module.exports = APIBenchmarks;

Benchmarks para Base de Datos:
javascript

// tests/benchmarks/database-benchmarks.js
const BenchmarkManager = require('../../utils/benchmark/BenchmarkManager');
const db = require('../../config/database');

class DatabaseBenchmarks {
  constructor() {
    this.benchmarkManager = new BenchmarkManager({
      outputDir: './benchmark-reports/database',
      iterations: 100
    });
  }

  async runQueryBenchmarks() {
    const queries = [
      {
        sql: 'SELECT * FROM users WHERE active = ?',
        params: [true],
        iterations: 500
      },
      {
        sql: 'SELECT u.*, p.name as profile_name FROM users u LEFT JOIN profiles p ON u.id = p.user_id WHERE u.created_at > ?',
        params: [new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)],
        iterations: 200
      },
      {
        sql: 'INSERT INTO audit_log (user_id, action, details) VALUES (?, ?, ?)',
        params: [1, 'test_action', JSON.stringify({ benchmark: true })],
        iterations: 1000
      },
      {
        sql: 'UPDATE users SET last_login = ? WHERE id = ?',
        params: [new Date(), 1],
        iterations: 300
      }
    ];

    return await this.benchmarkManager.benchmarkDatabase(
      'Database-Query-Performance',
      queries,
      db
    );
  }

  async benchmarkConnectionPool() {
    return await this.benchmarkManager.benchmarkFunction(
      'Database-Connection-Pool',
      async () => {
        const connection = await db.getConnection();
        await connection.query('SELECT 1');
        connection.release();
      },
      { iterations: 1000 }
    );
  }

  async benchmarkTransactions() {
    return await this.benchmarkManager.benchmarkFunction(
      'Database-Transactions',
      async () => {
        const connection = await db.getConnection();
        await connection.beginTransaction();
        
        try {
          await connection.query('INSERT INTO test_table (data) VALUES (?)', ['test']);
          await connection.query('UPDATE test_table SET data = ? WHERE id = LAST_INSERT_ID()', ['updated']);
          await connection.commit();
        } catch (error) {
          await connection.rollback();
          throw error;
        } finally {
          connection.release();
        }
      },
      { iterations: 100 }
    );
  }
}

module.exports = DatabaseBenchmarks;

Scripts de Automatización
Script Principal de Benchmarking:
javascript

// scripts/run-benchmarks.js
const APIBenchmarks = require('../tests/benchmarks/api-benchmarks');
const DatabaseBenchmarks = require('../tests/benchmarks/database-benchmarks');
const BenchmarkManager = require('../utils/benchmark/BenchmarkManager');

async function runAllBenchmarks() {
  console.log('🚀 Iniciando suite completa de benchmarks...');
  
  const startTime = Date.now();
  const results = {
    api: {},
    database: {},
    system: {}
  };

  try {
    // Benchmarks de API
    console.log('\n📡 Ejecutando benchmarks de API...');
    const apiBenchmarks = new APIBenchmarks();
    results.api.suite = await apiBenchmarks.runAllBenchmarks();
    results.api.auth = await apiBenchmarks.benchmarkAuthenticationFlow();

    // Benchmarks de Base de Datos
    console.log('\n🗄️ Ejecutando benchmarks de base de datos...');
    const dbBenchmarks = new DatabaseBenchmarks();
    results.database.queries = await dbBenchmarks.runQueryBenchmarks();
    results.database.connections = await dbBenchmarks.benchmarkConnectionPool();
    results.database.transactions = await dbBenchmarks.benchmarkTransactions();

    // Benchmarks del Sistema
    console.log('\n⚙️ Ejecutando benchmarks del sistema...');
    const systemBenchmarks = new BenchmarkManager({
      outputDir: './benchmark-reports/system'
    });

    results.system.memory = await systemBenchmarks.benchmarkResources(
      'Memory-Usage-Test',
      async () => {
        // Simular carga de memoria
        const data = [];
        for (let i = 0; i < 100000; i++) {
          data.push({ id: i, data: `test-data-${i}` });
        }
        return data;
      },
      { duration: 5000 }
    );

    const endTime = Date.now();
    const totalDuration = endTime - startTime;

    console.log(`\n✅ Todos los benchmarks completados en ${totalDuration}ms`);
    
    // Generar reporte consolidado
    await generateConsolidatedReport(results, totalDuration);
    
    return results;

  } catch (error) {
    console.error('❌ Error ejecutando benchmarks:', error);
    throw error;
  }
}

async function generateConsolidatedReport(results, duration) {
  const fs = require('fs').promises;
  const path = require('path');

  const report = {
    timestamp: new Date().toISOString(),
    totalDuration: duration,
    summary: {
      apiTests: Object.keys(results.api).length,
      databaseTests: Object.keys(results.database).length,
      systemTests: Object.keys(results.system).length
    },
    results: results,
    recommendations: generateRecommendations(results)
  };

  const reportPath = path.join('./benchmark-reports', `consolidated-report-${Date.now()}.json`);
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
  
  console.log(`📊 Reporte consolidado guardado en: ${reportPath}`);
}

function generateRecommendations(results) {
  const recommendations = [];

  // Analizar resultados de API
  if (results.api.suite && results.api.suite.benchmarks) {
    for (const benchmark of results.api.suite.benchmarks) {
      if (benchmark.statistics && benchmark.statistics.mean > 1000) {
        recommendations.push({
          type: 'performance',
          category: 'API',
          message: `El endpoint ${benchmark.name} tiene un tiempo de respuesta alto (${benchmark.statistics.mean.toFixed(2)}ms). Considerar optimización.`
        });
      }
    }
  }

  // Analizar resultados de base de datos
  if (results.database.queries && results.database.queries.queryResults) {
    for (const query of results.database.queries.queryResults) {
      if (query.statistics && query.statistics.mean > 500) {
        recommendations.push({
          type: 'performance',
          category: 'Database',
          message: `La query en posición ${query.index} es lenta (${query.statistics.mean.toFixed(2)}ms). Verificar índices y optimización.`
        });
      }
    }
  }

  return recommendations;
}

// Ejecutar si se llama directamente
if (require.main === module) {
  runAllBenchmarks()
    .then(() => process.exit(0))
    .catch(error => {
      console.error(error);
      process.exit(1);
    });
}

module.exports = { runAllBenchmarks };

Configuración de Package.json:
json

{
  "scripts": {
    "benchmark": "node scripts/run-benchmarks.js",
    "benchmark:api": "node tests/benchmarks/api-benchmarks.js",
    "benchmark:db": "node tests/benchmarks/database-benchmarks.js",
    "benchmark:clean": "node -e \"require('./utils/benchmark/BenchmarkManager')().cleanOldResults()\"",
    "benchmark:report": "node scripts/generate-benchmark-report.js",
    "benchmark:compare": "node scripts/compare-benchmarks.js"
  }
}

Integración con CI/CD
GitHub Actions para Benchmarking:
yaml

# .github/workflows/benchmark.yml
name: Performance Benchmarks

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * 1' # Ejecutar semanalmente los lunes a las 2 AM

jobs:
  benchmark:
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: password
          MYSQL_DATABASE: testdb
        ports:
          - 3306:3306
        options: --health-cmd="mysqladmin ping" --health-interval=10s --health-timeout=5s --health-retries=3

    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Wait for MySQL
      run: |
        while ! mysqladmin ping -h"127.0.0.1" -P"3306" -uroot -ppassword --silent; do
          sleep 1
        done
    
    - name: Setup database
      run: |
        mysql -h127.0.0.1 -P3306 -uroot -ppassword testdb < database/schema.sql
        mysql -h127.0.0.1 -P3306 -uroot -ppassword testdb < database/test-data.sql
    
    - name: Start application
      run: |
        npm start > app.log 2>&1 &
        sleep 10
      env:
        NODE_ENV: test
        DB_HOST: 127.0.0.1
        DB_PORT: 3306
        DB_NAME: testdb
        DB_USER: root
        DB_PASSWORD: password
    
    - name: Run benchmarks
      run: npm run benchmark
    
    - name: Upload benchmark results
      uses: actions/upload-artifact@v3
      with:
        name: benchmark-reports
        path: benchmark-reports/
    
    - name: Compare with baseline
      run: node scripts/compare-with-baseline.js
      
    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v6
      with:
        script: |
          const fs = require('fs');
          const path = './benchmark-reports/pr-summary.md';
          if (fs.existsSync(path)) {
            const summary = fs.readFileSync(path, 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: summary
            });
          }

Herramientas de Análisis y Comparación
Comparador de Benchmarks:
javascript

// scripts/compare-benchmarks.js
const fs = require('fs').promises;
const path = require('path');

class BenchmarkComparator {
  constructor(reportsDir = './benchmark-reports') {
    this.reportsDir = reportsDir;
  }

  async compareReports(baselineFile, currentFile) {
    const baseline = await this.loadReport(baselineFile);
    const current = await this.loadReport(currentFile);

    const comparison = {
      baseline: baselineFile,
      current: currentFile,
      timestamp: new Date().toISOString(),
      results: {}
    };

    // Comparar resultados por categoría
    for (const category of ['api', 'database', 'system']) {
      if (baseline[category] && current[category]) {
        comparison.results[category] = this.compareCategory(
          baseline[category],
          current[category],
          category
        );
      }
    }

    comparison.summary = this.generateComparisonSummary(comparison.results);
    
    await this.saveComparison(comparison);
    await this.generateComparisonReport(comparison);
    
    return comparison;
  }

  compareCategory(baselineData, currentData, category) {
    const results = {
      improvements: [],
      regressions: [],
      stable: []
    };

    switch (category) {
      case 'api':
        results = this.compareAPIResults(baselineData, currentData);
        break;
      case 'database':
        results = this.compareDatabaseResults(baselineData, currentData);
        break;
      case 'system':
        results = this.compareSystemResults(baselineData, currentData);
        break;
    }

    return results;
  }

  compareAPIResults(baseline, current) {
    const results = { improvements: [], regressions: [], stable: [] };

    if (baseline.suite && current.suite) {
      for (const currentBench of current.suite.benchmarks) {
        const baselineBench = baseline.suite.benchmarks.find(
          b => b.name === currentBench.name
        );

        if (baselineBench && baselineBench.statistics && currentBench.statistics) {
          const improvement = this.calculateImprovement(
            baselineBench.statistics.mean,
            currentBench.statistics.mean
          );

          const comparison = {
            name: currentBench.name,
            baseline: baselineBench.statistics.mean,
            current: currentBench.statistics.mean,
            improvement: improvement,
            category: 'api'
          };

          if (Math.abs(improvement) < 5) {
            results.stable.push(comparison);
          } else if (improvement > 0) {
            results.improvements.push(comparison);
          } else {
            results.regressions.push(comparison);
          }
        }
      }
    }

    return results;
  }

  compareDatabaseResults(baseline, current) {
    const results = { improvements: [], regressions: [], stable: [] };

    if (baseline.queries && current.queries) {
      for (let i = 0; i < Math.min(baseline.queries.queryResults.length, current.queries.queryResults.length); i++) {
        const baselineQuery = baseline.queries.queryResults[i];
        const currentQuery = current.queries.queryResults[i];

        if (baselineQuery.statistics && currentQuery.statistics) {
          const improvement = this.calculateImprovement(
            baselineQuery.statistics.mean,
            currentQuery.statistics.mean
          );

          const comparison = {
            name: `Query ${i + 1}`,
            baseline: baselineQuery.statistics.mean,
            current: currentQuery.statistics.mean,
            improvement: improvement,
            category: 'database'
          };

          if (Math.abs(improvement) < 5) {
            results.stable.push(comparison);
          } else if (improvement > 0) {
            results.improvements.push(comparison);
          } else {
            results.regressions.push(comparison);
          }
        }
      }
    }

    return results;
  }

  compareSystemResults(baseline, current) {
    const results = { improvements: [], regressions: [], stable: [] };

    // Comparar uso de memoria
    if (baseline.memory && current.memory) {
      const memoryImprovement = this.calculateImprovement(
        baseline.memory.resourceStats.memory.mean,
        current.memory.resourceStats.memory.mean
      );

      const comparison = {
        name: 'Memory Usage',
        baseline: baseline.memory.resourceStats.memory.mean,
        current: current.memory.resourceStats.memory.mean,
        improvement: memoryImprovement,
        category: 'system'
      };

      if (Math.abs(memoryImprovement) < 5) {
        results.stable.push(comparison);
      } else if (memoryImprovement > 0) {
        results.improvements.push(comparison);
      } else {
        results.regressions.push(comparison);
      }
    }

    return results;
  }

  calculateImprovement(baseline, current) {
    return ((baseline - current) / baseline) * 100;
  }

  generateComparisonSummary(results) {
    let totalImprovements = 0;
    let totalRegressions = 0;
    let totalStable = 0;

    for (const category of Object.values(results)) {
      totalImprovements += category.improvements.length;
      totalRegressions += category.regressions.length;
      totalStable += category.stable.length;
    }

    return {
      totalTests: totalImprovements + totalRegressions + totalStable,
      improvements: totalImprovements,
      regressions: totalRegressions,
      stable: totalStable,
      overallTrend: totalImprovements > totalRegressions ? 'improving' : 
                   totalRegressions > totalImprovements ? 'regressing' : 'stable'
    };
  }

  async generateComparisonReport(comparison) {
    const markdown = this.generateMarkdownReport(comparison);
    const html = this.generateHTMLReport(comparison);

    const timestamp = Date.now();
    await fs.writeFile(
      path.join(this.reportsDir, `comparison-${timestamp}.md`),
      markdown
    );
    await fs.writeFile(
      path.join(this.reportsDir, `comparison-${timestamp}.html`),
      html
    );

    // Generar resumen para PR si es necesario
    if (process.env.GITHUB_EVENT_NAME === 'pull_request') {
      const prSummary = this.generatePRSummary(comparison);
      await fs.writeFile(
        path.join(this.reportsDir, 'pr-summary.md'),
        prSummary
      );
    }
  }

  generateMarkdownReport(comparison) {
    let markdown = `# Comparación de Benchmarks\n\n`;
    markdown += `**Fecha:** ${new Date(comparison.timestamp).toLocaleString()}\n`;
    markdown += `**Baseline:** ${comparison.baseline}\n`;
    markdown += `**Current:** ${comparison.current}\n\n`;

    markdown += `## Resumen\n\n`;
    markdown += `- **Total de pruebas:** ${comparison.summary.totalTests}\n`;
    markdown += `- **Mejoras:** ${comparison.summary.improvements}\n`;
    markdown += `- **Regresiones:** ${comparison.summary.regressions}\n`;
    markdown += `- **Estables:** ${comparison.summary.stable}\n`;
    markdown += `- **Tendencia general:** ${comparison.summary.overallTrend}\n\n`;

    for (const [category, results] of Object.entries(comparison.results)) {
      markdown += `## ${category.toUpperCase()}\n\n`;

      if (results.improvements.length > 0) {
        markdown += `### ✅ Mejoras\n\n`;
        for (const item of results.improvements) {
          markdown += `- **${item.name}:** ${item.improvement.toFixed(2)}% más rápido (${item.baseline.toFixed(2)}ms → ${item.current.toFixed(2)}ms)\n`;
        }
        markdown += `\n`;
      }

      if (results.regressions.length > 0) {
        markdown += `### ❌ Regresiones\n\n`;
        for (const item of results.regressions) {
          markdown += `- **${item.name}:** ${Math.abs(item.improvement).toFixed(2)}% más lento (${item.baseline.toFixed(2)}ms → ${item.current.toFixed(2)}ms)\n`;
        }
        markdown += `\n`;
      }

      if (results.stable.length > 0) {
        markdown += `### ➖ Estables\n\n`;
        for (const item of results.stable) {
          markdown += `- **${item.name}:** Sin cambios significativos (${item.baseline.toFixed(2)}ms → ${item.current.toFixed(2)}ms)\n`;
        }
        markdown += `\n`;
      }
    }

    return markdown;
  }

  generateHTMLReport(comparison) {
    return `
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comparación de Benchmarks</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .summary-item { background: #f9f9f9; padding: 15px; border-radius: 5px; text-align: center; }
        .improvement { color: #27ae60; }
        .regression { color: #e74c3c; }
        .stable { color: #7f8c8d; }
        .category { margin: 30px 0; }
        .category h2 { border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .result-list { list-style: none; padding: 0; }
        .result-item { padding: 10px; margin: 5px 0; border-radius: 5px; }
        .result-item.improvement { background: #d5f4e6; }
        .result-item.regression { background: #fdf2f2; }
        .result-item.stable { background: #f8f9fa; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Comparación de Benchmarks</h1>
        <p><strong>Fecha:</strong> ${new Date(comparison.timestamp).toLocaleString()}</p>
        <p><strong>Baseline:</strong> ${comparison.baseline}</p>
        <p><strong>Current:</strong> ${comparison.current}</p>
    </div>

    <div class="summary">
        <div class="summary-item">
            <h3>Total de Pruebas</h3>
            <div class="value">${comparison.summary.totalTests}</div>
        </div>
        <div class="summary-item improvement">
            <h3>Mejoras</h3>
            <div class="value">${comparison.summary.improvements}</div>
        </div>
        <div class="summary-item regression">
            <h3>Regresiones</h3>
            <div class="value">${comparison.summary.regressions}</div>
        </div>
        <div class="summary-item stable">
            <h3>Estables</h3>
            <div class="value">${comparison.summary.stable}</div>
        </div>
    </div>

    ${Object.entries(comparison.results).map(([category, results]) => `
        <div class="category">
            <h2>${category.toUpperCase()}</h2>
            ${this.generateCategoryHTML(results)}
        </div>
    `).join('')}
</body>
</html>`;
  }

  generateCategoryHTML(results) {
    let html = '';

    if (results.improvements.length > 0) {
      html += '<h3>✅ Mejoras</h3><ul class="result-list">';
      for (const item of results.improvements) {
        html += `<li class="result-item improvement">
          <strong>${item.name}:</strong> ${item.improvement.toFixed(2)}% más rápido 
          (${item.baseline.toFixed(2)}ms → ${item.current.toFixed(2)}ms)
        </li>`;
      }
      html += '</ul>';
    }

    if (results.regressions.length > 0) {
      html += '<h3>❌ Regresiones</h3><ul class="result-list">';
      for (const item of results.regressions) {
        html += `<li class="result-item regression">
          <strong>${item.name}:</strong> ${Math.abs(item.improvement).toFixed(2)}% más lento 
          (${item.baseline.toFixed(2)}ms → ${item.current.toFixed(2)}ms)
        </li>`;
      }
      html += '</ul>';
    }

    if (results.stable.length > 0) {
      html += '<h3>➖ Estables</h3><ul class="result-list">';
      for (const item of results.stable) {
        html += `<li class="result-item stable">
          <strong>${item.name}:</strong> Sin cambios significativos 
          (${item.baseline.toFixed(2)}ms → ${item.current.toFixed(2)}ms)
        </li>`;
      }
      html += '</ul>';
    }

    return html;
  }

  generatePRSummary(comparison) {
    let summary = `## 📊 Resultados de Benchmarks\n\n`;
    
    const { improvements, regressions, stable } = comparison.summary;
    
    if (regressions > 0) {
      summary += `⚠️ **Se detectaron ${regressions} regresión(es) de rendimiento**\n\n`;
    } else if (improvements > 0) {
      summary += `✅ **Se detectaron ${improvements} mejora(s) de rendimiento**\n\n`;
    } else {
      summary += `➖ **Rendimiento estable - sin cambios significativos**\n\n`;
    }

    summary += `### Resumen\n`;
    summary += `- Mejoras: ${improvements}\n`;
    summary += `- Regresiones: ${regressions}\n`;
    summary += `- Estables: ${stable}\n\n`;

    // Mostrar regresiones más significativas
    if (regressions > 0) {
      summary += `### ⚠️ Regresiones Detectadas\n`;
      for (const [category, results] of Object.entries(comparison.results)) {
        for (const regression of results.regressions.slice(0, 3)) { // Top 3
          summary += `- **${regression.name}**: ${Math.abs(regression.improvement).toFixed(1)}% más lento\n`;
        }
      }
    }

    return summary;
  }

  async loadReport(filename) {
    const filepath = path.join(this.reportsDir, filename);
    const content = await fs.readFile(filepath, 'utf8');
    return JSON.parse(content);
  }

  async saveComparison(comparison) {
    const filename = `comparison-${Date.now()}.json`;
    const filepath = path.join(this.reportsDir, filename);
    await fs.writeFile(filepath, JSON.stringify(comparison, null, 2));
    return filename;
  }
}

module.exports = BenchmarkComparator;

Configuración de Alertas y Notificaciones
Sistema de Alertas de Rendimiento:
javascript

// utils/benchmark/BenchmarkAlerting.js
const nodemailer = require('nodemailer');
const slack = require('@slack/web-api');

class BenchmarkAlerting {
  constructor(config) {
    this.config = config;
    this.emailTransporter = this.setupEmailTransporter();
    this.slackClient = new slack.WebClient(config.slack?.token);
  }

  setupEmailTransporter() {
    if (!this.config.email) return null;
    
    return nodemailer.createTransporter({
      host: this.config.email.host,
      port: this.config.email.port,
      secure: this.config.email.secure,
      auth: {
        user: this.config.email.user,
        pass: this.config.email.password
      }
    });
  }

  async checkPerformanceThresholds(results) {
    const alerts = [];

    // Verificar umbrales de API
    if (results.api?.suite?.benchmarks) {
      for (const benchmark of results.api.suite.benchmarks) {
        if (benchmark.statistics?.mean > this.config.thresholds.api) {
          alerts.push({
            type: 'api_performance',
            severity: 'warning',
            message: `API endpoint ${benchmark.name} exceeded threshold: ${benchmark.statistics.mean.toFixed(2)}ms > ${this.config.thresholds.api}ms`,
            benchmark: benchmark.name,
            value: benchmark.statistics.mean,
            threshold: this.config.thresholds.api
          });
        }
      }
    }

    // Verificar umbrales de base de datos
    if (results.database?.queries?.queryResults) {
      for (const query of results.database.queries.queryResults) {
        if (query.statistics?.mean > this.config.thresholds.database) {
          alerts.push({
            type: 'database_performance',
            severity: 'warning',
            message: `Database query ${query.index} exceeded threshold: ${query.statistics.mean.toFixed(2)}ms > ${this.config.thresholds.database}ms`,
            query: query.index,
            value: query.statistics.mean,
            threshold: this.config.thresholds.database
          });
        }
      }
    }

    if (alerts.length > 0) {
      await this.sendAlerts(alerts);
    }

    return alerts;
  }

  async sendAlerts(alerts) {
    const summary = this.generateAlertSummary(alerts);
    
    // Enviar por email
    if (this.emailTransporter && this.config.email?.recipients) {
      await this.sendEmailAlert(summary, alerts);
    }

    // Enviar por Slack
    if (this.slackClient && this.config.slack?.channel) {
      await this.sendSlackAlert(summary, alerts);
    }

    console.log(`🚨 ${alerts.length} alerta(s) de rendimiento enviada(s)`);
  }

  generateAlertSummary(alerts) {
    const severityCounts = alerts.reduce((acc, alert) => {
      acc[alert.severity] = (acc[alert.severity] || 0) + 1;
      return acc;
    }, {});

    return {
      total: alerts.length,
      severityCounts,
      timestamp: new Date().toISOString()
    };
  }

  async sendEmailAlert(summary, alerts) {
    const html = `
      <h2>🚨 Alertas de Rendimiento</h2>
      <p><strong>Fecha:</strong> ${new Date(summary.timestamp).toLocaleString()}</p>
      <p><strong>Total de alertas:</strong> ${summary.total}</p>
      
      <h3>Detalles:</h3>
      <ul>
        ${alerts.map(alert => `
          <li>
            <strong>[${alert.severity.toUpperCase()}]</strong> ${alert.message}
            <br><small>Valor: ${alert.value?.toFixed(2)}ms | Umbral: ${alert.threshold}ms</small>
          </li>
        `).join('')}
      </ul>
    `;

    await this.emailTransporter.sendMail({
      from: this.config.email.from,
      to: this.config.email.recipients.join(', '),
      subject: `🚨 Alertas de Rendimiento - ${summary.total} alerta(s)`,
      html
    });
  }

  async sendSlackAlert(summary, alerts) {
    const blocks = [
      {
        type: 'header',
        text: {
          type: 'plain_text',
          text: '🚨 Alertas de Rendimiento'
        }
      },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*Total de alertas:* ${summary.total}\n*Fecha:* ${new Date(summary.timestamp).toLocaleString()}`
        }
      }
    ];

    for (const alert of alerts.slice(0, 5)) { // Máximo 5 alertas en Slack
      blocks.push({
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*[${alert.severity.toUpperCase()}]* ${alert.message}\nValor: ${alert.value?.toFixed(2)}ms | Umbral: ${alert.threshold}ms`
        }
      });
    }

    await this.slackClient.chat.postMessage({
      channel: this.config.slack.channel,
      blocks
    });
  }
}

module.exports = BenchmarkAlerting;

Esta implementación completa de la Sub/Subsección 3.5.3 "Evaluación Comparativa (Benchmarking)" proporciona un sistema integral para medir, comparar y monitorear el rendimiento de la aplicación en producción.

