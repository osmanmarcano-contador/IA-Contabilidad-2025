# 📊 Guía de Visualización de Datos - IA en Contabilidad

**Objetivo:** Estándares para crear visualizaciones efectivas y profesionales

---

## 🎨 Paleta de Colores Corporativa

### Colores Principales
```css
/* Azul Corporativo */
#1f4e79 - Títulos principales
#2e75b6 - Gráficos principales
#5b9bd5 - Elementos secundarios

/* Grises */
#404040 - Texto principal
#757575 - Texto secundario
#d9d9d9 - Bordes y separadores

/* Colores de Estado */
#70ad47 - Éxito/Positivo (Verde)
#ffc000 - Advertencia (Amarillo)
#c5504b - Error/Negativo (Rojo)
Colores para Gráficos
Serie 1: #1f4e79, #2e75b6, #5b9bd5, #a5c8e4
Serie 2: #70ad47, #92c353, #b5d96b, #d9e7ca
Serie 3: #ffc000, #ffca28, #ffd451, #ffe184

📊 Tipos de Gráficos por Caso de Uso
1. Comparación de Valores
Usar: Gráficos de barras horizontales/verticales
Cuándo: Comparar categorías, mostrar rankings
Ejemplo: Ingresos por departamento, Performance vs objetivos
2. Evolución Temporal
Usar: Gráficos de líneas
Cuándo: Mostrar tendencias, cambios en el tiempo
Ejemplo: Ingresos mensuales, Evolución de KPIs
3. Composición/Partes del Todo
Usar: Gráficos de dona (no pie)
Cuándo: Mostrar porcentajes, distribuciones
Ejemplo: Distribución de gastos, Composición de ingresos
4. Correlación entre Variables
Usar: Gráficos de dispersión
Cuándo: Mostrar relaciones, patrones de correlación
Ejemplo: Relación precio-volumen, Análisis de rentabilidad
5. Distribución de Datos
Usar: Histogramas, box plots
Cuándo: Mostrar distribuciones, identificar outliers
Ejemplo: Distribución de transacciones, Análisis de riesgos

🎯 Mejores Prácticas
Títulos y Etiquetas

Título principal: Claro, específico, accionable
Subtítulo: Contexto adicional, período de datos
Ejes: Siempre etiquetados con unidades
Leyenda: Solo si es necesaria, posición consistente

Formateo de Números
Moneda: $1,234,567
Porcentajes: 45.2% (una decimal)
Miles: 1.2K, 1.2M, 1.2B
Fechas: Ene 2025, Q1 2025
Elementos Visuales

Gridlines: Sutiles, solo si ayudan
Bordes: Mínimos, enfoque en datos
Espaciado: Suficiente espacio en blanco
Fuente: Arial/Calibri, tamaños consistentes


📱 Plantillas por Tipo de Dashboard
1. Dashboard Ejecutivo
Características:

Máximo 6 KPIs principales
Gráficos simples y claros
Indicadores de semáforo (🟢🟡🔴)
Resumen en una página

Layout Sugerido:
[KPI 1] [KPI 2] [KPI 3]
[Gráfico Principal - 60%] [Métricas - 40%]
[Tendencia Temporal] [Comparación]
2. Dashboard Operativo
Características:

Más detalle técnico
Múltiples períodos de tiempo
Drill-down disponible
Actualización en tiempo real

Layout Sugerido:
[Filtros y Controles]
[Métricas Clave - Horizontal]
[Gráfico Principal Grande]
[Gráficos de Soporte - Grid 2x2]
3. Dashboard de Monitoreo
Características:

Alertas y notificaciones
Estados de sistema
Métricas de performance
Histórico de incidentes
