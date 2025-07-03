Configuración de Backup de Archivos
// file-backup-config.js
const FILE_BACKUP_CONFIG = {
  sources: {
    application: ['/app', '/var/www', '/opt/app'],
    config: ['/etc/nginx', '/etc/ssl', '/etc/systemd'],
    logs: ['/var/log', '/app/logs'],
    uploads: ['/app/uploads', '/var/uploads'],
    scripts: ['/scripts', '/home/deploy/scripts']
  },
  exclusions: [
    '*.log', '*.tmp', 'node_modules', '.git', 'cache/*', 
    '*.sock', '/proc', '/sys', '/dev', '/tmp'
  ],
  destinations: {
    local: '/backups/files',
    s3: { bucket: process.env.S3_FILE_BACKUP_BUCKET, prefix: 'system-files/' },
    rsync: { host: process.env.BACKUP_SERVER, path: '/backups/files/', user: 'backup' }
  },
  retention: { daily: 7, weekly: 4, monthly: 12 },
  compression: { level: 6, algorithm: 'gzip' },
  encryption: { enabled: true, key: process.env.BACKUP_ENCRYPTION_KEY }
};

module.exports = FILE_BACKUP_CONFIG;
Gestor de Backup de Archivos
// file-backup-manager.js
const fs = require('fs').promises;
const path = require('path');
const { spawn } = require('child_process');
const { createReadStream, createWriteStream } = require('fs');
const { createGzip } = require('zlib');
const { createCipher } = require('crypto');
const { S3Client, PutObjectCommand } = require('@aws-sdk/client-s3');

class FileBackupManager {
  constructor(config) {
    this.config = config;
    this.s3 = new S3Client({ region: 'us-east-1' });
  }

  async createFileBackup(backupType = 'daily') {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupName = `${backupType}_${timestamp}`;
    const backupPath = path.join(this.config.destinations.local, `${backupName}.tar.gz`);
    
    try {
      await this.ensureBackupDirectory();
      const sourcePaths = this.collectSourcePaths();
      await this.createTarBackup(sourcePaths, backupPath);
      
      if (this.config.encryption.enabled) {
        await this.encryptBackup(backupPath);
      }
      
      await this.uploadBackup(backupPath, backupName);
      await this.syncToRemote(backupPath);
      
      return backupPath;
    } catch (error) {
      throw new Error(`Backup failed: ${error.message}`);
    }
  }

  async ensureBackupDirectory() {
    await fs.mkdir(this.config.destinations.local, { recursive: true });
  }

  collectSourcePaths() {
    const paths = [];
    Object.values(this.config.sources).forEach(sourceArray => {
      paths.push(...sourceArray);
    });
    return paths;
  }

  async createTarBackup(sources, outputPath) {
    const excludeArgs = this.config.exclusions.flatMap(pattern => ['--exclude', pattern]);
    const tarArgs = [
      '-czf', outputPath,
      '--absolute-names',
      '--ignore-failed-read',
      ...excludeArgs,
      ...sources
    ];

    return new Promise((resolve, reject) => {
      const tar = spawn('tar', tarArgs);
      let stderr = '';
      
      tar.stderr.on('data', (data) => {
        stderr += data.toString();
      });
      
      tar.on('close', (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error(`Tar backup failed: ${stderr}`));
        }
      });
    });
  }

  async encryptBackup(filePath) {
    const encryptedPath = `${filePath}.enc`;
    const cipher = createCipher('aes-256-cbc', this.config.encryption.key);
    const input = createReadStream(filePath);
    const output = createWriteStream(encryptedPath);

    await new Promise((resolve, reject) => {
      input.pipe(cipher).pipe(output);
      output.on('finish', resolve);
      output.on('error', reject);
    });

    await fs.unlink(filePath);
    await fs.rename(encryptedPath, filePath);
  }

  async uploadBackup(filePath, backupName) {
    const fileStream = createReadStream(filePath);
    const key = `${this.config.destinations.s3.prefix}${backupName}.tar.gz`;
    
    const command = new PutObjectCommand({
      Bucket: this.config.destinations.s3.bucket,
      Key: key,
      Body: fileStream,
      ServerSideEncryption: 'AES256',
      StorageClass: 'STANDARD_IA'
    });

    await this.s3.send(command);
  }

  async syncToRemote(filePath) {
    const { host, path: remotePath, user } = this.config.destinations.rsync;
    
    return new Promise((resolve, reject) => {
      const rsync = spawn('rsync', [
        '-avz',
        '--compress',
        '--progress',
        filePath,
        `${user}@${host}:${remotePath}`
      ]);

      rsync.on('close', (code) => {
        code === 0 ? resolve() : reject(new Error(`Rsync failed: ${code}`));
      });
    });
  }

  async createIncrementalBackup(lastBackupPath) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const backupName = `incremental_${timestamp}`;
    const backupPath = path.join(this.config.destinations.local, `${backupName}.tar.gz`);
    
    const sourcePaths = this.collectSourcePaths();
    const excludeArgs = this.config.exclusions.flatMap(pattern => ['--exclude', pattern]);
    
    const tarArgs = [
      '-czf', backupPath,
      '--newer-mtime', await this.getLastBackupDate(lastBackupPath),
      '--absolute-names',
      '--ignore-failed-read',
      ...excludeArgs,
      ...sourcePaths
    ];

    return new Promise((resolve, reject) => {
      const tar = spawn('tar', tarArgs);
      tar.on('close', (code) => {
        code === 0 ? resolve(backupPath) : reject(new Error(`Incremental backup failed: ${code}`));
      });
    });
  }

  async getLastBackupDate(backupPath) {
    const stats = await fs.stat(backupPath);
    return stats.mtime.toISOString();
  }

  async cleanupOldBackups() {
    const files = await fs.readdir(this.config.destinations.local);
    const backupFiles = files.filter(file => file.endsWith('.tar.gz'));
    
    const fileStats = await Promise.all(
      backupFiles.map(async (file) => {
        const filePath = path.join(this.config.destinations.local, file);
        const stats = await fs.stat(filePath);
        return { file, path: filePath, mtime: stats.mtime };
      })
    );

    const cutoffDate = new Date(Date.now() - (this.config.retention.daily * 24 * 60 * 60 * 1000));
    const filesToDelete = fileStats.filter(({ mtime }) => mtime < cutoffDate);

    await Promise.all(
      filesToDelete.map(({ path }) => fs.unlink(path))
    );

    return filesToDelete.length;
  }

  async verifyBackup(backupPath) {
    return new Promise((resolve, reject) => {
      const tar = spawn('tar', ['-tzf', backupPath]);
      let fileCount = 0;
      
      tar.stdout.on('data', (data) => {
        fileCount += data.toString().split('\n').length - 1;
      });
      
      tar.on('close', (code) => {
        if (code === 0 && fileCount > 0) {
          resolve({ valid: true, fileCount });
        } else {
          reject(new Error('Backup verification failed'));
        }
      });
    });
  }
}
Programador de Backups
// file-backup-scheduler.js
const cron = require('node-cron');
const FileBackupManager = require('./file-backup-manager');
const FILE_BACKUP_CONFIG = require('./file-backup-config');

class FileBackupScheduler {
  constructor() {
    this.backupManager = new FileBackupManager(FILE_BACKUP_CONFIG);
    this.initializeSchedules();
  }

  initializeSchedules() {
    // Backup diario a las 1:00 AM
    cron.schedule('0 1 * * *', () => this.executeBackup('daily'));
    
    // Backup semanal los domingos a las 2:00 AM
    cron.schedule('0 2 * * 0', () => this.executeBackup('weekly'));
    
    // Backup mensual el primer día del mes a las 3:00 AM
    cron.schedule('0 3 1 * *', () => this.executeBackup('monthly'));
    
    // Cleanup diario a las 4:00 AM
    cron.schedule('0 4 * * *', () => this.executeCleanup());
  }

  async executeBackup(type) {
    try {
      console.log(`Iniciando backup ${type} de archivos...`);
      const backupPath = await this.backupManager.createFileBackup(type);
      
      // Verificar backup
      const verification = await this.backupManager.verifyBackup(backupPath);
      console.log(`Backup ${type} completado: ${verification.fileCount} archivos`);
      
      // Notificar éxito
      await this.sendNotification('SUCCESS', `Backup ${type} completado exitosamente`);
      
    } catch (error) {
      console.error(`Error en backup ${type}:`, error);
      await this.sendNotification('ERROR', `Backup ${type} falló: ${error.message}`);
    }
  }

  async executeCleanup() {
    try {
      const deletedCount = await this.backupManager.cleanupOldBackups();
      console.log(`Cleanup completado: ${deletedCount} archivos eliminados`);
    } catch (error) {
      console.error('Error en cleanup:', error);
    }
  }

  async sendNotification(level, message) {
    // Implementar notificaciones (Slack, email, etc.)
    console.log(`[${level}] ${message}`);
  }
}

module.exports = FileBackupScheduler;
Utilidades de Backup
// backup-utilities.js
const fs = require('fs').promises;
const path = require('path');
const { spawn } = require('child_process');

class BackupUtilities {
  static async calculateDirectorySize(dirPath) {
    const stats = await fs.stat(dirPath);
    if (stats.isFile()) return stats.size;
    
    const files = await fs.readdir(dirPath);
    const sizes = await Promise.all(
      files.map(file => this.calculateDirectorySize(path.join(dirPath, file)))
    );
    
    return sizes.reduce((total, size) => total + size, 0);
  }

  static async getDiskUsage(path) {
    return new Promise((resolve, reject) => {
      const df = spawn('df', ['-h', path]);
      let output = '';
      
      df.stdout.on('data', (data) => {
        output += data.toString();
      });
      
      df.on('close', (code) => {
        if (code === 0) {
          const lines = output.trim().split('\n');
          const data = lines[1].split(/\s+/);
          resolve({
            filesystem: data[0],
            size: data[1],
            used: data[2],
            available: data[3],
            usePercent: data[4]
          });
        } else {
          reject(new Error('Failed to get disk usage'));
        }
      });
    });
  }

  static async createBackupReport(backupPath) {
    const stats = await fs.stat(backupPath);
    const diskUsage = await this.getDiskUsage(path.dirname(backupPath));
    
    return {
      backupFile: path.basename(backupPath),
      size: this.formatBytes(stats.size),
      created: stats.birthtime.toISOString(),
      diskUsage: diskUsage
    };
  }

  static formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}

module.exports = BackupUtilities;
Inicializador del Sistema
// init-file-backup.js
const FileBackupScheduler = require('./file-backup-scheduler');
const BackupUtilities = require('./backup-utilities');
const FILE_BACKUP_CONFIG = require('./file-backup-config');

async function initializeFileBackupSystem() {
  try {
    // Verificar directorios de origen
    await verifySourceDirectories();
    
    // Crear directorios de destino
    await createBackupDirectories();
    
    // Verificar espacio en disco
    await checkDiskSpace();
    
    // Inicializar scheduler
    const scheduler = new FileBackupScheduler();
    
    console.log('Sistema de backup de archivos inicializado correctamente');
    
    // Ejecutar backup de prueba
    await scheduler.executeBackup('test');
    
  } catch (error) {
    console.error('Error inicializando sistema de backup de archivos:', error);
    process.exit(1);
  }
}

async function verifySourceDirectories() {
  const allSources = Object.values(FILE_BACKUP_CONFIG.sources).flat();
  
  for (const source of allSources) {
    try {
      await fs.access(source);
    } catch (error) {
      console.warn(`Directorio de origen no encontrado: ${source}`);
    }
  }
}

async function createBackupDirectories() {
  await fs.mkdir(FILE_BACKUP_CONFIG.destinations.local, { recursive: true });
}

async function checkDiskSpace() {
  const usage = await BackupUtilities.getDiskUsage(FILE_BACKUP_CONFIG.destinations.local);
  const usedPercent = parseInt(usage.usePercent);
  
  if (usedPercent > 80) {
    console.warn(`Advertencia: Espacio en disco limitado (${usage.usePercent} usado)`);
  }
}

if (require.main === module) {
  initializeFileBackupSystem();
}

module.exports = { initializeFileBackupSystem };
