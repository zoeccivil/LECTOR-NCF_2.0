# Integración con Firebase

Esta guía te ayudará a integrar LECTOR-NCF con Firebase para almacenamiento en la nube y sincronización en tiempo real.

## Tabla de Contenidos

- [¿Por qué Firebase?](#por-qué-firebase)
- [Configuración Inicial](#configuración-inicial)
- [Firestore Database](#firestore-database)
- [Realtime Database](#realtime-database)
- [Estructura de Datos](#estructura-de-datos)
- [Implementación](#implementación)
- [Seguridad](#seguridad)

## ¿Por qué Firebase?

Firebase ofrece:

- ✅ **Firestore**: Base de datos NoSQL en tiempo real
- ✅ **Realtime Database**: Sincronización instantánea
- ✅ **Authentication**: Sistema de autenticación integrado
- ✅ **Storage**: Almacenamiento de imágenes
- ✅ **Free Tier**: Generoso para comenzar
- ✅ **Escalabilidad**: Crece con tu aplicación

## Configuración Inicial

### 1. Crear Proyecto Firebase

1. Ir a: https://console.firebase.google.com/
2. Click en "Crear un proyecto" (o "Add project")
3. Nombre del proyecto: `lector-ncf`
4. Habilitar Google Analytics (opcional)
5. Click en "Crear proyecto"

### 2. Habilitar Servicios

#### Firestore Database

1. En el menú lateral: **Build** → **Firestore Database**
2. Click en "Crear base de datos"
3. Modo de producción o prueba (recomendado: prueba para desarrollo)
4. Seleccionar región: `us-east1` o la más cercana
5. Click en "Habilitar"

#### Realtime Database (Alternativa)

1. En el menú lateral: **Build** → **Realtime Database**
2. Click en "Crear base de datos"
3. Seleccionar región
4. Modo de seguridad: "Modo de prueba" (para desarrollo)
5. Click en "Habilitar"

#### Storage (Para imágenes)

1. En el menú lateral: **Build** → **Storage**
2. Click en "Comenzar"
3. Configurar reglas de seguridad (modo prueba)
4. Seleccionar ubicación
5. Click en "Listo"

### 3. Obtener Credenciales

#### Service Account Key

1. Ir a: **Configuración del proyecto** (⚙️) → **Cuentas de servicio**
2. Click en "Generar nueva clave privada"
3. Formato: **JSON**
4. Click en "Generar clave"
5. Guardar archivo como `firebase-credentials.json`

#### Configuración Web (Opcional)

1. Ir a: **Configuración del proyecto** → **General**
2. En "Tus apps", click en el ícono web `</>`
3. Registrar app: `lector-ncf-web`
4. Copiar la configuración:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSy...",
  authDomain: "lector-ncf.firebaseapp.com",
  projectId: "lector-ncf",
  storageBucket: "lector-ncf.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abc123"
};
```

## Firestore Database

### Estructura de Colecciones

```
lector-ncf/
├── facturas/
│   ├── {invoice_id}/
│   │   ├── ncf: "B0100000123"
│   │   ├── rnc: "123456789"
│   │   ├── razon_social: "EMPRESA EJEMPLO SRL"
│   │   ├── fecha_emision: "2026-02-10"
│   │   ├── fecha_procesamiento: timestamp
│   │   ├── montos/
│   │   │   ├── subtotal: 1271.19
│   │   │   ├── itbis: 228.81
│   │   │   ├── total: 1500.00
│   │   │   └── moneda: "DOP"
│   │   └── metadata/
│   │       ├── imagen_url: "gs://..."
│   │       ├── confianza_ocr: 0.95
│   │       └── origen: "whatsapp"
├── proveedores/
│   └── {rnc}/
│       ├── razon_social: "..."
│       ├── rnc: "..."
│       └── total_facturas: 0
└── estadisticas/
    └── resumen/
        ├── total_facturas: 0
        ├── total_monto: 0
        └── ultima_actualizacion: timestamp
```

### Reglas de Seguridad Firestore

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Permitir lectura a usuarios autenticados
    match /facturas/{invoiceId} {
      allow read: if request.auth != null;
      allow create: if request.auth != null;
      allow update, delete: if request.auth != null && 
                              request.auth.token.admin == true;
    }
    
    match /proveedores/{rncId} {
      allow read: if request.auth != null;
      allow write: if request.auth != null;
    }
    
    match /estadisticas/{document=**} {
      allow read: if request.auth != null;
      allow write: if request.auth != null;
    }
  }
}
```

## Realtime Database

### Estructura de Datos

```json
{
  "facturas": {
    "uuid-1": {
      "ncf": "B0100000123",
      "rnc": "123456789",
      "razon_social": "EMPRESA EJEMPLO SRL",
      "fecha_emision": "2026-02-10",
      "fecha_procesamiento": 1707656400000,
      "montos": {
        "subtotal": 1271.19,
        "itbis": 228.81,
        "total": 1500.00,
        "moneda": "DOP"
      },
      "metadata": {
        "imagen_original": "factura_20260211_103000.jpg",
        "confianza_ocr": 0.95,
        "origen": "whatsapp"
      }
    }
  },
  "proveedores": {
    "123456789": {
      "razon_social": "EMPRESA EJEMPLO SRL",
      "rnc": "123456789",
      "total_facturas": 5,
      "monto_total": 7500.00
    }
  }
}
```

### Reglas de Seguridad Realtime Database

```json
{
  "rules": {
    "facturas": {
      ".read": "auth != null",
      "$invoiceId": {
        ".write": "auth != null"
      }
    },
    "proveedores": {
      ".read": "auth != null",
      ".write": "auth != null"
    },
    "estadisticas": {
      ".read": "auth != null",
      ".write": "auth != null"
    }
  }
}
```

## Implementación

### 1. Instalar Firebase Admin SDK

Ya está incluido en `requirements.txt`:
```
firebase-admin==6.3.0
```

### 2. Configurar Credenciales

Guardar archivo de credenciales:
```bash
mkdir -p credentials
mv ~/Downloads/firebase-credentials.json credentials/
chmod 600 credentials/firebase-credentials.json
```

Configurar `.env`:
```env
FIREBASE_CREDENTIALS=credentials/firebase-credentials.json
FIREBASE_DATABASE_URL=https://lector-ncf-default-rtdb.firebaseio.com
```

### 3. Crear Módulo Firebase

Crear `app/firebase_handler.py`:

```python
"""
Firebase integration handler
"""
import firebase_admin
from firebase_admin import credentials, firestore, db
from typing import Optional
from app.models import Invoice
from app.utils.logger import app_logger
from app.utils.config import settings


class FirebaseHandler:
    """Handles Firebase Firestore operations"""
    
    def __init__(self):
        """Initialize Firebase app"""
        try:
            if settings.firebase_credentials:
                cred = credentials.Certificate(settings.firebase_credentials)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': settings.firebase_database_url
                })
                self.db = firestore.client()
                app_logger.info("Firebase initialized successfully")
            else:
                self.db = None
                app_logger.warning("Firebase credentials not configured")
        except Exception as e:
            app_logger.error(f"Failed to initialize Firebase: {e}")
            self.db = None
    
    def save_invoice(self, invoice: Invoice) -> bool:
        """
        Save invoice to Firestore
        
        Args:
            invoice: Invoice object to save
            
        Returns:
            True if saved successfully
        """
        if not self.db:
            app_logger.warning("Firebase not initialized")
            return False
        
        try:
            # Prepare data
            invoice_data = {
                'ncf': invoice.ncf,
                'rnc': invoice.rnc,
                'razon_social': invoice.razon_social,
                'fecha_emision': invoice.fecha_emision,
                'fecha_procesamiento': invoice.fecha_procesamiento,
                'montos': {
                    'subtotal': invoice.montos.subtotal,
                    'itbis': invoice.montos.itbis,
                    'total': invoice.montos.total,
                    'moneda': invoice.montos.moneda
                },
                'metadata': {
                    'imagen_original': invoice.metadata.imagen_original,
                    'confianza_ocr': invoice.metadata.confianza_ocr,
                    'origen': invoice.metadata.origen
                }
            }
            
            # Save to Firestore
            doc_ref = self.db.collection('facturas').document(invoice.id)
            doc_ref.set(invoice_data)
            
            app_logger.info(f"Invoice saved to Firebase: {invoice.id}")
            
            # Update provider statistics
            if invoice.rnc:
                self._update_provider_stats(invoice.rnc, invoice.razon_social)
            
            return True
            
        except Exception as e:
            app_logger.error(f"Error saving to Firebase: {e}")
            return False
    
    def _update_provider_stats(self, rnc: str, razon_social: Optional[str]):
        """Update provider statistics"""
        try:
            provider_ref = self.db.collection('proveedores').document(rnc)
            provider_doc = provider_ref.get()
            
            if provider_doc.exists:
                # Increment counter
                provider_ref.update({
                    'total_facturas': firestore.Increment(1)
                })
            else:
                # Create new provider
                provider_ref.set({
                    'rnc': rnc,
                    'razon_social': razon_social or '',
                    'total_facturas': 1
                })
                
        except Exception as e:
            app_logger.error(f"Error updating provider stats: {e}")


# Global Firebase handler instance
firebase_handler = FirebaseHandler()
```

### 4. Integrar en main.py

Modificar `app/main.py` para guardar en Firebase:

```python
from app.firebase_handler import firebase_handler

# En el webhook, después de exportar:
try:
    # Save to Firebase
    firebase_handler.save_invoice(invoice)
except Exception as e:
    app_logger.error(f"Firebase save failed: {e}")
```

### 5. Storage para Imágenes (Opcional)

```python
from firebase_admin import storage

# Upload image to Storage
def upload_image(image_path: str, invoice_id: str) -> Optional[str]:
    """Upload image to Firebase Storage"""
    try:
        bucket = storage.bucket()
        blob = bucket.blob(f'facturas/{invoice_id}.jpg')
        blob.upload_from_filename(image_path)
        blob.make_public()
        
        return blob.public_url
    except Exception as e:
        app_logger.error(f"Error uploading to Storage: {e}")
        return None
```

## Seguridad

### 1. Autenticación

Para producción, implementar autenticación:

```python
from firebase_admin import auth

# Verify ID token
def verify_token(id_token: str):
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        return uid
    except Exception as e:
        return None
```

### 2. Reglas de Seguridad Estrictas

```javascript
// Firestore - Producción
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /facturas/{invoiceId} {
      allow read: if request.auth != null;
      allow create: if request.auth != null && 
                      validateInvoice(request.resource.data);
      allow update: if request.auth != null && 
                      request.auth.token.admin == true;
      allow delete: if request.auth != null && 
                      request.auth.token.admin == true;
    }
  }
  
  function validateInvoice(invoice) {
    return invoice.keys().hasAll(['ncf', 'rnc', 'fecha_procesamiento']) &&
           invoice.ncf is string &&
           invoice.rnc is string;
  }
}
```

### 3. Encriptar Datos Sensibles

```python
from cryptography.fernet import Fernet

def encrypt_sensitive_data(data: str, key: bytes) -> str:
    """Encrypt sensitive data before saving"""
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return encrypted.decode()
```

## Monitoreo y Costos

### Límites del Free Tier

**Firestore:**
- 1 GB de almacenamiento
- 50,000 lecturas/día
- 20,000 escrituras/día
- 20,000 eliminaciones/día

**Realtime Database:**
- 1 GB de almacenamiento
- 10 GB/mes de descarga
- 100 conexiones simultáneas

**Storage:**
- 5 GB de almacenamiento
- 1 GB/día de descarga

### Monitorear Uso

1. Ir a: https://console.firebase.google.com/
2. Seleccionar proyecto
3. **Usage and billing** → **Details**

### Configurar Alertas

1. **Budget & alerts**
2. Configurar presupuesto mensual
3. Agregar email para alertas

## Recursos Adicionales

- [Firebase Admin SDK Python](https://firebase.google.com/docs/admin/setup)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)
- [Realtime Database Documentation](https://firebase.google.com/docs/database)
- [Security Rules](https://firebase.google.com/docs/rules)

## Próximos Pasos

Con Firebase configurado, puedes:

1. Crear dashboard web para visualizar facturas
2. Implementar sincronización en tiempo real
3. Agregar autenticación de usuarios
4. Generar reportes desde Firebase
5. Integrar con otros servicios de Google Cloud
