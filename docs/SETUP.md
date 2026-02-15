# Guía de Configuración e Instalación - LECTOR-NCF

Esta guía proporciona instrucciones detalladas para instalar y configurar el sistema LECTOR-NCF.

## Tabla de Contenidos

- [Requisitos del Sistema](#requisitos-del-sistema)
- [Instalación Local](#instalación-local)
- [Configuración de Variables de Entorno](#configuración-de-variables-de-entorno)
- [Configuración de Servicios Externos](#configuración-de-servicios-externos)
- [Deployment en Producción](#deployment-en-producción)
- [Troubleshooting](#troubleshooting)

## Requisitos del Sistema

### Software Requerido

- **Python**: 3.11 o superior
- **pip**: Gestor de paquetes de Python
- **Git**: Para clonar el repositorio
- **Docker** (opcional): Para deployment containerizado

### Cuentas de Servicios Externos

- **Google Cloud Platform**: Para Vision API (OCR)
- **Twilio**: Para WhatsApp Business API
- **Firebase** (opcional): Para almacenamiento en la nube

## Instalación Local

### 1. Clonar el Repositorio

```bash
git clone https://github.com/zoeccivil/LECTOR-NCF.git
cd LECTOR-NCF
```

### 2. Crear Entorno Virtual

**En Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**En Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Crear Estructura de Directorios

Los directorios se crean automáticamente, pero puedes verificar:

```bash
mkdir -p data/exports data/temp data/processed logs credentials
```

## Configuración de Variables de Entorno

### 1. Copiar Archivo de Ejemplo

```bash
cp .env.example .env
```

### 2. Editar Variables de Entorno

Abrir `.env` y configurar las siguientes variables:

#### Google Cloud Vision

```env
GOOGLE_APPLICATION_CREDENTIALS=credentials/google-cloud-vision.json
GOOGLE_CLOUD_PROJECT_ID=tu-proyecto-id
```

Ver [GOOGLE_CLOUD.md](GOOGLE_CLOUD.md) para obtener estas credenciales.

#### Twilio WhatsApp

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=tu_auth_token_secreto
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
TWILIO_WEBHOOK_URL=https://tu-dominio.com/webhook/whatsapp
```

Ver [TWILIO_WHATSAPP.md](TWILIO_WHATSAPP.md) para configurar Twilio.

#### Configuración de Exportación

```env
EXPORT_FORMAT=both  # csv, json, o both
CSV_DELIMITER=,
TIMEZONE=America/Santo_Domingo
```

#### Configuración de Aplicación

```env
DEBUG=False
LOG_LEVEL=INFO
MAX_IMAGE_SIZE_MB=10
HOST=0.0.0.0
PORT=8000
```

## Configuración de Servicios Externos

### Google Cloud Vision API

1. Ver guía completa: [GOOGLE_CLOUD.md](GOOGLE_CLOUD.md)
2. Descargar archivo JSON de credenciales
3. Guardar en `credentials/google-cloud-vision.json`

### Twilio WhatsApp

1. Ver guía completa: [TWILIO_WHATSAPP.md](TWILIO_WHATSAPP.md)
2. Obtener Account SID y Auth Token
3. Configurar webhook URL
4. Activar WhatsApp Sandbox (desarrollo) o número de producción

### Firebase (Opcional)

1. Ver guía completa: [FIREBASE.md](FIREBASE.md)
2. Descargar credenciales
3. Configurar en `.env`

## Deployment en Producción

### Opción 1: Servidor VPS (DigitalOcean, Linode, etc.)

#### 1. Preparar el Servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python y dependencias
sudo apt install python3.11 python3.11-venv python3-pip git nginx -y
```

#### 2. Clonar y Configurar

```bash
cd /var/www
sudo git clone https://github.com/zoeccivil/LECTOR-NCF.git
cd LECTOR-NCF
sudo chown -R $USER:$USER .
```

#### 3. Configurar Servicio Systemd

Crear archivo `/etc/systemd/system/lector-ncf.service`:

```ini
[Unit]
Description=LECTOR-NCF FastAPI Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/LECTOR-NCF
Environment="PATH=/var/www/LECTOR-NCF/venv/bin"
ExecStart=/var/www/LECTOR-NCF/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 4. Iniciar Servicio

```bash
sudo systemctl daemon-reload
sudo systemctl start lector-ncf
sudo systemctl enable lector-ncf
sudo systemctl status lector-ncf
```

#### 5. Configurar Nginx como Reverse Proxy

Crear `/etc/nginx/sites-available/lector-ncf`:

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/lector-ncf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 6. Configurar SSL con Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d tu-dominio.com
```

### Opción 2: Docker

#### 1. Construir Imagen

```bash
docker build -t lector-ncf:latest .
```

#### 2. Ejecutar con Docker Compose

```bash
docker-compose up -d
```

#### 3. Ver Logs

```bash
docker-compose logs -f
```

### Opción 3: Heroku

#### 1. Crear `Procfile`

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

#### 2. Deploy

```bash
heroku create lector-ncf
heroku config:set GOOGLE_APPLICATION_CREDENTIALS=credentials/google-cloud-vision.json
git push heroku main
```

### Opción 4: Railway

1. Conectar repositorio GitHub
2. Configurar variables de entorno
3. Deploy automático

## Verificación de Instalación

### 1. Verificar que la Aplicación está Corriendo

```bash
curl http://localhost:8000/
```

Respuesta esperada:
```json
{
  "status": "running",
  "service": "LECTOR-NCF",
  "version": "1.0.0"
}
```

### 2. Verificar Health Check

```bash
curl http://localhost:8000/health
```

### 3. Ejecutar Tests

```bash
pytest tests/ -v
```

## Troubleshooting

### Error: "Google Cloud credentials not found"

**Solución:**
1. Verificar que el archivo de credenciales existe
2. Verificar la ruta en `.env`
3. Verificar permisos del archivo

```bash
chmod 600 credentials/google-cloud-vision.json
```

### Error: "Twilio authentication failed"

**Solución:**
1. Verificar Account SID y Auth Token
2. Verificar que no hay espacios extra en `.env`
3. Regenerar Auth Token si es necesario

### Error: "Module not found"

**Solución:**
```bash
pip install -r requirements.txt --upgrade
```

### Error: "Permission denied" en directorios

**Solución:**
```bash
sudo chown -R $USER:$USER data/ logs/
chmod -R 755 data/ logs/
```

### La aplicación no recibe mensajes de WhatsApp

**Solución:**
1. Verificar que la URL del webhook es accesible públicamente
2. Verificar que el webhook está configurado en Twilio
3. Verificar logs: `tail -f logs/app.log`

### OCR no funciona correctamente

**Solución:**
1. Verificar que Vision API está habilitada en Google Cloud
2. Verificar cuota de API
3. Verificar facturación habilitada
4. Probar con imágenes de mejor calidad

## Mantenimiento

### Actualizar Aplicación

```bash
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart lector-ncf
```

### Limpiar Archivos Temporales

```bash
# Limpiar imágenes temporales antiguas (más de 7 días)
find data/temp -type f -mtime +7 -delete
```

### Backup de Datos

```bash
# Backup de exports
tar -czf backup_exports_$(date +%Y%m%d).tar.gz data/exports/

# Backup de processed
tar -czf backup_processed_$(date +%Y%m%d).tar.gz data/processed/
```

### Rotar Logs

Los logs se rotan automáticamente según configuración en `app/utils/logger.py`.

## Siguientes Pasos

1. [Configurar Google Cloud Vision](GOOGLE_CLOUD.md)
2. [Configurar Twilio WhatsApp](TWILIO_WHATSAPP.md)
3. [Integrar con Firebase](FIREBASE.md) (opcional)

## Soporte

Para problemas adicionales, abrir un issue en GitHub o contactar al equipo de desarrollo.
