Guía de Despliegue en Producción - Node.js y Express
Sección 3: Monitoreo, Logging y Performance
3.1 Configuración de registros del sistema
3.1.1 Instalación y configuración de Winston
Winston es la librería de logging más popular para Node.js. Proporciona un sistema robusto y flexible para registrar eventos de la aplicación.
Instalación:
bashnpm install winston winston-daily-rotate-file
Configuración básica de Winston:
javascript// config/logger.js
const winston = require('winston');
const DailyRotateFile = require('winston-daily-rotate-file');
const path = require('path');

// Definir niveles de log personalizados
const levels = {
  error: 0,
  warn: 1,
  info: 2,
  http: 3,
  debug: 4,
};

// Definir colores para cada nivel
const colors = {
  error: 'red',
  warn: 'yellow',
  info: 'green',
  http: 'magenta',
  debug: 'white',
};

winston.addColors(colors);

// Formato personalizado para logs
const format = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss:ms' }),
  winston.format.colorize({ all: true }),
  winston.format.printf(
    (info) => `${info.timestamp} ${info.level}: ${info.message}`,
  ),
);

// Configuración de transports
const transports = [
  // Console transport para desarrollo
  new winston.transports.Console({
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.simple()
    )
  }),
  
  // File transport para errores
  new winston.transports.File({
    filename: 'logs/error.log',
    level: 'error',
    format: winston.format.combine(
      winston.format.timestamp(),
      winston.format.json()
    )
  }),
  
  // Daily rotate file para logs generales
  new DailyRotateFile({
    filename: 'logs/application-%DATE%.log',
    datePattern: 'YYYY-MM-DD',
    zippedArchive: true,
    maxSize: '20m',
    maxFiles: '14d',
    format: winston.format.combine(
      winston.format.timestamp(),
      winston.format.json()
    )
  })
];

// Crear logger
const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  levels,
  format,
  transports,
  exceptionHandlers: [
    new winston.transports.File({ filename: 'logs/exceptions.log' })
  ],
  rejectionHandlers: [
    new winston.transports.File({ filename: 'logs/rejections.log' })
  ]
});

// En producción, no logear a la consola
if (process.env.NODE_ENV === 'production') {
  logger.remove(winston.transports.Console);
}

module.exports = logger;
3.1.2 Configuración de Morgan para logs HTTP
Morgan es un middleware de logging HTTP para Express que registra todas las peticiones HTTP.
Instalación:
bashnpm install morgan
Configuración de Morgan:
javascript// middleware/morgan.js
const morgan = require('morgan');
const logger = require('../config/logger');

// Crear stream personalizado para Winston
const stream = {
  write: (message) => {
    logger.http(message.trim());
  }
};

// Función para omitir logs en ciertos casos
const skip = (req, res) => {
  const env = process.env.NODE_ENV || 'development';
  // En producción, solo registrar errores
  return env === 'production' && res.statusCode < 400;
};

// Configurar morgan
const morganMiddleware = morgan(
  // Formato personalizado
  ':method :url :status :res[content-length] - :response-time ms',
  {
    stream,
    skip
  }
);

module.exports = morganMiddleware;
3.1.3 Niveles de registro y mejores prácticas
Niveles de registro estándar:
javascript// utils/logLevels.js
const LOG_LEVELS = {
  ERROR: 'error',    // Errores críticos que requieren atención inmediata
  WARN: 'warn',      // Advertencias que pueden indicar problemas
  INFO: 'info',      // Información general sobre el flujo de la aplicación
  HTTP: 'http',      // Requests HTTP
  DEBUG: 'debug'     // Información detallada para debugging
};

// Ejemplos de uso correcto
const logger = require('../config/logger');

// ERROR - Para errores críticos
logger.error('Database connection failed', { 
  error: err.message,
  stack: err.stack,
  timestamp: new Date().toISOString()
});

// WARN - Para situaciones que requieren atención
logger.warn('High memory usage detected', {
  memoryUsage: process.memoryUsage(),
  threshold: '80%'
});

// INFO - Para eventos importantes de la aplicación
logger.info('User logged in successfully', {
  userId: user.id,
  email: user.email,
  ip: req.ip
});

// DEBUG - Para información detallada de desarrollo
logger.debug('Processing payment', {
  paymentId: payment.id,
  amount: payment.amount,
  method: payment.method
});

module.exports = LOG_LEVELS;
3.1.4 Rotación de archivos de registro
Configuración avanzada de rotación:
javascript// config/logRotation.js
const DailyRotateFile = require('winston-daily-rotate-file');

const createRotateTransport = (filename, level = 'info') => {
  return new DailyRotateFile({
    filename: `logs/${filename}-%DATE%.log`,
    datePattern: 'YYYY-MM-DD-HH',
    zippedArchive: true,
    maxSize: '20m',
    maxFiles: '14d',
    level: level,
    format: winston.format.combine(
      winston.format.timestamp(),
      winston.format.json()
    )
  });
};

// Transports específicos por tipo
const transports = {
  error: createRotateTransport('error', 'error'),
  combined: createRotateTransport('combined'),
  access: createRotateTransport('access', 'http')
};

module.exports = transports;
3.1.5 Integración con Express
Implementación en la aplicación Express:
javascript// app.js
const express = require('express');
const logger = require('./config/logger');
const morganMiddleware = require('./middleware/morgan');

const app = express();

// Middleware de logging HTTP
app.use(morganMiddleware);

// Middleware para logging de errores
app.use((err, req, res, next) => {
  logger.error('Unhandled error', {
    error: err.message,
    stack: err.stack,
    url: req.url,
    method: req.method,
    ip: req.ip,
    userAgent: req.get('user-agent')
  });
  
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'production' ? 'Something went wrong' : err.message
  });
});

// Logging de inicio de aplicación
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  logger.info(`Server started successfully`, {
    port: PORT,
    environment: process.env.NODE_ENV,
    timestamp: new Date().toISOString()
  });
});

module.exports = app;
3.1.6 Variables de entorno para logging
Configuración de variables de entorno:
bash# .env
# Configuración de logging
LOG_LEVEL=info
LOG_FORMAT=json
LOG_FILE_MAX_SIZE=20m
LOG_FILE_MAX_FILES=14d
LOG_DIRECTORY=logs

# En producción
NODE_ENV=production
LOG_LEVEL=warn
ENABLE_CONSOLE_LOG=false
3.1.7 Estructura de directorios de logs
proyecto/
├── logs/
│   ├── application-2025-06-14.log
│   ├── error.log
│   ├── exceptions.log
│   ├── rejections.log
│   └── access-2025-06-14.log
├── config/
│   ├── logger.js
│   └── logRotation.js
└── middleware/
    └── morgan.js
3.1.8 Mejores prácticas de logging
Recomendaciones importantes:

Información sensible: Nunca registrar contraseñas, tokens o datos sensibles
Formato consistente: Usar formato JSON para facilitar el análisis
Contexto relevante: Incluir información útil como IDs de usuario, timestamps
Niveles apropiados: Usar el nivel correcto para cada tipo de evento
Rotación regular: Configurar rotación para evitar archivos muy grandes
Monitoreo: Implementar alertas para logs de error críticos

Ejemplo de log estructurado:
javascript// Ejemplo de logging correcto
logger.info('User action completed', {
  action: 'update_profile',
  userId: user.id,
  changes: ['email', 'name'],
  duration: Date.now() - startTime,
  success: true,
  timestamp: new Date().toISOString()
});

⚠️ Importante:

Asegúrate de crear el directorio logs/ antes de ejecutar la aplicación
Configura logrotate en sistemas Linux para gestión adicional de archivos
Nunca incluyas archivos de log en el control de versiones (añadir a .gitignore)


Esta es la Subsección 3.1 de la Guía de Despliegue en Producción. Continúa con la Subsección 3.2 para el monitoreo de la aplicación.
