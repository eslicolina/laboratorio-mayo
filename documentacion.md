# Documentación Técnica del Proyecto Smart-Gate

## Visión General
Sistema de control de acceso inteligente basado en visión artificial que utiliza reconocimiento facial con algoritmo LBPH (Local Binary Patterns Histograms) para identificar usuarios y detectar anomalías de acceso.

## Arquitectura del Sistema

### Componentes Principales
1. **app.py** - Aplicación Flask principal que expone la API y sirve la interfaz web
2. **smart_gate.py** - Lógica core del sistema de reconocimiento facial y detección de anomalías
3. **camera.py** - Manejo de la cámara web con patrón Singleton
4. **database.py** - Inicialización y configuración de la base de datos SQLite
5. **vision_engine.py** - Motor de visión (referenciado pero no mostrado en detalle)
6. **reconocedor.py** - Módulo de reconocimiento facial

### Tecnologías Utilizadas
- **Backend**: Python 3.x
- **Framework Web**: Flask
- **Visión Artificial**: OpenCV (cv2) con Haar Cascades y LBPH
- **Base de Datos**: SQLite3
- **Patrones de Diseño**: Singleton (para CameraStream y SmartGate)

## Detalles de Implementación

### SmartGate (smart_gate.py)
Clase principal que implementa:
- **Singleton Pattern**: Garantiza una única instancia del sistema
- **Reconocimiento Facial**: 
  - Detector Haar Cascades para localización de rostros
  - Reconocedor LBPH para identificación de usuarios
  - Umbral de confianza configurable (default: 70)
- **Detección de Anomalías**: 
  - Identifica "viajes impossibles" verificando ubicación vs. último registro
  - Tiempo límite de 15 segundos entre ubicaciones diferentes
- **Gestión de Eventos**:
  - Registro en base de datos SQLite
  - Sistema de cooldown para evitar registros excesivos
  - Captura de snapshots para eventos de desconocidos
- **Base de Datos**:
  - Tabla `eventos_acceso` con campos: id_evento, timestamp, usuario, ubicacion, confianza, tipo_evento, accion_tomada, snapshots
  - Índices en timestamp y usuario para optimización de consultas

### CameraStream (camera.py)
Implementa:
- **Singleton Thread-Safe**: Acceso seguro a la cámara desde múltiples hilos
- **OpenCV VideoCapture**: Interfaz con la cámara web (dispositivo 0)
- **Mecanismo de Bloqueo**: Lock para prevenir condiciones de carrera

### Aplicación Flask (app.py)
Endpoints principales:
- `/` - Interfaz web principal
- `/video_feed` - Streaming MJPEG del video procesado
- `/api/logs` - Últimos 10 eventos de acceso
- `/api/eventos` - Historial de eventos con paginación
- `/api/eventos/hoy` - Eventos de las últimas 24 horas
- `/api/estadisticas` - Estadísticas por tipo de evento y acción
- `/api/cooldown` - Configuración dinámica del tiempo de cooldown

## Flujo de Procesamiento

1. **Captura de Video**: La cámara captura frames continuamente
2. **Detección de Rostros**: Haar Cascades identifica regiones faciales en escala de grises
3. **Reconocimiento**: LBPH predice el ID del usuario y calcula confianza
4. **Toma de Decisiones**:
   - Si confianza > umbral → Usuario conocido
     - Verificar anomalía de ubicación → Posible denegación
   - Si confianza ≤ umbral → Usuario desconocido → Denegado automáticamente
5. **Registro de Eventos**:
   - Aplicar cooldown por usuario
   - Guardar en base de datos con timestamp
   - Para desconocidos: capturar múltiples snapshots
6. **Respuesta Visual**:
   - Dibujar rectángulo alrededor del rostro (verde: acceso, rojo: denegado)
   - Mostrar nombre de usuario y estado en pantalla

## Base de Datos

### Esquema
```sql
CREATE TABLE eventos_acceso (
    id_evento     INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     REAL    NOT NULL,
    usuario       TEXT,
    ubicacion     TEXT,
    confianza     REAL,
    tipo_evento   TEXT    NOT NULL DEFAULT 'acceso',
    accion_tomada TEXT,
    snapshots     TEXT    DEFAULT NULL
);

CREATE INDEX idx_timestamp ON eventos_acceso(timestamp);
CREATE INDEX idx_usuario ON eventos_acceso(usuario);
```

### Tipos de Eventos
- `acceso`: Entrada normal autorizada
- `anomalia`: Viaje imposible detectado
- `desconocido`: Usuario no reconocido

### Acciones Tomadas
- `permitido`: Acceso concedido
- `denegado`: Acceso denegado

## Configuración

### Parámetros Ajustables
- **umbral_confianza** (smart_gate.py:37): Umbral para reconocimiento válido (default: 70)
- **cooldown_segundos** (smart_gate.py:35): Tiempo mínimo entre registros del mismo usuario (default: 10.0)
- **ubicacion_actual** (smart_gate.py:36): Ubicación actual del sistema para detección de anomalías
- **usuarios** (smart_gate.py:33): Mapeo de IDs de entrenamiento a nombres reales

### Archivos Requeridos
- `haarcascade_frontalface_default.xml`: Detector de rostros Haar Cascades
- `trainer.yml`: Modelo entrenado LBPH
- `eventos_acceso.db`: Base de datos de eventos (generada automáticamente)
- `smart_gate.db`: Base de datos adicional (según documentación)
- Carpeta `snapshots/`: Almacenamiento de capturas de desconocidos

## API REST

### Endpoints Disponibles

#### GET /
- Devuelve la interfaz web principal (index.html)

#### GET /video_feed
- Stream MJPEG del video procesado en tiempo real
- Content-Type: multipart/x-mixed-replace; boundary=frame

#### GET /api/logs
- Parámetros: Ninguno
- Respuesta: Array de los 10 últimos eventos loggeados
- Campos: id, usuario, ubicacion, confianza, estado, fecha

#### GET /api/eventos
- Parámetros: `limite` (integer, default: 50)
- Respuesta: 
  ```json
  {
    "status": "ok",
    "timestamp": <unix_timestamp>,
    "data": [<evento>, ...]
  }
  ```
- Campos por evento: id_evento, timestamp, usuario, ubicacion, confianza, tipo_evento, accion_tomada, snapshots, fecha

#### GET /api/eventos/hoy
- Parámetros: Ninguno
- Respuesta: Eventos de las últimas 24 horas (mismo formato que /api/eventos)

#### GET /api/estadisticas
- Parámetros: Ninguno
- Respuesta:
  ```json
  {
    "status": "ok",
    "timestamp": <unix_timestamp>,
    "data": [
      {"tipo_evento": "...", "accion_tomada": "...", "total": <count>},
      ...
    ]
  }
  ```

#### POST /api/cooldown
- Parámetros: `{"segundos": <float>}` en body JSON
- Respuesta:
  ```json
  {
    "status": "ok",
    "timestamp": <unix_timestamp>,
    "data": {"cooldown_segundos": <float>}
  }
  ```
- Errores: 400 si faltan parámetros o segundos < 0

## Consideraciones de Rendimiento

### Optimizaciones Implementadas
1. **Índices de Base de Datos**: En timestamp y usuario para consultas rápidas
2. **Row Factory**: sqlite3.Row para acceso por nombre de columna
3. **Bloqueo de Cámaras**: Lock para prevenir condiciones de carrera en acceso a hardware
4. **Singleton Pattern**: Evita instanciación múltiple de recursos costosos
5. **Procesamiento Eficiente**: Solo procesa frames cuando hay rostros detectados

### Limitaciones Conocidas
1. **Dependencia de Iluminación**: El rendimiento de Haar Cascades y LBPH puede variar con condiciones de iluminación
2. **Precisión del Reconocedor**: Depende totalmente de la calidad del entrenamiento (trainer.yml)
3. **Recursos de Hardware**: Procesamiento continuo de video puede ser intensivo en CPU
4. **Almacenamiento de Snapshots**: Los snapshots de desconocidos pueden acumular espacio con el tiempo

## Seguridad y Privacidad

### Medidas de Seguridad
1. **Validación de Entrada**: Los endpoints API validan parámetros de entrada
2. **Manejo de Errores**: Excepciones capturadas en operaciones de base de datos y JSON
3. **Límites de Tasa**: Implementados mediante cooldown por usuario

### Consideraciones de Privacidad
1. **Almacenamiento Local**: Todos los datos (incluyendo snapshots) se almacenan localmente
2. **Datos Biométricos**: Solo se almacenan métricas de confianza, no plantillas faciales raw
3. **Retención de Datos**: No se implementa política automática de eliminación (debe gestionarse externamente)

## Próximos Pasos y Mejoras Sugeridas

1. **Interfaz de Administración**: Panel web para gestión de usuarios y visualización avanzada
2. **Exportación de Datos**: Funcionalidad para exportar reportes en CSV/JSON
3. **Integración con Sistemas Externos**: Webhooks o APIs para notificación de eventos
4. **Mejoras de Precisión**: 
   - Entrenamiento continuo con retroalimentación
   - Algoritmos de reconocimiento más avanzados (deep learning)
5. **Escalabilidad**:
   - Soporte para múltiples cámaras
   - Distribución de carga en sistemas de alta disponibilidad
6. **Monitoreo y Alertas**:
   - Notificaciones por email/SMS para eventos críticos
   - Dashboard de métricas en tiempo real

## Dependencias

### Paquetes de Python Requeridos
- Flask
- OpenCV-Python (cv2)
- SQLite3 (incluido en Python estándar)

### Archivos de Modelo
- `haarcascade_frontalface_default.xml`: Proveído por OpenCV
- `trainer.yml`: Generado mediante proceso de entrenamiento previo

## Conclusión

El proyecto Smart-Gate implementa un sistema completo de control de acceso basado en visión artificial con las siguientes características clave:
- Reconocimiento facial en tiempo real usando LBPH
- Detección inteligente de anomalías de acceso
- Interfaz web para monitoreo y visualización
- API REST para integración con otros sistemas
- Registro persistente de eventos con soporte para evidencia visual
- Diseño modular y mantenible con patrones de diseño apropiados

El sistema está listo para despliegue en entornos de control de acceso donde se requiera verificación de identidad y detección de comportamientos sospechosos.