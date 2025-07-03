Sistema de Backup Incremental y Diferencial
// incremental-backup.js - Sistema de Backup Incremental/Diferencial
const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const { spawn } = require('child_process');

class IncrementalBackupManager {
    constructor() {
        this.backupPath = process.env.INCREMENTAL_BACKUP_PATH || './backups/incremental';
        this.metadataPath = path.join(this.backupPath, 'metadata.json');
        this.sourcePaths = [
            process.env.APP_DATA_PATH || './data',
            process.env.UPLOADS_PATH || './uploads',
            process.env.LOGS_PATH || './logs'
        ];
        this.retentionDays = process.env.BACKUP_RETENTION_DAYS || 7;
    }

    async initializeBackup() {
        await fs.mkdir(this.backupPath, { recursive: true });
        
        const metadata = {
            lastFullBackup: null,
            lastIncrementalBackup: null,
            backupChain: [],
            fileHashes: {},
            version: '1.0.0'
        };
        
        try {
            await fs.access(this.metadataPath);
            const existing = JSON.parse(await fs.readFile(this.metadataPath, 'utf8'));
            return { ...metadata, ...existing };
        } catch {
            await fs.writeFile(this.metadataPath, JSON.stringify(metadata, null, 2));
            return metadata;
        }
    }

    async createFullBackup() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const backupName = `full-${timestamp}`;
        const backupDir = path.join(this.backupPath, backupName);
        
        try {
            await fs.mkdir(backupDir, { recursive: true });
            
            const metadata = await this.initializeBackup();
            const fileHashes = {};
            
            for (const sourcePath of this.sourcePaths) {
                await this.copyDirectoryWithHashes(sourcePath, backupDir, fileHashes);
            }
            
            const archivePath = await this.createArchive(backupDir, backupName);
            
            metadata.lastFullBackup = timestamp;
            metadata.lastIncrementalBackup = timestamp;
            metadata.backupChain = [{ type: 'full', timestamp, path: archivePath }];
            metadata.fileHashes = fileHashes;
            
            await fs.writeFile(this.metadataPath, JSON.stringify(metadata, null, 2));
            
            console.log(`✅ Backup completo creado: ${backupName}`);
            return { type: 'full', path: archivePath, timestamp };
            
        } catch (error) {
            console.error('❌ Error en backup completo:', error);
            throw error;
        }
    }

    async createIncrementalBackup() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const backupName = `incremental-${timestamp}`;
        const backupDir = path.join(this.backupPath, backupName);
        
        try {
            const metadata = await this.initializeBackup();
            
            if (!metadata.lastFullBackup) {
                console.log('⚠️  No hay backup completo. Creando backup completo...');
                return await this.createFullBackup();
            }
            
            await fs.mkdir(backupDir, { recursive: true });
            
            const changedFiles = await this.findChangedFiles(metadata.fileHashes);
            
            if (changedFiles.length === 0) {
                console.log('ℹ️  No hay cambios desde el último backup');
                return null;
            }
            
            const newHashes = { ...metadata.fileHashes };
            
            for (const fileInfo of changedFiles) {
                const relativePath = path.relative(process.cwd(), fileInfo.path);
                const backupFilePath = path.join(backupDir, relativePath);
                
                await fs.mkdir(path.dirname(backupFilePath), { recursive: true });
                await fs.copyFile(fileInfo.path, backupFilePath);
                
                newHashes[relativePath] = fileInfo.hash;
            }
            
            const archivePath = await this.createArchive(backupDir, backupName);
            
            metadata.lastIncrementalBackup = timestamp;
            metadata.backupChain.push({ 
                type: 'incremental', 
                timestamp, 
                path: archivePath,
                filesCount: changedFiles.length 
            });
            metadata.fileHashes = newHashes;
            
            await fs.writeFile(this.metadataPath, JSON.stringify(metadata, null, 2));
            
            console.log(`✅ Backup incremental creado: ${backupName} (${changedFiles.length} archivos)`);
            return { type: 'incremental', path: archivePath, timestamp, filesCount: changedFiles.length };
            
        } catch (error) {
            console.error('❌ Error en backup incremental:', error);
            throw error;
        }
    }

    async createDifferentialBackup() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const backupName = `differential-${timestamp}`;
        const backupDir = path.join(this.backupPath, backupName);
        
        try {
            const metadata = await this.initializeBackup();
            
            if (!metadata.lastFullBackup) {
                console.log('⚠️  No hay backup completo. Creando backup completo...');
                return await this.createFullBackup();
            }
            
            await fs.mkdir(backupDir, { recursive: true });
            
            const fullBackupMetadata = this.getFullBackupMetadata(metadata);
            const changedFiles = await this.findChangedFiles(fullBackupMetadata.fileHashes);
            
            if (changedFiles.length === 0) {
                console.log('ℹ️  No hay cambios desde el último backup completo');
                return null;
            }
            
            for (const fileInfo of changedFiles) {
                const relativePath = path.relative(process.cwd(), fileInfo.path);
                const backupFilePath = path.join(backupDir, relativePath);
                
                await fs.mkdir(path.dirname(backupFilePath), { recursive: true });
                await fs.copyFile(fileInfo.path, backupFilePath);
            }
            
            const archivePath = await this.createArchive(backupDir, backupName);
            
            metadata.backupChain.push({ 
                type: 'differential', 
                timestamp, 
                path: archivePath,
                filesCount: changedFiles.length,
                basedOn: metadata.lastFullBackup
            });
            
            await fs.writeFile(this.metadataPath, JSON.stringify(metadata, null, 2));
            
            console.log(`✅ Backup diferencial creado: ${backupName} (${changedFiles.length} archivos)`);
            return { type: 'differential', path: archivePath, timestamp, filesCount: changedFiles.length };
            
        } catch (error) {
            console.error('❌ Error en backup diferencial:', error);
            throw error;
        }
    }

    async findChangedFiles(baselineHashes) {
        const changedFiles = [];
        
        for (const sourcePath of this.sourcePaths) {
            await this.scanForChanges(sourcePath, baselineHashes, changedFiles);
        }
        
        return changedFiles;
    }

    async scanForChanges(dirPath, baselineHashes, changedFiles) {
        try {
            const items = await fs.readdir(dirPath);
            
            for (const item of items) {
                const itemPath = path.join(dirPath, item);
                const stats = await fs.stat(itemPath);
                
                if (stats.isDirectory()) {
                    await this.scanForChanges(itemPath, baselineHashes, changedFiles);
                } else if (stats.isFile()) {
                    const relativePath = path.relative(process.cwd(), itemPath);
                    const currentHash = await this.calculateFileHash(itemPath);
                    
                    if (!baselineHashes[relativePath] || baselineHashes[relativePath] !== currentHash) {
                        changedFiles.push({ path: itemPath, hash: currentHash, size: stats.size });
                    }
                }
            }
        } catch (error) {
            if (error.code !== 'ENOENT') {
                console.warn(`⚠️  Error escaneando ${dirPath}:`, error.message);
            }
        }
    }

    async copyDirectoryWithHashes(sourcePath, targetPath, fileHashes) {
        try {
            const items = await fs.readdir(sourcePath);
            const targetDir = path.join(targetPath, path.basename(sourcePath));
            
            await fs.mkdir(targetDir, { recursive: true });
            
            for (const item of items) {
                const sourceItem = path.join(sourcePath, item);
                const targetItem = path.join(targetDir, item);
                const stats = await fs.stat(sourceItem);
                
                if (stats.isDirectory()) {
                    await this.copyDirectoryWithHashes(sourceItem, targetDir, fileHashes);
                } else if (stats.isFile()) {
                    await fs.copyFile(sourceItem, targetItem);
                    const relativePath = path.relative(process.cwd(), sourceItem);
                    fileHashes[relativePath] = await this.calculateFileHash(sourceItem);
                }
            }
        } catch (error) {
            if (error.code !== 'ENOENT') {
                console.warn(`⚠️  Error copiando ${sourcePath}:`, error.message);
            }
        }
    }

    async calculateFileHash(filePath) {
        const content = await fs.readFile(filePath);
        return crypto.createHash('sha256').update(content).digest('hex');
    }

    async createArchive(sourceDir, name) {
        return new Promise((resolve, reject) => {
            const archivePath = path.join(this.backupPath, `${name}.tar.gz`);
            const tar = spawn('tar', ['-czf', archivePath, '-C', sourceDir, '.']);
            
            tar.on('close', (code) => {
                if (code === 0) {
                    resolve(archivePath);
                } else {
                    reject(new Error(`tar exited with code ${code}`));
                }
            });
            
            tar.on('error', reject);
        });
    }

    getFullBackupMetadata(metadata) {
        const fullBackup = metadata.backupChain.find(b => b.type === 'full');
        return fullBackup || { fileHashes: {} };
    }

    async restoreFromBackupChain(targetTimestamp) {
        const metadata = await this.initializeBackup();
        const restoreChain = this.buildRestoreChain(metadata.backupChain, targetTimestamp);
        
        console.log(`🔄 Restaurando desde cadena de ${restoreChain.length} backups`);
        
        for (const backup of restoreChain) {
            await this.extractBackup(backup.path);
            console.log(`✅ Restaurado: ${backup.type} ${backup.timestamp}`);
        }
        
        return restoreChain;
    }

    buildRestoreChain(backupChain, targetTimestamp) {
        const target = backupChain.find(b => b.timestamp === targetTimestamp);
        if (!target) throw new Error('Backup no encontrado');
        
        if (target.type === 'full') {
            return [target];
        }
        
        const fullBackup = backupChain.find(b => b.type === 'full');
        const incrementals = backupChain
            .filter(b => b.type === 'incremental' && b.timestamp <= targetTimestamp)
            .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
        
        return [fullBackup, ...incrementals];
    }

    async extractBackup(backupPath) {
        return new Promise((resolve, reject) => {
            const tar = spawn('tar', ['-xzf', backupPath, '-C', process.cwd()]);
            
            tar.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error(`tar extract failed with code ${code}`));
                }
            });
            
            tar.on('error', reject);
        });
    }

    async cleanupOldBackups() {
        const metadata = await this.initializeBackup();
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - this.retentionDays);
        
        const toDelete = metadata.backupChain.filter(b => 
            new Date(b.timestamp) < cutoffDate && b.type !== 'full'
        );
        
        for (const backup of toDelete) {
            try {
                await fs.unlink(backup.path);
                console.log(`🗑️  Eliminado: ${backup.type} ${backup.timestamp}`);
            } catch (error) {
                console.warn(`⚠️  Error eliminando ${backup.path}:`, error.message);
            }
        }
        
        metadata.backupChain = metadata.backupChain.filter(b => !toDelete.includes(b));
        await fs.writeFile(this.metadataPath, JSON.stringify(metadata, null, 2));
    }
}

module.exports = IncrementalBackupManager;
Automatización y Programación
// backup-scheduler.js - Programador de backups
const schedule = require('node-cron');
const IncrementalBackupManager = require('./incremental-backup');

class BackupScheduler {
    constructor() {
        this.backupManager = new IncrementalBackupManager();
    }

    start() {
        // Backup completo semanal (domingo 1:00 AM)
        schedule.schedule('0 1 * * 0', async () => {
            console.log('🕐 Iniciando backup completo programado');
            await this.backupManager.createFullBackup();
        });

        // Backup incremental diario (2:00 AM)
        schedule.schedule('0 2 * * 1-6', async () => {
            console.log('🕐 Iniciando backup incremental programado');
            await this.backupManager.createIncrementalBackup();
        });

        // Limpieza semanal (lunes 3:00 AM)
        schedule.schedule('0 3 * * 1', async () => {
            console.log('🕐 Limpiando backups antiguos');
            await this.backupManager.cleanupOldBackups();
        });

        console.log('📅 Programador de backups iniciado');
    }
}

module.exports = BackupScheduler;
Variables de Entorno
# Configuración de backup incremental
INCREMENTAL_BACKUP_PATH=/var/backups/incremental
APP_DATA_PATH=/var/www/app/data
UPLOADS_PATH=/var/www/app/uploads
LOGS_PATH=/var/www/app/logs
BACKUP_RETENTION_DAYS=7
