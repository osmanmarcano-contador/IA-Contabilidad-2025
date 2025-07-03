Implementación de Backup de Archivos de Configuración
// backup-config.js - Sistema de Backup de Configuraciones
const fs = require('fs').promises;
const path = require('path');
const archiver = require('archiver');
const crypto = require('crypto');

class ConfigBackupManager {
    constructor() {
        this.backupPath = process.env.CONFIG_BACKUP_PATH || './backups/config';
        this.configPaths = [
            '.env',
            'config/',
            'nginx.conf',
            'pm2.json',
            'package.json',
            'docker-compose.yml'
        ];
        this.retentionDays = process.env.CONFIG_RETENTION_DAYS || 30;
    }

    async createBackup() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const backupName = `config-backup-${timestamp}`;
        const backupDir = path.join(this.backupPath, backupName);
        
        try {
            await fs.mkdir(backupDir, { recursive: true });
            
            const manifest = {
                timestamp: new Date().toISOString(),
                version: process.env.npm_package_version || '1.0.0',
                environment: process.env.NODE_ENV || 'production',
                files: []
            };

            // Backup archivos de configuración
            for (const configPath of this.configPaths) {
                await this.backupConfigFile(configPath, backupDir, manifest);
            }

            // Crear archivo comprimido
            const zipPath = await this.createZipArchive(backupDir, backupName);
            
            // Generar checksum
            const checksum = await this.generateChecksum(zipPath);
            manifest.checksum = checksum;
            
            // Guardar manifiesto
            await fs.writeFile(
                path.join(backupDir, 'manifest.json'),
                JSON.stringify(manifest, null, 2)
            );

            console.log(`✅ Backup de configuración creado: ${backupName}`);
            return { path: zipPath, manifest };
            
        } catch (error) {
            console.error('❌ Error en backup de configuración:', error);
            throw error;
        }
    }

    async backupConfigFile(configPath, backupDir, manifest) {
        const fullPath = path.resolve(configPath);
        
        try {
            const stats = await fs.stat(fullPath);
            
            if (stats.isFile()) {
                const content = await fs.readFile(fullPath);
                const backupFilePath = path.join(backupDir, path.basename(configPath));
                await fs.writeFile(backupFilePath, content);
                
                manifest.files.push({
                    original: configPath,
                    backup: path.basename(configPath),
                    size: stats.size,
                    modified: stats.mtime
                });
                
            } else if (stats.isDirectory()) {
                await this.backupConfigDirectory(fullPath, backupDir, manifest);
            }
        } catch (error) {
            if (error.code !== 'ENOENT') {
                console.warn(`⚠️  No se pudo respaldar ${configPath}:`, error.message);
            }
        }
    }

    async backupConfigDirectory(dirPath, backupDir, manifest) {
        const items = await fs.readdir(dirPath);
        const configDirName = path.basename(dirPath);
        const backupConfigDir = path.join(backupDir, configDirName);
        
        await fs.mkdir(backupConfigDir, { recursive: true });
        
        for (const item of items) {
            const itemPath = path.join(dirPath, item);
            const stats = await fs.stat(itemPath);
            
            if (stats.isFile()) {
                const content = await fs.readFile(itemPath);
                await fs.writeFile(path.join(backupConfigDir, item), content);
                
                manifest.files.push({
                    original: itemPath,
                    backup: path.join(configDirName, item),
                    size: stats.size,
                    modified: stats.mtime
                });
            }
        }
    }

    async createZipArchive(sourceDir, backupName) {
        const zipPath = path.join(this.backupPath, `${backupName}.zip`);
        const output = require('fs').createWriteStream(zipPath);
        const archive = archiver('zip', { zlib: { level: 9 } });
        
        return new Promise((resolve, reject) => {
            output.on('close', () => resolve(zipPath));
            archive.on('error', reject);
            
            archive.pipe(output);
            archive.directory(sourceDir, false);
            archive.finalize();
        });
    }

    async generateChecksum(filePath) {
        const content = await fs.readFile(filePath);
        return crypto.createHash('sha256').update(content).digest('hex');
    }

    async restoreConfig(backupPath) {
        try {
            const manifestPath = path.join(path.dirname(backupPath), 'manifest.json');
            const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
            
            console.log(`🔄 Restaurando configuración desde: ${backupPath}`);
            
            for (const file of manifest.files) {
                const backupFilePath = path.join(path.dirname(backupPath), file.backup);
                const originalPath = path.resolve(file.original);
                
                // Crear directorio si no existe
                await fs.mkdir(path.dirname(originalPath), { recursive: true });
                
                // Restaurar archivo
                const content = await fs.readFile(backupFilePath);
                await fs.writeFile(originalPath, content);
                
                console.log(`✅ Restaurado: ${file.original}`);
            }
            
            return manifest;
            
        } catch (error) {
            console.error('❌ Error restaurando configuración:', error);
            throw error;
        }
    }

    async validateBackup(backupPath) {
        try {
            const manifestPath = path.join(path.dirname(backupPath), 'manifest.json');
            const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
            
            // Verificar checksum
            const currentChecksum = await this.generateChecksum(backupPath);
            if (currentChecksum !== manifest.checksum) {
                throw new Error('Checksum no coincide - backup corrupto');
            }
            
            // Verificar archivos
            for (const file of manifest.files) {
                const backupFilePath = path.join(path.dirname(backupPath), file.backup);
                const stats = await fs.stat(backupFilePath);
                
                if (stats.size !== file.size) {
                    throw new Error(`Tamaño incorrecto para ${file.backup}`);
                }
            }
            
            console.log('✅ Backup de configuración validado correctamente');
            return true;
            
        } catch (error) {
            console.error('❌ Validación fallida:', error);
            return false;
        }
    }

    async cleanupOldBackups() {
        try {
            const backupFiles = await fs.readdir(this.backupPath);
            const cutoffDate = new Date();
            cutoffDate.setDate(cutoffDate.getDate() - this.retentionDays);
            
            for (const file of backupFiles) {
                if (file.startsWith('config-backup-')) {
                    const filePath = path.join(this.backupPath, file);
                    const stats = await fs.stat(filePath);
                    
                    if (stats.mtime < cutoffDate) {
                        await fs.unlink(filePath);
                        console.log(`🗑️  Eliminado backup antiguo: ${file}`);
                    }
                }
            }
        } catch (error) {
            console.error('❌ Error limpiando backups antiguos:', error);
        }
    }

    async scheduleBackup() {
        const schedule = require('node-cron');
        
        // Backup diario a las 2:00 AM
        schedule.schedule('0 2 * * *', async () => {
            console.log('🕐 Iniciando backup programado de configuración');
            await this.createBackup();
            await this.cleanupOldBackups();
        });
        
        console.log('📅 Backup programado de configuración activado');
    }
}

module.exports = ConfigBackupManager;
Script de Automatización
#!/bin/bash
# config-backup.sh - Script de backup de configuración

set -e

CONFIG_BACKUP_DIR="/var/backups/config"
LOG_FILE="/var/log/config-backup.log"

# Función de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Crear directorio de backup
mkdir -p "$CONFIG_BACKUP_DIR"

# Backup de configuración
log "Iniciando backup de configuración..."
node /path/to/your/app/scripts/config-backup.js

# Verificar backup
if [ $? -eq 0 ]; then
    log "✅ Backup de configuración completado"
else
    log "❌ Error en backup de configuración"
    exit 1
fi

# Sincronizar con almacenamiento remoto (opcional)
if [ -n "$REMOTE_BACKUP_PATH" ]; then
    log "Sincronizando con almacenamiento remoto..."
    rsync -av --delete "$CONFIG_BACKUP_DIR/" "$REMOTE_BACKUP_PATH/"
    log "✅ Sincronización completada"
fi

log "Proceso de backup de configuración finalizado"
Uso y Configuración
// Implementación en aplicación principal
const ConfigBackupManager = require('./backup-config');

const configBackup = new ConfigBackupManager();

// Crear backup manual
async function createConfigBackup() {
    try {
        const backup = await configBackup.createBackup();
        console.log('Backup creado:', backup.path);
    } catch (error) {
        console.error('Error creando backup:', error);
    }
}

// Restaurar configuración
async function restoreConfiguration(backupPath) {
    try {
        const manifest = await configBackup.restoreConfig(backupPath);
        console.log('Configuración restaurada:', manifest.timestamp);
    } catch (error) {
        console.error('Error restaurando:', error);
    }
}

// Iniciar backup programado
configBackup.scheduleBackup();
Variables de Entorno
# .env - Configuración de backup
CONFIG_BACKUP_PATH=/var/backups/config
CONFIG_RETENTION_DAYS=30
REMOTE_BACKUP_PATH=user@server:/backups/config
NODE_ENV=production
