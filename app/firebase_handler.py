"""
Firebase integration handler
"""
import firebase_admin
from firebase_admin import credentials, firestore, db
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path
import base64
import json
import tempfile
import os
from app.models import Invoice
from app.utils.logger import app_logger
from app.utils.config import settings


class FirebaseHandler:
    """Handles Firebase Firestore operations"""
    
    def __init__(self):
        """Initialize Firebase"""
        try:
            # Check if already initialized
            try:
                firebase_admin.get_app()
                app_logger.info("Firebase app already initialized, using existing instance")
            except ValueError:
                cred = None
                
                # OPTION 1: Use Base64 from environment (PRODUCTION)
                creds_base64 = os.environ.get("FIREBASE_CREDENTIALS_BASE64")
                
                if creds_base64:
                    try:
                        # Decode Base64
                        creds_json = base64.b64decode(creds_base64).decode('utf-8')
                        creds_dict = json.loads(creds_json)
                        
                        # Create temporary file
                        temp_cred_path = None
                        try:
                            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                                json.dump(creds_dict, f)
                                temp_cred_path = f.name
                            
                            cred = credentials.Certificate(temp_cred_path)
                            app_logger.info("✅ Using Firebase credentials from Base64 environment variable")
                        finally:
                            # Clean up temp file
                            if temp_cred_path and os.path.exists(temp_cred_path):
                                os.unlink(temp_cred_path)
                    except Exception as e:
                        app_logger.error(f"Failed to decode Base64 credentials: {e}")
                
                # OPTION 2: Use file path (LOCAL DEVELOPMENT)
                if cred is None and settings.firebase_credentials:
                    cred_path = Path(settings.firebase_credentials)
                    if cred_path.exists():
                        cred = credentials.Certificate(str(cred_path))
                        app_logger.info("✅ Using Firebase credentials from file")
                
                if cred is None:
                    app_logger.error("❌ No Firebase credentials found (checked env var and file)")
                    self.db = None
                    self.firestore_db = None
                    return
                
                # Initialize Firebase
                firebase_admin.initialize_app(cred, {
                    'databaseURL': settings.firebase_database_url
                })
                
                app_logger.info("Firebase Firestore initialized successfully")
            
            # Get references
            self.db = db.reference()
            self.firestore_db = firestore.client()
            
            app_logger.info(f"Database URL: {settings.firebase_database_url}")
            
        except Exception as e:
            app_logger.error(f"Failed to initialize Firebase: {e}")
            self.db = None
            self.firestore_db = None
    
    def save_invoice(self, invoice: Invoice, empresa_id: Optional[str] = None) -> bool:
        """
        Save invoice to Firestore
        
        Args:
            invoice: Invoice object to save
            empresa_id: ID of the company (optional, will use RNC if not provided)
            
        Returns:
            True if saved successfully
        """
        if not self.firestore_db:
            app_logger.warning("Firebase not initialized")
            return False
        
        try:
            # Use RNC as empresa_id if not provided
            if not empresa_id and invoice.rnc:
                empresa_id = f"emp_{invoice.rnc}"
            elif not empresa_id:
                empresa_id = "sin_empresa"
            
            # Prepare data for Firestore
            invoice_data = {
                'id': invoice.id,
                'ncf': invoice.ncf or '',
                'rnc': invoice.rnc or '',
                'razon_social': invoice.razon_social or '',
                'fecha_emision': invoice.fecha_emision or '',
                'fecha_procesamiento': invoice.fecha_procesamiento or datetime.now().isoformat(),
                'subtotal': invoice.montos.subtotal if invoice.montos.subtotal else 0,
                'itbis': invoice.montos.itbis if invoice.montos.itbis else 0,
                'total': invoice.montos.total if invoice.montos.total else 0,
                'moneda': invoice.montos.moneda or 'DOP',
                'imagen_original': invoice.metadata.imagen_original or '',
                'confianza_ocr': invoice.metadata.confianza_ocr if invoice.metadata.confianza_ocr else 0,
                'origen': invoice.metadata.origen or 'whatsapp',
                'revisada': False,
                'exportada': False,
                'empresa_id': empresa_id,
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            
            # Save to: facturas/{empresa_id}/items/{invoice_id}
            factura_ref = self.firestore_db.collection('facturas').document(empresa_id).collection('items').document(invoice.id)
            factura_ref.set(invoice_data)
            
            app_logger.info(f"Invoice saved to Firestore: {invoice.id} (Empresa: {empresa_id})")
            
            # Update empresa info if not exists
            if invoice.rnc and invoice.razon_social:
                self._ensure_empresa_exists(empresa_id, invoice.rnc, invoice.razon_social)
            
            # Update provider statistics
            if invoice.rnc:
                self._update_provider_stats(invoice.rnc, invoice.razon_social, empresa_id)
            
            return True
            
        except Exception as e:
            app_logger.error(f"Error saving to Firestore: {e}")
            return False
    
    def _ensure_empresa_exists(self, empresa_id: str, rnc: str, razon_social: str):
        """
        Ensure empresa exists in Firestore, create if not
        
        Args:
            empresa_id: Empresa ID
            rnc: RNC of the company
            razon_social: Business name
        """
        try:
            empresa_ref = self.firestore_db.collection('empresas').document(empresa_id)
            empresa_doc = empresa_ref.get()
            
            if not empresa_doc.exists:
                # Create new empresa
                empresa_ref.set({
                    'id': empresa_id,
                    'rnc': rnc,
                    'nombre': razon_social,
                    'activa': True,
                    'fecha_creacion': firestore.SERVER_TIMESTAMP,
                    'total_facturas': 1
                })
                app_logger.info(f"Created new empresa: {empresa_id} - {razon_social}")
            else:
                # Update total facturas
                empresa_ref.update({
                    'total_facturas': firestore.Increment(1)
                })
                
        except Exception as e:
            app_logger.error(f"Error ensuring empresa exists: {e}")
    
    def _update_provider_stats(self, rnc: str, razon_social: Optional[str], empresa_id: str):
        """
        Update provider statistics
        
        Args:
            rnc: RNC of the provider
            razon_social: Business name
            empresa_id: Empresa ID
        """
        try:
            provider_ref = self.firestore_db.collection('proveedores').document(rnc)
            provider_doc = provider_ref.get()
            
            if provider_doc.exists:
                # Increment counter
                provider_ref.update({
                    'total_facturas': firestore.Increment(1),
                    'ultima_factura': firestore.SERVER_TIMESTAMP
                })
            else:
                # Create new provider
                provider_ref.set({
                    'rnc': rnc,
                    'razon_social': razon_social or '',
                    'total_facturas': 1,
                    'empresa_id': empresa_id,
                    'fecha_registro': firestore.SERVER_TIMESTAMP,
                    'ultima_factura': firestore.SERVER_TIMESTAMP
                })
                app_logger.info(f"Created new provider: {rnc} - {razon_social}")
                
        except Exception as e:
            app_logger.error(f"Error updating provider stats: {e}")
    
    def get_empresas(self) -> List[Dict]:
        """
        Get all empresas from Firestore
        
        Returns:
            List of empresa dictionaries
        """
        if not self.firestore_db:
            app_logger.warning("Firebase not initialized")
            return []
        
        try:
            empresas_ref = self.firestore_db.collection('empresas')
            empresas_docs = empresas_ref.stream()
            
            empresas = []
            for doc in empresas_docs:
                empresa_data = doc.to_dict()
                empresa_data['id'] = doc.id
                empresas.append(empresa_data)
            
            app_logger.info(f"Retrieved {len(empresas)} empresas from Firestore")
            return empresas
            
        except Exception as e:
            app_logger.error(f"Error getting empresas: {e}")
            return []
    
    def get_facturas_by_empresa(self, empresa_id: str) -> List[Dict]:
        """
        Get all facturas for a specific empresa
        
        Args:
            empresa_id: Empresa ID
            
        Returns:
            List of factura dictionaries
        """
        if not self.firestore_db:
            app_logger.warning("Firebase not initialized")
            return []
        
        try:
            facturas_ref = self.firestore_db.collection('facturas').document(empresa_id).collection('items')
            facturas_docs = facturas_ref.order_by('fecha_procesamiento', direction=firestore.Query.DESCENDING).stream()
            
            facturas = []
            for doc in facturas_docs:
                factura_data = doc.to_dict()
                factura_data['id'] = doc.id
                facturas.append(factura_data)
            
            app_logger.info(f"Retrieved {len(facturas)} facturas for empresa {empresa_id}")
            return facturas
            
        except Exception as e:
            app_logger.error(f"Error getting facturas for empresa {empresa_id}: {e}")
            return []
    
    def get_factura(self, empresa_id: str, factura_id: str) -> Optional[Dict]:
        """
        Get a specific factura
        
        Args:
            empresa_id: Empresa ID
            factura_id: Factura ID
            
        Returns:
            Factura dictionary or None
        """
        if not self.firestore_db:
            app_logger.warning("Firebase not initialized")
            return None
        
        try:
            factura_ref = self.firestore_db.collection('facturas').document(empresa_id).collection('items').document(factura_id)
            factura_doc = factura_ref.get()
            
            if factura_doc.exists:
                factura_data = factura_doc.to_dict()
                factura_data['id'] = factura_doc.id
                return factura_data
            
            return None
            
        except Exception as e:
            app_logger.error(f"Error getting factura {factura_id}: {e}")
            return None
    
    def update_factura(self, empresa_id: str, factura_id: str, updates: Dict) -> bool:
        """
        Update a factura
        
        Args:
            empresa_id: Empresa ID
            factura_id: Factura ID
            updates: Dictionary with fields to update
            
        Returns:
            True if updated successfully
        """
        if not self.firestore_db:
            app_logger.warning("Firebase not initialized")
            return False
        
        try:
            factura_ref = self.firestore_db.collection('facturas').document(empresa_id).collection('items').document(factura_id)
            factura_ref.update(updates)
            
            app_logger.info(f"Updated factura {factura_id} in empresa {empresa_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"Error updating factura {factura_id}: {e}")
            return False
    
    def mark_factura_revisada(self, empresa_id: str, factura_id: str) -> bool:
        """
        Mark a factura as reviewed
        
        Args:
            empresa_id: Empresa ID
            factura_id: Factura ID
            
        Returns:
            True if updated successfully
        """
        return self.update_factura(empresa_id, factura_id, {
            'revisada': True,
            'fecha_revision': firestore.SERVER_TIMESTAMP
        })
    
    def mark_factura_exportada(self, empresa_id: str, factura_id: str) -> bool:
        """
        Mark a factura as exported
        
        Args:
            empresa_id: Empresa ID
            factura_id: Factura ID
            
        Returns:
            True if updated successfully
        """
        return self.update_factura(empresa_id, factura_id, {
            'exportada': True,
            'fecha_exportacion': firestore.SERVER_TIMESTAMP
        })
    
    def get_facturas_pendientes(self, empresa_id: Optional[str] = None) -> List[Dict]:
        """
        Get all facturas that haven't been reviewed yet
        
        Args:
            empresa_id: Optional empresa ID to filter
            
        Returns:
            List of factura dictionaries
        """
        if not self.firestore_db:
            app_logger.warning("Firebase not initialized")
            return []
        
        try:
            facturas = []
            
            if empresa_id:
                # Get for specific empresa
                facturas_ref = self.firestore_db.collection('facturas').document(empresa_id).collection('items')
                facturas_docs = facturas_ref.where('revisada', '==', False).order_by('fecha_procesamiento', direction=firestore.Query.DESCENDING).stream()
                
                for doc in facturas_docs:
                    factura_data = doc.to_dict()
                    factura_data['id'] = doc.id
                    facturas.append(factura_data)
            else:
                # Get all empresas first
                empresas = self.get_empresas()
                
                for empresa in empresas:
                    emp_id = empresa['id']
                    facturas_ref = self.firestore_db.collection('facturas').document(emp_id).collection('items')
                    facturas_docs = facturas_ref.where('revisada', '==', False).stream()
                    
                    for doc in facturas_docs:
                        factura_data = doc.to_dict()
                        factura_data['id'] = doc.id
                        factura_data['empresa_id'] = emp_id
                        facturas.append(factura_data)
            
            app_logger.info(f"Found {len(facturas)} facturas pendientes")
            return facturas
            
        except Exception as e:
            app_logger.error(f"Error getting facturas pendientes: {e}")
            return []
    
    def get_facturas_para_exportar(self, empresa_id: Optional[str] = None) -> List[Dict]:
        """
        Get all facturas that have been reviewed but not exported
        
        Args:
            empresa_id: Optional empresa ID to filter
            
        Returns:
            List of factura dictionaries
        """
        if not self.firestore_db:
            app_logger.warning("Firebase not initialized")
            return []
        
        try:
            facturas = []
            
            if empresa_id:
                # Get for specific empresa
                facturas_ref = self.firestore_db.collection('facturas').document(empresa_id).collection('items')
                facturas_docs = facturas_ref.where('revisada', '==', True).where('exportada', '==', False).stream()
                
                for doc in facturas_docs:
                    factura_data = doc.to_dict()
                    factura_data['id'] = doc.id
                    facturas.append(factura_data)
            else:
                # Get all empresas first
                empresas = self.get_empresas()
                
                for empresa in empresas:
                    emp_id = empresa['id']
                    facturas_ref = self.firestore_db.collection('facturas').document(emp_id).collection('items')
                    # Note: Firestore doesn't support multiple inequality filters on different fields
                    # So we filter in Python
                    facturas_docs = facturas_ref.where('revisada', '==', True).stream()
                    
                    for doc in facturas_docs:
                        factura_data = doc.to_dict()
                        if not factura_data.get('exportada', False):
                            factura_data['id'] = doc.id
                            factura_data['empresa_id'] = emp_id
                            facturas.append(factura_data)
            
            app_logger.info(f"Found {len(facturas)} facturas para exportar")
            return facturas
            
        except Exception as e:
            app_logger.error(f"Error getting facturas para exportar: {e}")
            return []
    
    def delete_factura(self, empresa_id: str, factura_id: str) -> bool:
        """
        Delete a factura
        
        Args:
            empresa_id: Empresa ID
            factura_id: Factura ID
            
        Returns:
            True if deleted successfully
        """
        if not self.firestore_db:
            app_logger.warning("Firebase not initialized")
            return False
        
        try:
            factura_ref = self.firestore_db.collection('facturas').document(empresa_id).collection('items').document(factura_id)
            factura_ref.delete()
            
            # Update empresa total facturas
            empresa_ref = self.firestore_db.collection('empresas').document(empresa_id)
            empresa_ref.update({
                'total_facturas': firestore.Increment(-1)
            })
            
            app_logger.info(f"Deleted factura {factura_id} from empresa {empresa_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"Error deleting factura {factura_id}: {e}")
            return False
    
    def get_all_facturas(self) -> List[Dict]:
        """
        Get all facturas from all empresas
        
        Returns:
            List of factura dictionaries
        """
        if not self.firestore_db:
            app_logger.warning("Firebase not initialized")
            return []
        
        try:
            empresas = self.get_empresas()
            all_facturas = []
            
            for empresa in empresas:
                emp_id = empresa['id']
                facturas = self.get_facturas_by_empresa(emp_id)
                
                for factura in facturas:
                    factura['empresa_id'] = emp_id
                    factura['empresa_nombre'] = empresa.get('nombre', '')
                    all_facturas.append(factura)
            
            app_logger.info(f"Retrieved {len(all_facturas)} facturas from all empresas")
            return all_facturas
            
        except Exception as e:
            app_logger.error(f"Error getting all facturas: {e}")
            return []


# Global Firebase handler instance
firebase_handler = FirebaseHandler()