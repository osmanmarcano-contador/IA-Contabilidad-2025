// services/performance-reporter.js
const fs = require('fs').promises;
const path = require('path');
const moment = require('moment');
const PDFDocument = require('pdfkit');
const nodemailer = require('nodemailer');

class PerformanceReporter {
    constructor() {
        this.reportConfig = {
            schedules: {
                daily: '0 6 * * *',     // 6:00 AM diario
                weekly: '0 8 * * 1',    // 8:00 AM lunes
                monthly: '0 9 1 * *'    // 9:00 AM primer día del mes
            },
            recipients: process.env.REPORT_RECIPIENTS?.split(',') || [],
            storage: {
                local: process.env.REPORTS_PATH || './reports',
                retention: parseInt(process.env.REPORT_RETENTION_DAYS) || 90
            }
        };
        this.initializeReporter();
    }

    async initializeReporter() {
        try {
            await fs.mkdir(this.reportConfig.storage.local, { recursive: true });
            console.log('📊 Performance Reporter inicializado correctamente');
        } catch (error) {
            console.error('❌ Error inicializando Performance Reporter:', error);
        }
    }

    async generateComprehensiveReport(period = 'daily', startDate = null, endDate = null) {
        const reportData = await this.collectReportData(period, startDate, endDate);
        const report = {
            metadata: this.generateReportMetadata(period, startDate, endDate),
            executive_summary: this.generateExecutiveSummary(reportData),
            performance_metrics: this.generatePerformanceMetrics(reportData),
            database_analysis: this.generateDatabaseAnalysis(reportData),
            security_insights: this.generateSecurityInsights(reportData),
            recommendations: this.generateRecommendations(reportData),
            appendices: this.generateAppendices(reportData)
        };

        return await this.renderReport(report);
    }

    async collectReportData(period, startDate, endDate) {
        const dateRange = this.calculateDateRange(period, startDate, endDate);
        
        return {
            application_metrics: await this.collectApplicationMetrics(dateRange),
            database_metrics: await this.collectDatabaseMetrics(dateRange),
            system_metrics: await this.collectSystemMetrics(dateRange),
            security_events: await this.collectSecurityEvents(dateRange),
            user_analytics: await this.collectUserAnalytics(dateRange),
            error_logs: await this.collectErrorAnalysis(dateRange)
        };
    }

    generateReportMetadata(period, startDate, endDate) {
        const dateRange = this.calculateDateRange(period, startDate, endDate);
        return {
            report_id: `PERF-${moment().format('YYYYMMDD-HHmmss')}`,
            period: period,
            date_range: {
                start: dateRange.start.format('YYYY-MM-DD HH:mm:ss'),
                end: dateRange.end.format('YYYY-MM-DD HH:mm:ss')
            },
            generated_at: moment().format('YYYY-MM-DD HH:mm:ss'),
            version: process.env.APP_VERSION || '1.0.0',
            environment: process.env.NODE_ENV || 'production'
        };
    }

    generateExecutiveSummary(data) {
        const avgResponseTime = this.calculateAverageResponseTime(data.application_metrics);
        const errorRate = this.calculateErrorRate(data.application_metrics);
        const uptime = this.calculateUptime(data.system_metrics);
        const performanceScore = this.calculatePerformanceScore(data);

        return {
            overall_health: this.determineOverallHealth(performanceScore),
            key_metrics: {
                performance_score: performanceScore,
                average_response_time: `${avgResponseTime.toFixed(2)}ms`,
                error_rate: `${errorRate.toFixed(2)}%`,
                uptime: `${uptime.toFixed(2)}%`,
                total_requests: data.application_metrics.total_requests || 0
            },
            critical_issues: this.identifyCriticalIssues(data),
            improvements_implemented: this.trackImprovements(data),
            next_actions: this.suggestNextActions(data)
        };
    }

    generatePerformanceMetrics(data) {
        return {
            response_times: {
                average: this.calculateAverageResponseTime(data.application_metrics),
                percentiles: this.calculateResponseTimePercentiles(data.application_metrics),
                trend_analysis: this.analyzeResponseTimeTrends(data.application_metrics)
            },
            throughput: {
                requests_per_second: this.calculateRPS(data.application_metrics),
                peak_load: this.identifyPeakLoad(data.application_metrics),
                load_distribution: this.analyzeLoadDistribution(data.application_metrics)
            },
            resource_utilization: {
                cpu: this.analyzeCPUUtilization(data.system_metrics),
                memory: this.analyzeMemoryUtilization(data.system_metrics),
                disk: this.analyzeDiskUtilization(data.system_metrics),
                network: this.analyzeNetworkUtilization(data.system_metrics)
            },
            error_analysis: {
                total_errors: data.error_logs.total_count || 0,
                error_categories: this.categorizeErrors(data.error_logs),
                critical_errors: this.identifyCriticalErrors(data.error_logs),
                error_trends: this.analyzeErrorTrends(data.error_logs)
            }
        };
    }

    generateDatabaseAnalysis(data) {
        return {
            query_performance: {
                slow_queries: this.identifySlowQueries(data.database_metrics),
                query_optimization_opportunities: this.identifyOptimizationOpportunities(data.database_metrics),
                index_effectiveness: this.analyzeIndexEffectiveness(data.database_metrics)
            },
            connection_management: {
                connection_pool_utilization: this.analyzeConnectionPool(data.database_metrics),
                connection_leaks: this.identifyConnectionLeaks(data.database_metrics),
                timeout_analysis: this.analyzeTimeouts(data.database_metrics)
            },
            data_growth: {
                table_sizes: this.analyzeTableSizes(data.database_metrics),
                growth_projections: this.projectDataGrowth(data.database_metrics),
                storage_recommendations: this.generateStorageRecommendations(data.database_metrics)
            }
        };
    }

    generateRecommendations(data) {
        const recommendations = [];

        // Análisis de rendimiento
        if (this.calculateAverageResponseTime(data.application_metrics) > 500) {
            recommendations.push({
                priority: 'HIGH',
                category: 'Performance',
                issue: 'Tiempo de respuesta elevado',
                recommendation: 'Implementar caché de aplicación y optimizar consultas database',
                estimated_impact: 'Reducción del 40-60% en tiempo de respuesta',
                implementation_effort: 'Medium'
            });
        }

        // Análisis de errores
        if (this.calculateErrorRate(data.application_metrics) > 1) {
            recommendations.push({
                priority: 'HIGH',
                category: 'Reliability',
                issue: 'Tasa de errores superior al umbral',
                recommendation: 'Revisar logs de errores y implementar mejor manejo de excepciones',
                estimated_impact: 'Mejora de la estabilidad del sistema',
                implementation_effort: 'High'
            });
        }

        // Análisis de recursos
        const cpuUtilization = this.getAverageCPUUtilization(data.system_metrics);
        if (cpuUtilization > 80) {
            recommendations.push({
                priority: 'MEDIUM',
                category: 'Infrastructure',
                issue: 'Alta utilización de CPU',
                recommendation: 'Considerar escalado horizontal o optimización de algoritmos',
                estimated_impact: 'Mejora en capacidad de procesamiento',
                implementation_effort: 'Medium'
            });
        }

        return {
            total_recommendations: recommendations.length,
            high_priority: recommendations.filter(r => r.priority === 'HIGH').length,
            recommendations: recommendations,
            implementation_roadmap: this.generateImplementationRoadmap(recommendations)
        };
    }

    async renderReport(reportData) {
        const formats = {
            html: await this.generateHTMLReport(reportData),
            pdf: await this.generatePDFReport(reportData),
            json: JSON.stringify(reportData, null, 2)
        };

        const reportPaths = await this.saveReports(formats, reportData.metadata);
        
        return {
            ...reportData,
            files: reportPaths,
            sharing_links: await this.generateSharingLinks(reportPaths)
        };
    }

    async generateHTMLReport(data) {
        return `
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Análisis de Rendimiento - ${data.metadata.report_id}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { text-align: center; border-bottom: 3px solid #007bff; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #007bff; margin: 0; font-size: 2.5em; }
        .header .metadata { color: #666; margin-top: 10px; }
        .section { margin-bottom: 40px; }
        .section h2 { color: #333; border-left: 4px solid #007bff; padding-left: 15px; }
        .executive-summary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 8px; }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
        .metric-card { background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745; }
        .metric-value { font-size: 2em; font-weight: bold; color: #28a745; }
        .recommendations { background: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107; }
        .recommendation-item { margin-bottom: 15px; padding: 15px; background: white; border-radius: 5px; }
        .priority-high { border-left: 4px solid #dc3545; }
        .priority-medium { border-left: 4px solid #ffc107; }
        .priority-low { border-left: 4px solid #28a745; }
        .chart-placeholder { height: 300px; background: #e9ecef; border-radius: 8px; display: flex; align-items: center; justify-content: center; margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; font-weight: 600; }
        .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Reporte de Análisis de Rendimiento</h1>
            <div class="metadata">
                <p><strong>ID:</strong> ${data.metadata.report_id} | <strong>Período:</strong> ${data.metadata.period} | <strong>Generado:</strong> ${data.metadata.generated_at}</p>
                <p><strong>Rango:</strong> ${data.metadata.date_range.start} - ${data.metadata.date_range.end}</p>
            </div>
        </div>

        <div class="section">
            <div class="executive-summary">
                <h2>🎯 Resumen Ejecutivo</h2>
                <div class="metrics-grid">
                    <div>
                        <div class="metric-value">${data.executive_summary.key_metrics.performance_score}/100</div>
                        <div>Puntuación de Rendimiento</div>
                    </div>
                    <div>
                        <div class="metric-value">${data.executive_summary.key_metrics.average_response_time}</div>
                        <div>Tiempo de Respuesta Promedio</div>
                    </div>
                    <div>
                        <div class="metric-value">${data.executive_summary.key_metrics.uptime}</div>
                        <div>Tiempo de Actividad</div>
                    </div>
                    <div>
                        <div class="metric-value">${data.executive_summary.key_metrics.error_rate}</div>
                        <div>Tasa de Errores</div>
                    </div>
                </div>
                <h3>Estado General: ${data.executive_summary.overall_health}</h3>
            </div>
        </div>

        <div class="section">
            <h2>⚡ Métricas de Rendimiento</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Tiempos de Respuesta</h3>
                    <div class="metric-value">${data.performance_metrics.response_times.average.toFixed(2)}ms</div>
                    <p>Promedio del período</p>
                </div>
                <div class="metric-card">
                    <h3>Throughput</h3>
                    <div class="metric-value">${data.performance_metrics.throughput.requests_per_second.toFixed(2)}</div>
                    <p>Solicitudes por segundo</p>
                </div>
                <div class="metric-card">
                    <h3>Utilización CPU</h3>
                    <div class="metric-value">${data.performance_metrics.resource_utilization.cpu.average.toFixed(1)}%</div>
                    <p>Promedio del período</p>
                </div>
                <div class="metric-card">
                    <h3>Utilización Memoria</h3>
                    <div class="metric-value">${data.performance_metrics.resource_utilization.memory.average.toFixed(1)}%</div>
                    <p>Promedio del período</p>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>🗄️ Análisis de Base de Datos</h2>
            <table>
                <thead>
                    <tr>
                        <th>Métrica</th>
                        <th>Valor</th>
                        <th>Estado</th>
                        <th>Recomendación</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Consultas Lentas</td>
                        <td>${data.database_analysis.query_performance.slow_queries.count}</td>
                        <td>${data.database_analysis.query_performance.slow_queries.count > 10 ? '⚠️ Atención' : '✅ Normal'}</td>
                        <td>${data.database_analysis.query_performance.slow_queries.count > 10 ? 'Optimizar consultas' : 'Mantener monitoreo'}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>🎯 Recomendaciones</h2>
            <div class="recommendations">
                <h3>Total de Recomendaciones: ${data.recommendations.total_recommendations}</h3>
                <p><strong>Alta Prioridad:</strong> ${data.recommendations.high_priority}</p>
                
                ${data.recommendations.recommendations.map(rec => `
                    <div class="recommendation-item priority-${rec.priority.toLowerCase()}">
                        <h4>${rec.category}: ${rec.issue}</h4>
                        <p><strong>Recomendación:</strong> ${rec.recommendation}</p>
                        <p><strong>Impacto Estimado:</strong> ${rec.estimated_impact}</p>
                        <p><strong>Esfuerzo:</strong> ${rec.implementation_effort}</p>
                    </div>
                `).join('')}
            </div>
        </div>

        <div class="footer">
            <p>Reporte generado automáticamente por el Sistema de Análisis de Rendimiento</p>
            <p>Versión ${data.metadata.version} | Ambiente: ${data.metadata.environment}</p>
        </div>
    </div>
</body>
</html>`;
    }

    // Métodos auxiliares para cálculos
    calculateAverageResponseTime(metrics) {
        return metrics.response_times?.reduce((sum, time) => sum + time, 0) / (metrics.response_times?.length || 1) || 0;
    }

    calculateErrorRate(metrics) {
        const totalRequests = metrics.total_requests || 1;
        const totalErrors = metrics.total_errors || 0;
        return (totalErrors / totalRequests) * 100;
    }

    calculateUptime(metrics) {
        return metrics.uptime_percentage || 99.9;
    }

    calculatePerformanceScore(data) {
        const responseScore = Math.max(0, 100 - (this.calculateAverageResponseTime(data.application_metrics) / 10));
        const errorScore = Math.max(0, 100 - (this.calculateErrorRate(data.application_metrics) * 10));
        const uptimeScore = this.calculateUptime(data.system_metrics);
        
        return Math.round((responseScore + errorScore + uptimeScore) / 3);
    }

    determineOverallHealth(score) {
        if (score >= 90) return '🟢 Excelente';
        if (score >= 75) return '🟡 Bueno';
        if (score >= 60) return '🟠 Atención';
        return '🔴 Crítico';
    }

    async scheduleAutomaticReports() {
        const cron = require('node-cron');
        
        // Reporte diario
        cron.schedule(this.reportConfig.schedules.daily, async () => {
            try {
                const report = await this.generateComprehensiveReport('daily');
                await this.distributeReport(report, 'daily');
            } catch (error) {
                console.error('Error generando reporte diario:', error);
            }
        });

        // Reporte semanal
        cron.schedule(this.reportConfig.schedules.weekly, async () => {
            try {
                const report = await this.generateComprehensiveReport('weekly');
                await this.distributeReport(report, 'weekly');
            } catch (error) {
                console.error('Error generando reporte semanal:', error);
            }
        });

        // Reporte mensual
        cron.schedule(this.reportConfig.schedules.monthly, async () => {
            try {
                const report = await this.generateComprehensiveReport('monthly');
                await this.distributeReport(report, 'monthly');
            } catch (error) {
                console.error('Error generando reporte mensual:', error);
            }
        });
    }

    async distributeReport(report, frequency) {
        // Envío por email
        if (this.reportConfig.recipients.length > 0) {
            await this.sendEmailReport(report, frequency);
        }

        // Notificación Slack (si está configurado)
        if (process.env.SLACK_WEBHOOK) {
            await this.sendSlackNotification(report, frequency);
        }

        // Archivo en sistema de archivos
        await this.archiveReport(report, frequency);
    }

    async sendEmailReport(report, frequency) {
        const transporter = nodemailer.createTransporter({
            host: process.env.SMTP_HOST,
            port: process.env.SMTP_PORT,
            secure: process.env.SMTP_SECURE === 'true',
            auth: {
                user: process.env.SMTP_USER,
                pass: process.env.SMTP_PASS
            }
        });

        const mailOptions = {
            from: process.env.REPORT_FROM_EMAIL,
            to: this.reportConfig.recipients.join(','),
            subject: `Reporte de Rendimiento ${frequency.toUpperCase()} - ${report.metadata.report_id}`,
            html: report.files.html,
            attachments: [
                {
                    filename: `reporte-rendimiento-${frequency}-${moment().format('YYYY-MM-DD')}.pdf`,
                    path: report.files.pdf
                }
            ]
        };

        await transporter.sendMail(mailOptions);
    }
}

module.exports = PerformanceReporter;
// app.js - Integración con la aplicación principal
const PerformanceReporter = require('./services/performance-reporter');

class App {
    constructor() {
        this.performanceReporter = new PerformanceReporter();
        this.initializeReporting();
    }

    async initializeReporting() {
        // Programar reportes automáticos
        await this.performanceReporter.scheduleAutomaticReports();
        
        // Configurar endpoint para reportes bajo demanda
        this.setupReportingEndpoints();
    }

    setupReportingEndpoints() {
        // Endpoint para generar reporte bajo demanda
        this.app.get('/api/reports/performance/:period', async (req, res) => {
            try {
                const { period } = req.params;
                const { start_date, end_date } = req.query;
                
                const report = await this.performanceReporter.generateComprehensiveReport(
                    period, 
                    start_date, 
                    end_date
                );
                
                res.json({
                    success: true,
                    report: report,
                    download_links: report.sharing_links
                });
            } catch (error) {
                res.status(500).json({
                    success: false,
                    error: 'Error generando reporte de rendimiento'
                });
            }
        });

        // Endpoint para listar reportes históricos
        this.app.get('/api/reports/history', async (req, res) => {
            try {
                const reports = await this.performanceReporter.listHistoricalReports();
                res.json({ success: true, reports });
            } catch (error) {
                res.status(500).json({
                    success: false,
                    error: 'Error listando reportes históricos'
                });
            }
        });
    }
}
# .env - Configuración de reportes
# Configuración de reportes
REPORTS_PATH=./reports
REPORT_RETENTION_DAYS=90
REPORT_RECIPIENTS=admin@empresa.com,ops@empresa.com

# Configuración SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=reports@empresa.com
SMTP_PASS=password_app

# Email de envío
REPORT_FROM_EMAIL=noreply@empresa.com

# Notificaciones Slack (opcional)
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
// scripts/init-reporting.js
const PerformanceReporter = require('../services/performance-reporter');

async function initializeReporting() {
    const reporter = new PerformanceReporter();
    
    console.log('🚀 Inicializando sistema de reportes...');
    
    // Generar reporte inicial
    const initialReport = await reporter.generateComprehensiveReport('daily');
    console.log('✅ Reporte inicial generado:', initialReport.metadata.report_id);
    
    // Programar reportes automáticos
    await reporter.scheduleAutomaticReports();
    console.log('⏰ Reportes automáticos programados');
    
    console.log('📊 Sistema de reportes listo!');
}

// Ejecutar si es llamado directamente
if (require.main === module) {
    initializeReporting().catch(console.error);
}

module.exports = initializeReporting;
