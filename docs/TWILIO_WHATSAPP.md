# Configuración de Twilio WhatsApp Business API

Esta guía te ayudará a configurar Twilio WhatsApp para recibir y enviar mensajes con facturas.

## Tabla de Contenidos

- [Crear Cuenta en Twilio](#crear-cuenta-en-twilio)
- [WhatsApp Sandbox (Desarrollo)](#whatsapp-sandbox-desarrollo)
- [Configurar Webhook](#configurar-webhook)
- [Obtener Credenciales](#obtener-credenciales)
- [WhatsApp Business API (Producción)](#whatsapp-business-api-producción)
- [Pruebas](#pruebas)
- [Troubleshooting](#troubleshooting)

## Crear Cuenta en Twilio

### 1. Registrarse en Twilio

1. Ir a: https://www.twilio.com/try-twilio
2. Llenar formulario de registro
3. Verificar email y teléfono
4. Completar cuestionario inicial

### 2. Crédito Inicial

Twilio ofrece **$15 USD de crédito gratuito** para nuevas cuentas.

**Costos de WhatsApp:**
- **Mensajes entrantes**: GRATIS
- **Mensajes salientes**: ~$0.005 USD por mensaje
- Suficiente para ~3,000 mensajes con el crédito gratuito

## WhatsApp Sandbox (Desarrollo)

El Sandbox permite probar WhatsApp sin aprobación de Meta/WhatsApp (ideal para desarrollo).

### 1. Activar WhatsApp Sandbox

1. Ir a: https://console.twilio.com/
2. En el menú lateral: **Messaging** → **Try it out** → **Send a WhatsApp message**
3. O directamente: https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn

### 2. Conectar tu Número WhatsApp

Verás un código de activación como: `join <código-aleatorio>`

**Pasos:**
1. Agregar el número de Twilio a tus contactos WhatsApp:
   - **+1 415 523 8886** (número del Sandbox)
2. Enviar mensaje WhatsApp con el código:
   ```
   join <tu-código-aquí>
   ```
   Ejemplo: `join happy-tiger`
3. Recibirás confirmación: "You are all set!"

### 3. Número del Sandbox

El número del Sandbox de Twilio es:
```
whatsapp:+14155238886
```

Este es el número que usarás en la configuración.

## Configurar Webhook

El webhook es la URL donde Twilio enviará los mensajes recibidos.

### 1. Exponer tu Aplicación Local (Desarrollo)

Para desarrollo local, necesitas exponer tu puerto 8000:

#### Opción A: ngrok (Recomendado)

```bash
# Instalar ngrok
# macOS:
brew install ngrok

# Linux:
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# Ejecutar ngrok
ngrok http 8000
```

Copiar la URL HTTPS generada (ej: `https://abc123.ngrok.io`)

#### Opción B: localtunnel

```bash
npm install -g localtunnel
lt --port 8000
```

### 2. Configurar Webhook en Twilio

1. Ir a: https://console.twilio.com/us1/develop/sms/settings/whatsapp-sandbox
2. En "When a message comes in":
   - **URL**: `https://tu-url.ngrok.io/webhook/whatsapp`
   - **HTTP Method**: `POST`
3. Click en "Save"

**Importante:** Debe ser HTTPS (no HTTP)

### 3. Verificar Webhook

Envía un mensaje de WhatsApp al número del Sandbox. 

En los logs de tu aplicación deberías ver:
```
Received WhatsApp message from whatsapp:+1234567890
```

## Obtener Credenciales

### 1. Account SID y Auth Token

1. Ir a: https://console.twilio.com/
2. En el Dashboard verás:
   - **Account SID**: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Auth Token**: Click en "Show" para ver

### 2. Configurar en .env

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=tu_auth_token_aquí
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
TWILIO_WEBHOOK_URL=https://tu-dominio.com/webhook/whatsapp
```

**⚠️ Importante:** Nunca compartas tu Auth Token públicamente.

## WhatsApp Business API (Producción)

Para producción, necesitas un número WhatsApp Business aprobado.

### 1. Requisitos

- Cuenta de Twilio verificada y con facturación activa
- Cuenta de Meta Business
- Proceso de aprobación de Meta/WhatsApp

### 2. Solicitar Número WhatsApp

1. En Twilio Console: **Messaging** → **Senders** → **WhatsApp senders**
2. Click en "Request to add business profile"
3. Completar información de tu negocio:
   - Nombre del negocio
   - Dirección
   - Descripción
   - Categoría
4. Enviar para aprobación

### 3. Tiempo de Aprobación

- **Sandbox**: Instantáneo
- **Producción**: 1-5 días hábiles

### 4. Costos de Producción

| Región | Mensaje entrante | Mensaje saliente |
|--------|-----------------|------------------|
| República Dominicana | GRATIS | $0.0045 USD |
| Estados Unidos | GRATIS | $0.005 USD |
| Otros países | GRATIS | $0.003-$0.01 USD |

### 5. Configurar Número de Producción

Una vez aprobado:

1. Ir a: **Messaging** → **Senders** → **WhatsApp senders**
2. Click en tu número aprobado
3. Configurar webhook URL: `https://tu-dominio.com/webhook/whatsapp`
4. Actualizar `.env`:
   ```env
   TWILIO_WHATSAPP_NUMBER=whatsapp:+1234567890  # Tu número aprobado
   ```

## Pruebas

### 1. Probar Recepción de Mensajes

```bash
# Iniciar aplicación
python -m app.main

# En WhatsApp, enviar mensaje de texto al Sandbox
```

Deberías recibir respuesta:
```
Por favor envía una foto de la factura. 📸
```

### 2. Probar Envío de Factura

1. Tomar foto de una factura NCF
2. Enviar por WhatsApp al número del Sandbox
3. Esperar respuesta:
   ```
   ✅ Factura recibida, procesando...
   ```
4. Luego recibirás resultado:
   ```
   ✅ Factura NCF: B0100000123 - Monto: RD$1,500.00 - Procesada correctamente
   ```

### 3. Verificar en Twilio Logs

1. Ir a: https://console.twilio.com/us1/monitor/logs/messages
2. Ver mensajes entrantes y salientes
3. Verificar estado de entrega

### 4. Script de Prueba Manual

```python
from twilio.rest import Client

# Configurar credenciales
account_sid = 'tu_account_sid'
auth_token = 'tu_auth_token'
client = Client(account_sid, auth_token)

# Enviar mensaje de prueba
message = client.messages.create(
    from_='whatsapp:+14155238886',
    to='whatsapp:+18091234567',  # Tu número
    body='✅ Prueba de envío desde LECTOR-NCF'
)

print(f"Mensaje enviado: {message.sid}")
```

## Configuración Avanzada

### 1. Plantillas de Mensajes Aprobadas

Para producción, Meta requiere plantillas aprobadas.

**Crear Plantilla:**
1. Ir a: **Messaging** → **Content Editor** → **Create**
2. Nombre: `invoice_processed`
3. Contenido: 
   ```
   ✅ Factura NCF: {{1}} - Monto: RD${{2}} - Procesada correctamente
   ```
4. Enviar para aprobación

### 2. Rate Limiting

Implementar límites para evitar spam:

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/webhook/whatsapp", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def whatsapp_webhook(...):
    # Tu código
```

### 3. Múltiples Webhooks

Puedes configurar diferentes webhooks para diferentes eventos:

- **When a message comes in**: Mensajes entrantes
- **When a status changes**: Estado de entrega
- **When a media message comes in**: Solo media

## Troubleshooting

### Error: "Invalid webhook URL"

**Solución:**
- URL debe ser HTTPS (no HTTP)
- URL debe ser accesible públicamente
- Verificar que la aplicación está corriendo

### Error: "Unauthorized"

**Solución:**
```bash
# Verificar credenciales en .env
echo $TWILIO_ACCOUNT_SID
echo $TWILIO_AUTH_TOKEN

# Regenerar Auth Token si es necesario
# En Twilio Console → Settings → API Keys
```

### No recibo mensajes en el webhook

**Solución:**
1. Verificar logs de ngrok: `ngrok http 8000 --log=stdout`
2. Verificar que la URL del webhook está correcta en Twilio
3. Verificar logs de aplicación: `tail -f logs/app.log`
4. Probar manualmente con curl:
   ```bash
   curl -X POST https://tu-url.ngrok.io/webhook/whatsapp \
     -d "From=whatsapp:+1234567890" \
     -d "To=whatsapp:+14155238886" \
     -d "MessageSid=SM123" \
     -d "NumMedia=0" \
     -d "Body=Hola"
   ```

### Mensajes no se envían

**Solución:**
1. Verificar que el número está activo en Sandbox
2. Verificar crédito de Twilio
3. Verificar logs en: https://console.twilio.com/us1/monitor/logs/errors

### Error: "Join code expired"

**Solución:**
- El código del Sandbox cambia periódicamente
- Enviar nuevo mensaje `join <nuevo-código>`

## Monitoreo y Costos

### Ver Uso

1. Ir a: https://console.twilio.com/us1/billing/usage
2. Filtrar por "WhatsApp"
3. Ver mensajes enviados/recibidos

### Configurar Alertas

1. Ir a: **Billing** → **Usage triggers**
2. Crear alerta (ej: $5 USD)
3. Agregar email para notificaciones

### Optimizar Costos

- Mensajes entrantes son GRATIS
- Reducir mensajes salientes innecesarios
- Usar plantillas para mensajes frecuentes
- Implementar caché para evitar duplicados

## Recursos Adicionales

- [Twilio WhatsApp Quickstart](https://www.twilio.com/docs/whatsapp/quickstart)
- [WhatsApp API Reference](https://www.twilio.com/docs/whatsapp/api)
- [Pricing WhatsApp](https://www.twilio.com/whatsapp/pricing)
- [Best Practices](https://www.twilio.com/docs/whatsapp/tutorial/connect-number-business-profile)

## Siguiente Paso

Continuar con: [Integración con Firebase](FIREBASE.md) (opcional)
