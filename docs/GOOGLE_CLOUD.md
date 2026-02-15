# Configuración de Google Cloud Vision API

Esta guía te ayudará a configurar Google Cloud Vision API para el procesamiento OCR de facturas.

## Tabla de Contenidos

- [Crear Proyecto en Google Cloud](#crear-proyecto-en-google-cloud)
- [Habilitar Vision API](#habilitar-vision-api)
- [Configurar Facturación](#configurar-facturación)
- [Crear Credenciales](#crear-credenciales)
- [Configurar en LECTOR-NCF](#configurar-en-lector-ncf)
- [Verificar Instalación](#verificar-instalación)
- [Límites y Costos](#límites-y-costos)

## Crear Proyecto en Google Cloud

### 1. Acceder a Google Cloud Console

Ir a: https://console.cloud.google.com/

### 2. Crear Nuevo Proyecto

1. Click en el selector de proyectos en la parte superior
2. Click en "Nuevo Proyecto"
3. Ingresar nombre: `lector-ncf` (o el que prefieras)
4. Seleccionar organización (si aplica)
5. Click en "Crear"

### 3. Seleccionar el Proyecto

Asegúrate de que el proyecto recién creado esté seleccionado en el selector de proyectos.

## Habilitar Vision API

### 1. Ir a la Biblioteca de APIs

- Menú (☰) → APIs y servicios → Biblioteca
- O directamente: https://console.cloud.google.com/apis/library

### 2. Buscar Vision API

1. En el buscador, escribir: "Cloud Vision API"
2. Click en "Cloud Vision API"
3. Click en "Habilitar"

Espera unos segundos mientras se habilita la API.

## Configurar Facturación

**Importante:** Google Cloud Vision requiere una cuenta de facturación, pero ofrece un nivel gratuito generoso.

### 1. Crear Cuenta de Facturación

1. Menú (☰) → Facturación
2. Click en "Vincular una cuenta de facturación"
3. Crear nueva cuenta de facturación o seleccionar una existente

### 2. Nivel Gratuito (Free Tier)

Google Cloud Vision ofrece:
- **1,000 unidades/mes GRATIS** para detección de texto
- Después de eso: $1.50 por 1,000 unidades

**Nota:** Para la mayoría de usuarios, el tier gratuito es suficiente.

## Crear Credenciales

### Opción 1: Service Account (Recomendado)

#### 1. Ir a Credenciales

- Menú (☰) → APIs y servicios → Credenciales
- O: https://console.cloud.google.com/apis/credentials

#### 2. Crear Service Account

1. Click en "Crear credenciales"
2. Seleccionar "Cuenta de servicio"
3. Ingresar detalles:
   - **Nombre**: `lector-ncf-service`
   - **ID**: `lector-ncf-service` (auto-generado)
   - **Descripción**: "Service account for LECTOR-NCF OCR processing"
4. Click en "Crear y continuar"

#### 3. Asignar Rol

1. En "Función", seleccionar: **Cloud Vision AI Service Agent**
2. Click en "Continuar"
3. Click en "Listo"

#### 4. Crear Clave JSON

1. En la lista de cuentas de servicio, click en la cuenta recién creada
2. Ir a la pestaña "Claves"
3. Click en "Agregar clave" → "Crear clave nueva"
4. Seleccionar tipo: **JSON**
5. Click en "Crear"

**¡Importante!** El archivo JSON se descargará automáticamente. Guárdalo de forma segura.

#### 5. Renombrar y Mover el Archivo

```bash
# Renombrar el archivo descargado
mv ~/Downloads/lector-ncf-*.json ./credentials/google-cloud-vision.json

# Verificar permisos
chmod 600 credentials/google-cloud-vision.json
```

### Opción 2: API Key (No Recomendado para Producción)

1. Click en "Crear credenciales" → "Clave de API"
2. Copiar la clave generada
3. **Restringir la clave** (Importante):
   - Click en "Restringir clave"
   - En "Restricciones de API", seleccionar "Restringir clave"
   - Seleccionar solo "Cloud Vision API"
   - Guardar

## Configurar en LECTOR-NCF

### 1. Copiar Credenciales al Proyecto

```bash
# Crear directorio de credenciales si no existe
mkdir -p credentials

# Copiar archivo de credenciales
cp /ruta/al/archivo/descargado.json credentials/google-cloud-vision.json
```

### 2. Configurar Variables de Entorno

Editar archivo `.env`:

```env
GOOGLE_APPLICATION_CREDENTIALS=credentials/google-cloud-vision.json
GOOGLE_CLOUD_PROJECT_ID=lector-ncf  # Tu project ID
```

**Obtener Project ID:**
```bash
# En Google Cloud Console
# Menú → IAM y administración → Configuración
# O usar gcloud CLI:
gcloud config get-value project
```

### 3. Verificar Permisos del Archivo

```bash
# El archivo debe ser legible solo por el usuario
chmod 600 credentials/google-cloud-vision.json

# Verificar
ls -la credentials/
```

## Verificar Instalación

### 1. Probar con Python

Crear archivo `test_vision.py`:

```python
import os
from google.cloud import vision

# Configurar credenciales
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials/google-cloud-vision.json'

# Crear cliente
client = vision.ImageAnnotatorClient()

print("✅ Google Cloud Vision client initialized successfully!")
print(f"Project ID: {os.environ.get('GOOGLE_CLOUD_PROJECT_ID')}")
```

Ejecutar:
```bash
python test_vision.py
```

### 2. Probar OCR con Imagen de Prueba

```python
from google.cloud import vision
import io

client = vision.ImageAnnotatorClient()

# Leer imagen
with io.open('test_invoice.jpg', 'rb') as image_file:
    content = image_file.read()

image = vision.Image(content=content)
response = client.text_detection(image=image)

if response.text_annotations:
    print("✅ OCR funcionando correctamente!")
    print(f"Texto detectado: {response.text_annotations[0].description[:100]}...")
else:
    print("⚠️ No se detectó texto en la imagen")
```

### 3. Verificar desde la Aplicación

```bash
# Iniciar aplicación
python -m app.main

# En otra terminal, verificar health
curl http://localhost:8000/health
```

Debería mostrar:
```json
{
  "status": "healthy",
  "services": {
    "ocr": true,
    "whatsapp": false
  }
}
```

## Límites y Costos

### Límites del Nivel Gratuito

- **1,000 unidades/mes** gratis
- 1 unidad = 1 imagen procesada
- Suficiente para ~33 facturas/día

### Costos Después del Nivel Gratuito

| Característica | Primeras 1,000 | Siguientes |
|---------------|----------------|------------|
| Text Detection | GRATIS | $1.50/1,000 |
| Document Text Detection | GRATIS | $1.50/1,000 |

**Ejemplo de Costos:**
- 100 facturas/día = 3,000/mes = **1,000 gratis + 2,000 × $1.50/1000 = $3.00/mes**
- 500 facturas/mes = **GRATIS**

### Monitorear Uso

1. Ir a: https://console.cloud.google.com/apis/dashboard
2. Seleccionar "Cloud Vision API"
3. Ver gráficas de uso y cuotas

### Configurar Alertas de Facturación

1. Menú → Facturación → Presupuestos y alertas
2. Click en "Crear presupuesto"
3. Configurar alerta (ej: $10/mes)
4. Agregar email para notificaciones

## Mejores Prácticas

### Seguridad

1. **Nunca** commitear el archivo JSON al repositorio
2. Agregar `*.json` al `.gitignore`
3. Usar variables de entorno en producción
4. Rotar credenciales regularmente

### Optimización de Costos

1. **Optimizar imágenes** antes de enviar (reduce tamaño)
2. **Cachear resultados** para evitar procesar duplicados
3. **Monitorear uso** mensualmente
4. **Implementar rate limiting** para prevenir abuso

### Rendimiento

1. Usar `document_text_detection` para facturas (mejor precisión)
2. Procesar imágenes de forma asíncrona
3. Implementar retry logic para errores temporales

## Troubleshooting

### Error: "Could not load credentials"

**Solución:**
```bash
# Verificar que el archivo existe
ls -la credentials/google-cloud-vision.json

# Verificar variable de entorno
echo $GOOGLE_APPLICATION_CREDENTIALS

# Verificar contenido del archivo (debe ser JSON válido)
cat credentials/google-cloud-vision.json | python -m json.tool
```

### Error: "Permission denied"

**Solución:**
```bash
# Dar permisos correctos
chmod 600 credentials/google-cloud-vision.json
```

### Error: "Vision API is not enabled"

**Solución:**
1. Ir a: https://console.cloud.google.com/apis/library/vision.googleapis.com
2. Click en "Habilitar"

### Error: "Quota exceeded"

**Solución:**
1. Verificar uso en: https://console.cloud.google.com/apis/dashboard
2. Esperar hasta próximo mes (free tier)
3. O habilitar facturación para continuar

### Error: "Invalid project ID"

**Solución:**
```bash
# Obtener project ID correcto
gcloud projects list

# Actualizar .env
GOOGLE_CLOUD_PROJECT_ID=tu-project-id-correcto
```

## Recursos Adicionales

- [Documentación oficial de Vision API](https://cloud.google.com/vision/docs)
- [Pricing Calculator](https://cloud.google.com/products/calculator)
- [Python Client Library](https://googleapis.dev/python/vision/latest/index.html)
- [Samples and Tutorials](https://cloud.google.com/vision/docs/samples)

## Siguiente Paso

Continuar con: [Configuración de Twilio WhatsApp](TWILIO_WHATSAPP.md)
