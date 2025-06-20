3.5.1 Perfilado de Aplicación
El perfilado de aplicaciones es una técnica fundamental para identificar cuellos de botella, optimizar el rendimiento y garantizar una experiencia de usuario óptima en entornos de producción. Esta sección proporciona herramientas y metodologías para realizar un análisis profundo del rendimiento de aplicaciones Node.js.
Configuración del Entorno de Perfilado
Instalación de Dependencias de Perfilado
bash# Herramientas esenciales para perfilado
npm install --save-dev clinic autocannon 0x
npm install --save @google-cloud/profiler pprof
npm install --save-dev why-is-node-running
Configuración Básica del Profiler
javascript// config/profiler.js
const profiler = require('@google-cloud/profiler');

class ApplicationProfiler {
  constructor() {
    this.isProfilingEnabled = process.env.NODE_ENV === 'production' && 
                             process.env.ENABLE_PROFILING === 'true';
    this.profileConfig = {
      projectId: process.env.GOOGLE_CLOUD_PROJECT_ID,
      keyFilename: process.env.GOOGLE_CLOUD_KEYFILE,
      logLevel: process.env.PROFILER_LOG_LEVEL || 'info'
    };
  }

  async initializeProfiler() {
    if (!this.isProfilingEnabled) {
      console.log('Profiling disabled in current environment');
      return;
    }

    try {
      await profiler.start(this.profileConfig);
      console.log('Application profiler started successfully');
    } catch (error) {
      console.error('Failed to start profiler:', error);
    }
  }

  // Profiler condicional para desarrollo
  startDevelopmentProfiler() {
    if (process.env.NODE_ENV === 'development') {
      const inspector = require('inspector');
      inspector.open(9229, '127.0.0.1', true);
      console.log('Development profiler started on port 9229');
    }
  }
}

module.exports = new ApplicationProfiler();
Herramientas de Perfilado CPU
Configuración de Clinic.js
javascript// scripts/profile-cpu.js
const { exec } = require('child_process');
const path = require('path');

class CPUProfiler {
  constructor() {
    this.outputDir = path.join(process.cwd(), 'profiles', 'cpu');
    this.ensureOutputDir();
  }

  ensureOutputDir() {
    const fs = require('fs');
    if (!fs.existsSync(this.outputDir)) {
      fs.mkdirSync(this.outputDir, { recursive: true });
    }
  }

  // Perfilado con Clinic Doctor
  async profileWithClinicDoctor(duration = 30) {
    const timestamp = new Date().toISOString().replace(/:/g, '-');
    const outputPath = path.join(this.outputDir, `doctor-${timestamp}`);
    
    const command = `clinic doctor --dest ${outputPath} --duration ${duration}s -- node app.js`;
    
    return new Promise((resolve, reject) => {
      console.log(`Starting CPU profiling with Clinic Doctor for ${duration} seconds...`);
      
      exec(command, (error, stdout, stderr) => {
        if (error) {
          reject(error);
          return;
        }
        
        console.log('CPU profiling completed. Report available at:', outputPath);
        resolve({ outputPath, stdout, stderr });
      });
    });
  }

  // Perfilado con 0x
  async profileWith0x(duration = 30) {
    const timestamp = new Date().toISOString().replace(/:/g, '-');
    const outputPath = path.join(this.outputDir, `0x-${timestamp}`);
    
    const command = `0x --output-dir ${outputPath} --duration ${duration}s -- node app.js`;
    
    return new Promise((resolve, reject) => {
      console.log(`Starting flame graph generation with 0x for ${duration} seconds...`);
      
      exec(command, (error, stdout, stderr) => {
        if (error) {
          reject(error);
          return;
        }
        
        console.log('Flame graph generated. Report available at:', outputPath);
        resolve({ outputPath, stdout, stderr });
      });
    });
  }
}

module.exports = new CPUProfiler();
