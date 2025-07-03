Sistema de Validación de Backups
// backup-validator.js - Sistema de Validación de Backups
const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const { spawn } = require('child_process');

class BackupValidator {
    constructor() {
        this.backupPaths = [
            process.env.DB_BACKUP_PATH || './backups/database',
            process.env.FILES_BACKUP_PATH || './backups/files',
            process.env.CONFIG_BACKUP_PATH || './backups/config',
            process.env.INCREMENTAL_BACKUP_PATH || './backups/incremental'
        ];
        this.validationResults = [];
        this.criticalFailures = [];
    }

    async validateAllBackups() {
        console.log('🔍 Iniciando validación completa de backups');
        this.validationResults = [];
        this.criticalFailures = [];
        
        const results = {
            timestamp: new Date().toISOString(),
            totalBackups: 0,
            validBackups: 0,
            failedBackups: 0,
            criticalFailures: 0,
            details: []
        };

        for (const backupPath of this.backupPaths) {
            try {
                const backupType = path.basename(backupPath);
                const backupResults = await this.validateBackupDirectory(backupPath, backupType);
                
                results.totalBackups += backupResults.length;
                results.validBackups += backupResults.filter(r => r.valid).length;
                results.failedBackups += backupResults.filter(r => !r.valid).length;
                results.details.push(...backupResults);
                
            } catch (error) {
                console.error(`❌ Error validando ${backupPath}:`, error.message);
                this.criticalFailures.push({ path: backupPath, error: error.message });
            }
        }

        results.criticalFailures = this.criticalFailures.length;
        await this.generateValidationReport(results);
        
        console.log(`✅ Validación completa: ${results.validBackups}/${results.totalBackups} backups válidos`);
        return results;
    }

    async validateBackupDirectory(backupPath, backupType) {
        const results = [];
        
        try {
            const files = await fs.readdir(backupPath);
            const backupFiles = files.filter(f => 
                f.endsWith('.sql') || f.endsWith('.tar.gz') || f.endsWith('.zip')
            );

            for (const file of backupFiles) {
                const filePath = path.join(backupPath, file);
                const result = await this.validateSingleBackup(filePath, backupType);
                results.push(result);
            }
            
        } catch (error) {
            if (error.code !== 'ENOENT') {
                console.error(`❌ Error accediendo a ${backupPath}:`, error.message);
            }
        }
        
        return results;
    }

    async validateSingleBackup(backupPath, backupType) {
        const result = {
            path: backupPath,
            type: backupType,
            filename: path.basename(backupPath),
            valid: false,
            checks: {},
            errors: [],
            warnings: [],
            metadata: {}
        };

        try {
            // Validación de existencia y permisos
            const stats = await fs.stat(backupPath);
            result.metadata.size = stats.size;
            result.metadata.created = stats.birthtime;
            result.metadata.modified = stats.mtime;
            result.checks.exists = true;
            
            // Validación de tamaño mínimo
            if (stats.size < 1024) {
                result.errors.push('Backup demasiado pequeño (<1KB)');
                result.checks.sizeCheck = false;
            } else {
                result.checks.sizeCheck = true;
            }

            // Validación de integridad según tipo
            await this.validateByType(backupPath, backupType, result);

            // Validación de checksum si existe
            await this.validateChecksum(backupPath, result);

            // Validación de edad del backup
            this.validateBackupAge(result);

            // Determinar validez general
            result.valid = result.errors.length === 0 && 
                          Object.values(result.checks).every(check => check === true);

        } catch (error) {
            result.errors.push(`Error de validación: ${error.message}`);
            result.checks.accessible = false;
        }

        return result;
    }

    async validateByType(backupPath, backupType, result) {
        const extension = path.extname(backupPath).toLowerCase();
        
        switch (extension) {
            case '.sql':
                await this.validateSQLBackup(backupPath, result);
                break;
            case '.tar.gz':
            case '.tgz':
                await this.validateTarGzBackup(backupPath, result);
                break;
            case '.zip':
                await this.validateZipBackup(backupPath, result);
                break;
            default:
                result.warnings.push(`Tipo de archivo no reconocido: ${extension}`);
        }
    }

    async validateSQLBackup(backupPath, result) {
        try {
            const content = await fs.readFile(backupPath, 'utf8');
            
            // Verificar estructura SQL básica
            const sqlChecks = {
                hasHeader: content.includes('-- MySQL dump') || content.includes('-- PostgreSQL database dump'),
                hasCreateTable: content.includes('CREATE TABLE'),
                hasInsertData: content.includes('INSERT INTO'),
                hasValidSyntax: !content.includes('ERROR') && !content.includes('FAILED')
            };

            result.checks.sqlStructure = sqlChecks.hasHeader && sqlChecks.hasCreateTable;
            result.checks.hasData = sqlChecks.hasInsertData;
            result.checks.syntaxValid = sqlChecks.hasValidSyntax;
            
            if (!sqlChecks.hasValidSyntax) {
                result.errors.push('Archivo SQL contiene errores de sintaxis');
            }
            
            // Contar tablas y registros aproximados
            const tableMatches = content.match(/CREATE TABLE/g);
            const insertMatches = content.match(/INSERT INTO/g);
            
            result.metadata.tablesCount = tableMatches ? tableMatches.length : 0;
            result.metadata.insertsCount = insertMatches ? insertMatches.length : 0;
            
        } catch (error) {
            result.errors.push(`Error validando SQL: ${error.message}`);
            result.checks.sqlStructure = false;
        }
    }

    async validateTarGzBackup(backupPath, result) {
        try {
            const isValid = await this.testTarGzIntegrity(backupPath);
            result.checks.archiveIntegrity = isValid;
            
            if (!isValid) {
                result.errors.push('Archivo tar.gz corrupto o dañado');
            }
            
            // Obtener lista de archivos
            const fileList = await this.getTarGzFileList(backupPath);
            result.metadata.filesCount = fileList.length;
            result.metadata.hasManifest = fileList.includes('manifest.json');
            
        } catch (error) {
            result.errors.push(`Error validando tar.gz: ${error.message}`);
            result.checks.archiveIntegrity = false;
        }
    }

    async validateZipBackup(backupPath, result) {
        try {
            const isValid = await this.testZipIntegrity(backupPath);
            result.checks.archiveIntegrity = isValid;
            
            if (!isValid) {
                result.errors.push('Archivo ZIP corrupto o dañado');
            }
            
            // Test de extracción parcial
            const canExtract = await this.testZipExtraction(backupPath);
            result.checks.extractable = canExtract;
            
        } catch (error) {
            result.errors.push(`Error validando ZIP: ${error.message}`);
            result.checks.archiveIntegrity = false;
        }
    }

    async testTarGzIntegrity(filePath) {
        return new Promise((resolve) => {
            const tar = spawn('tar', ['-tzf', filePath]);
            let hasError = false;
            
            tar.stderr.on('data', () => { hasError = true; });
            tar.on('close', (code) => resolve(code === 0 && !hasError));
            tar.on('error', () => resolve(false));
        });
    }

    async getTarGzFileList(filePath) {
        return new Promise((resolve, reject) => {
            const tar = spawn('tar', ['-tzf', filePath]);
            let output = '';
            
            tar.stdout.on('data', (data) => { output += data; });
            tar.on('close', (code) => {
                if (code === 0) {
                    resolve(output.split('\n').filter(line => line.trim()));
                } else {
                    reject(new Error('Error listando archivos tar.gz'));
                }
            });
            tar.on('error', reject);
        });
    }

    async testZipIntegrity(filePath) {
        return new Promise((resolve) => {
            const unzip = spawn('unzip', ['-t', filePath]);
            let hasError = false;
            
            unzip.stderr.on('data', () => { hasError = true; });
            unzip.on('close', (code) => resolve(code === 0 && !hasError));
            unzip.on('error', () => resolve(false));
        });
    }

    async testZipExtraction(filePath) {
        return new Promise((resolve) => {
            const unzip = spawn('unzip', ['-l', filePath]);
            let hasError = false;
            
            unzip.stderr.on('data', () => { hasError = true; });
            unzip.on('close', (code) => resolve(code === 0 && !hasError));
            unzip.on('error', () => resolve(false));
        });
    }

    async validateChecksum(backupPath, result) {
        const checksumPath = `${backupPath}.sha256`;
        
        try {
            await fs.access(checksumPath);
            const expectedChecksum = (await fs.readFile(checksumPath, 'utf8')).trim();
            const actualChecksum = await this.calculateChecksum(backupPath);
            
            result.checks.checksumMatch = expectedChecksum === actualChecksum;
            result.metadata.checksum = actualChecksum;
            
            if (!result.checks.checksumMatch) {
                result.errors.push('Checksum no coincide - posible corrupción');
            }
            
        } catch (error) {
            result.warnings.push('Archivo de checksum no encontrado');
            result.checks.checksumMatch = null;
        }
    }

    async calculateChecksum(filePath) {
        const hash = crypto.createHash('sha256');
        const stream = require('fs').createReadStream(filePath);
        
        return new Promise((resolve, reject) => {
            stream.on('data', (data) => hash.update(data));
            stream.on('end', () => resolve(hash.digest('hex')));
            stream.on('error', reject);
        });
    }

    validateBackupAge(result) {
        const age = Date.now() - result.metadata.created.getTime();
        const ageInDays = age / (1000 * 60 * 60 * 24);
        
        result.metadata.ageInDays = ageInDays;
        
        if (ageInDays > 7) {
            result.warnings.push(`Backup antiguo: ${Math.round(ageInDays)} días`);
        }
        
        if (ageInDays > 30) {
            result.errors.push('Backup demasiado antiguo (>30 días)');
            result.checks.ageCheck = false;
        } else {
            result.checks.ageCheck = true;
        }
    }

    async generateValidationReport(results) {
        const reportPath = path.join(process.cwd(), 'backup-validation-report.json');
        
        const report = {
            ...results,
            generatedAt: new Date().toISOString(),
            summary: {
                successRate: ((results.validBackups / results.totalBackups) * 100).toFixed(2) + '%',
                criticalIssues: this.criticalFailures.length,
                recommendedActions: this.getRecommendedActions(results)
            }
        };
        
        await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
        console.log(`📋 Reporte de validación guardado: ${reportPath}`);
        
        return report;
    }

    getRecommendedActions(results) {
        const actions = [];
        
        if (results.failedBackups > 0) {
            actions.push('Regenerar backups fallidos');
        }
        
        if (this.criticalFailures.length > 0) {
            actions.push('Revisar configuración de rutas de backup');
        }
        
        const oldBackups = results.details.filter(d => d.metadata.ageInDays > 7).length;
        if (oldBackups > 0) {
            actions.push('Ejecutar nuevos backups para reemplazar los antiguos');
        }
        
        return actions;
    }

    async scheduleValidation() {
        const schedule = require('node-cron');
        
        // Validación diaria a las 4:00 AM
        schedule.schedule('0 4 * * *', async () => {
            console.log('🕐 Iniciando validación programada de backups');
            await this.validateAllBackups();
        });
        
        console.log('📅 Validación programada de backups activada');
    }
}

module.exports = BackupValidator;
Script de Validación Independiente
#!/bin/bash
# validate-backups.sh - Script de validación de backups

LOG_FILE="/var/log/backup-validation.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Iniciando validación de backups..."

# Ejecutar validación
node /path/to/backup-validator.js

if [ $? -eq 0 ]; then
    log "✅ Validación completada exitosamente"
else
    log "❌ Error en validación de backups"
    exit 1
fi

# Verificar si hay backups críticos fallidos
if [ -f "backup-validation-report.json" ]; then
    CRITICAL_FAILURES=$(jq '.criticalFailures' backup-validation-report.json)
    if [ "$CRITICAL_FAILURES" -gt 0 ]; then
        log "🚨 ALERTA: $CRITICAL_FAILURES backups críticos fallidos"
        # Enviar notificación (implementar según necesidad)
    fi
fi

log "Validación de backups finalizada"
Configuración y Uso
// Uso del validador
const BackupValidator = require('./backup-validator');

const validator = new BackupValidator();

// Validación manual
async function runValidation() {
    const results = await validator.validateAllBackups();
    
    if (results.criticalFailures > 0) {
        console.error('🚨 Backups críticos fallidos detectados');
        process.exit(1);
    }
    
    console.log(`📊 Tasa de éxito: ${results.summary.successRate}`);
}

// Iniciar validación programada
validator.scheduleValidation();

// Ejecutar validación
runValidation().catch(console.error);
