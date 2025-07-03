Configuración Automática de Backups
// backup-config.js
const BACKUP_CONFIG = {
  mongodb: {
    uri: process.env.MONGODB_URI,
    databases: ['production', 'logs', 'analytics'],
    retention: { daily: 7, weekly: 4, monthly: 12 },
    compression: true,
    encryption: true
  },
  postgresql: {
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    databases: ['main_db', 'audit_db'],
    user: process.env.DB_BACKUP_USER,
    retention: { daily: 7, weekly: 4, monthly: 12 },
    compression: true
  },
  storage: {
    local: '/backups/database',
    s3: { bucket: process.env.S3_BACKUP_BUCKET, region: 'us-east-1' },
    gcs: { bucket: process.env.GCS_BACKUP_BUCKET, project: process.env.GCP_PROJECT }
  }
};

module.exports = BACKUP_CONFIG;
Automatización de Backup MongoDB
// mongodb-backup.js
const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const { S3Client, PutObjectCommand } = require('@aws-sdk/client-s3');
const { createGzip } = require('zlib');
const { pipeline } = require('stream/promises');

class MongoBackup {
  constructor(config) {
    this.config = config;
    this.s3 = new S3Client({ region: config.storage.s3.region });
  }

  async createBackup(database) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupPath = path.join(this.config.storage.local, `${database}_${timestamp}`);
    
    const mongodump = spawn('mongodump', [
      '--uri', this.config.mongodb.uri,
      '--db', database,
      '--out', backupPath,
      '--gzip'
    ]);

    return new Promise((resolve, reject) => {
      mongodump.on('close', (code) => {
        code === 0 ? resolve(backupPath) : reject(new Error(`Backup failed: ${code}`));
      });
    });
  }

  async compressBackup(backupPath) {
    const tarPath = `${backupPath}.tar.gz`;
    const tar = spawn('tar', ['-czf', tarPath, '-C', path.dirname(backupPath), path.basename(backupPath)]);
    
    return new Promise((resolve, reject) => {
      tar.on('close', (code) => {
        code === 0 ? resolve(tarPath) : reject(new Error(`Compression failed: ${code}`));
      });
    });
  }

  async uploadToS3(filePath, database) {
    const fileStream = require('fs').createReadStream(filePath);
    const fileName = path.basename(filePath);
    
    const command = new PutObjectCommand({
      Bucket: this.config.storage.s3.bucket,
      Key: `mongodb/${database}/${fileName}`,
      Body: fileStream,
      ServerSideEncryption: 'AES256'
    });

    return await this.s3.send(command);
  }

  async cleanup(localPath, retentionDays = 7) {
    const cutoffDate = new Date(Date.now() - (retentionDays * 24 * 60 * 60 * 1000));
    const files = await fs.readdir(this.config.storage.local);
    
    for (const file of files) {
      const filePath = path.join(this.config.storage.local, file);
      const stats = await fs.stat(filePath);
      if (stats.mtime < cutoffDate) {
        await fs.unlink(filePath);
      }
    }
  }
}
Automatización de Backup PostgreSQL
// postgresql-backup.js
const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');

class PostgreSQLBackup {
  constructor(config) {
    this.config = config;
  }

  async createBackup(database) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupFile = path.join(this.config.storage.local, `${database}_${timestamp}.sql`);
    
    const pgDump = spawn('pg_dump', [
      '-h', this.config.postgresql.host,
      '-p', this.config.postgresql.port,
      '-U', this.config.postgresql.user,
      '-d', database,
      '--no-password',
      '--verbose',
      '--clean',
      '--if-exists',
      '--format=custom',
      '--file', backupFile
    ], {
      env: { ...process.env, PGPASSWORD: process.env.DB_BACKUP_PASSWORD }
    });

    return new Promise((resolve, reject) => {
      pgDump.on('close', (code) => {
        code === 0 ? resolve(backupFile) : reject(new Error(`PostgreSQL backup failed: ${code}`));
      });
    });
  }

  async createFullClusterBackup() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupFile = path.join(this.config.storage.local, `cluster_${timestamp}.sql`);
    
    const pgDumpAll = spawn('pg_dumpall', [
      '-h', this.config.postgresql.host,
      '-p', this.config.postgresql.port,
      '-U', this.config.postgresql.user,
      '--no-password',
      '--verbose',
      '--clean',
      '--file', backupFile
    ], {
      env: { ...process.env, PGPASSWORD: process.env.DB_BACKUP_PASSWORD }
    });

    return new Promise((resolve, reject) => {
      pgDumpAll.on('close', (code) => {
        code === 0 ? resolve(backupFile) : reject(new Error(`Cluster backup failed: ${code}`));
      });
    });
  }
}
Orquestador de Backups
// backup-orchestrator.js
const cron = require('node-cron');
const MongoBackup = require('./mongodb-backup');
const PostgreSQLBackup = require('./postgresql-backup');
const BACKUP_CONFIG = require('./backup-config');

class BackupOrchestrator {
  constructor() {
    this.mongoBackup = new MongoBackup(BACKUP_CONFIG);
    this.pgBackup = new PostgreSQLBackup(BACKUP_CONFIG);
    this.setupSchedules();
  }

  setupSchedules() {
    // Backup diario a las 2:00 AM
    cron.schedule('0 2 * * *', () => this.executeDailyBackup());
    
    // Backup semanal los domingos a las 3:00 AM
    cron.schedule('0 3 * * 0', () => this.executeWeeklyBackup());
    
    // Backup mensual el primer día del mes a las 4:00 AM
    cron.schedule('0 4 1 * *', () => this.executeMonthlyBackup());
  }

  async executeDailyBackup() {
    try {
      console.log('Iniciando backup diario...');
      
      // MongoDB backups
      for (const db of BACKUP_CONFIG.mongodb.databases) {
        const backupPath = await this.mongoBackup.createBackup(db);
        const compressedPath = await this.mongoBackup.compressBackup(backupPath);
        await this.mongoBackup.uploadToS3(compressedPath, db);
      }
      
      // PostgreSQL backups
      for (const db of BACKUP_CONFIG.postgresql.databases) {
        const backupPath = await this.pgBackup.createBackup(db);
        // Comprimir y subir similar a MongoDB
      }
      
      // Cleanup local files
      await this.mongoBackup.cleanup(BACKUP_CONFIG.storage.local, 7);
      
      console.log('Backup diario completado exitosamente');
    } catch (error) {
      console.error('Error en backup diario:', error);
      this.sendAlert('DAILY_BACKUP_FAILED', error.message);
    }
  }

  async executeWeeklyBackup() {
    // Implementación similar con retención semanal
  }

  async executeMonthlyBackup() {
    // Implementación similar con retención mensual
  }

  sendAlert(type, message) {
    // Integración con sistema de alertas (Slack, email, etc.)
    console.error(`ALERT [${type}]: ${message}`);
  }
}

module.exports = BackupOrchestrator;
Script de Inicialización
// init-backup.js
const BackupOrchestrator = require('./backup-orchestrator');
const fs = require('fs').promises;
const path = require('path');

async function initializeBackupSystem() {
  try {
    // Crear directorios necesarios
    await fs.mkdir('/backups/database', { recursive: true });
    await fs.mkdir('/backups/logs', { recursive: true });
    
    // Verificar conexiones de base de datos
    await verifyDatabaseConnections();
    
    // Inicializar orquestador
    const orchestrator = new BackupOrchestrator();
    
    console.log('Sistema de backup inicializado correctamente');
    
    // Ejecutar backup inicial para prueba
    await orchestrator.executeDailyBackup();
    
  } catch (error) {
    console.error('Error inicializando sistema de backup:', error);
    process.exit(1);
  }
}

async function verifyDatabaseConnections() {
  // Verificar MongoDB
  const { MongoClient } = require('mongodb');
  const mongoClient = new MongoClient(process.env.MONGODB_URI);
  await mongoClient.connect();
  await mongoClient.close();
  
  // Verificar PostgreSQL
  const { Client } = require('pg');
  const pgClient = new Client({
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    user: process.env.DB_BACKUP_USER,
    password: process.env.DB_BACKUP_PASSWORD
  });
  await pgClient.connect();
  await pgClient.end();
}

// Ejecutar si es llamado directamente
if (require.main === module) {
  initializeBackupSystem();
}

module.exports = { initializeBackupSystem };
Variables de Entorno Requeridas
# .env.backup
# MongoDB
MONGODB_URI=mongodb://localhost:27017

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_BACKUP_USER=backup_user
DB_BACKUP_PASSWORD=secure_password

# Cloud Storage
S3_BACKUP_BUCKET=company-backups
GCS_BACKUP_BUCKET=company-backups-gcs
GCP_PROJECT=company-project-id

# Alertas
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
EMAIL_ALERT_TO=admin@company.com
