#!/usr/bin/env python3
"""
Cliente simple para conectar con Odoo via XML-RPC
"""
import xmlrpc.client
import json
from typing import Any, Dict, List, Optional


class OdooClient:
    def __init__(self, url: str, db: str, username: str, password: str):
        """
        Inicializa el cliente de Odoo
        """
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.models = None
        
        # Endpoints XML-RPC
        self.common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        self.models_endpoint = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
    def connect(self) -> bool:
        """
        Autentica con el servidor Odoo
        """
        try:
            self.uid = self.common.authenticate(
                self.db, 
                self.username, 
                self.password, 
                {}
            )
            return self.uid is not False
        except Exception as e:
            print(f"Error conectando: {e}")
            return False
    
    def get_version(self) -> Dict:
        """
        Obtiene la versión de Odoo
        """
        try:
            return self.common.version()
        except Exception as e:
            return {"error": str(e)}
    
    def search(self, model: str, domain: List = None, limit: int = 100) -> List[int]:
        """
        Busca registros en un modelo
        """
        if not self.uid:
            raise Exception("No conectado a Odoo")
        
        domain = domain or []
        return self.models_endpoint.execute_kw(
            self.db, self.uid, self.password,
            model, 'search',
            [domain],
            {'limit': limit}
        )
    
    def read(self, model: str, ids: List[int], fields: List[str] = None) -> List[Dict]:
        """
        Lee registros específicos
        """
        if not self.uid:
            raise Exception("No conectado a Odoo")
        
        params = {}
        if fields:
            params['fields'] = fields
            
        return self.models_endpoint.execute_kw(
            self.db, self.uid, self.password,
            model, 'read',
            [ids],
            params
        )
    
    def search_read(self, model: str, domain: List = None, fields: List[str] = None, limit: int = 100) -> List[Dict]:
        """
        Busca y lee registros en una sola operación
        """
        if not self.uid:
            raise Exception("No conectado a Odoo")
        
        domain = domain or []
        params = {'limit': limit}
        if fields:
            params['fields'] = fields
            
        return self.models_endpoint.execute_kw(
            self.db, self.uid, self.password,
            model, 'search_read',
            [domain],
            params
        )
    
    def create(self, model: str, values: Dict) -> int:
        """
        Crea un nuevo registro
        """
        if not self.uid:
            raise Exception("No conectado a Odoo")
        
        return self.models_endpoint.execute_kw(
            self.db, self.uid, self.password,
            model, 'create',
            [values]
        )
    
    def update(self, model: str, ids: List[int], values: Dict) -> bool:
        """
        Actualiza registros existentes
        """
        if not self.uid:
            raise Exception("No conectado a Odoo")
        
        return self.models_endpoint.execute_kw(
            self.db, self.uid, self.password,
            model, 'write',
            [ids, values]
        )
    
    def delete(self, model: str, ids: List[int]) -> bool:
        """
        Elimina registros
        """
        if not self.uid:
            raise Exception("No conectado a Odoo")
        
        return self.models_endpoint.execute_kw(
            self.db, self.uid, self.password,
            model, 'unlink',
            [ids]
        )
    
    def get_fields(self, model: str) -> Dict:
        """
        Obtiene los campos de un modelo
        """
        if not self.uid:
            raise Exception("No conectado a Odoo")
        
        return self.models_endpoint.execute_kw(
            self.db, self.uid, self.password,
            model, 'fields_get',
            [],
            {'attributes': ['string', 'help', 'type', 'required']}
        )
    
    def list_models(self) -> List[str]:
        """
        Lista todos los modelos disponibles
        """
        if not self.uid:
            raise Exception("No conectado a Odoo")
        
        models = self.search_read('ir.model', [], ['model', 'name'], limit=500)
        return [{'model': m['model'], 'name': m['name']} for m in models]