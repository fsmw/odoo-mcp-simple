#!/usr/bin/env python3
"""
Servidor MCP Simple para Odoo 18
Conecta Claude con Odoo via XML-RPC

Este servidor implementa el protocolo MCP (Model Context Protocol) que permite
a Claude interactuar directamente con una instancia de Odoo a través de herramientas.

Funcionamiento:
1. Se conecta a Odoo usando XML-RPC
2. Expone herramientas que Claude puede usar
3. Cada herramienta realiza operaciones CRUD en Odoo
4. Devuelve los resultados formateados para Claude
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

# Importar componentes del protocolo MCP
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

# Importar nuestro cliente personalizado para Odoo
from odoo_client import OdooClient

# Configurar sistema de logging para debug y monitoreo
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar configuración desde config.json
# Este archivo contiene las credenciales y configuración de Odoo
config_path = Path(__file__).parent / "config.json"
with open(config_path) as f:
    config = json.load(f)

# Variable global para mantener la conexión con Odoo
# Se inicializa cuando se conecta por primera vez
odoo_client = None


async def initialize_odoo():
    """
    Inicializa la conexión con Odoo usando las credenciales del config.json
    
    Pasos:
    1. Obtiene las credenciales de la configuración
    2. Crea una instancia del cliente Odoo
    3. Intenta conectar usando XML-RPC
    4. Verifica la conexión obteniendo la versión del servidor
    
    Returns:
        bool: True si la conexión fue exitosa, False en caso contrario
    """
    global odoo_client
    
    # Obtener configuración de Odoo desde config.json
    odoo_config = config["odoo"]
    
    # Crear instancia del cliente con las credenciales
    odoo_client = OdooClient(
        url=odoo_config["url"],           # URL del servidor Odoo
        db=odoo_config["database"],       # Nombre de la base de datos
        username=odoo_config["username"], # Usuario de Odoo
        password=odoo_config["password"]  # Contraseña del usuario
    )
    
    # Intentar conectar y autenticarse
    if odoo_client.connect():
        # Si la conexión es exitosa, obtener información del servidor
        version = odoo_client.get_version()
        logger.info(f"✅ Conectado a Odoo {version.get('server_serie', 'Unknown')}")
        return True
    else:
        # Si falla la conexión, registrar el error
        logger.error("❌ No se pudo conectar a Odoo")
        return False


# Crear la instancia del servidor MCP
# Este servidor manejará todas las comunicaciones con Claude
app = Server(config["mcp"]["name"])


@app.list_tools()
async def list_tools() -> List[Tool]:
    """
    Define todas las herramientas que Claude puede usar para interactuar con Odoo
    
    Esta función registra las capacidades del servidor MCP.
    Cada herramienta tiene un nombre, descripción y esquema de entrada.
    Claude usará esta información para saber qué operaciones puede realizar.
    
    Returns:
        List[Tool]: Lista de herramientas disponibles con sus definiciones
    """
    return [
        # Herramienta para establecer conexión inicial con Odoo
        Tool(
            name="connect_odoo",
            description="Conectar con el servidor Odoo",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        # Herramienta para explorar la estructura de datos de Odoo
        Tool(
            name="list_models",
            description="Listar todos los modelos disponibles en Odoo",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        # Herramienta principal para buscar y filtrar registros
        Tool(
            name="search_records",
            description="Buscar registros en un modelo de Odoo",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Nombre del modelo (ej: res.partner)"},
                    "domain": {"type": "array", "description": "Dominio de búsqueda Odoo", "default": []},
                    "fields": {"type": "array", "description": "Campos a retornar", "default": []},
                    "limit": {"type": "integer", "description": "Límite de registros", "default": 10}
                },
                "required": ["model"]
            }
        ),
        # Herramienta para obtener detalles de un registro específico
        Tool(
            name="read_record",
            description="Leer un registro específico por ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Nombre del modelo"},
                    "record_id": {"type": "integer", "description": "ID del registro"},
                    "fields": {"type": "array", "description": "Campos a retornar", "default": []}
                },
                "required": ["model", "record_id"]
            }
        ),
        # Herramienta para crear nuevos registros en Odoo
        Tool(
            name="create_record",
            description="Crear un nuevo registro en Odoo",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Nombre del modelo"},
                    "values": {"type": "object", "description": "Valores del nuevo registro"}
                },
                "required": ["model", "values"]
            }
        ),
        # Herramienta para modificar registros existentes
        Tool(
            name="update_record",
            description="Actualizar un registro existente",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Nombre del modelo"},
                    "record_id": {"type": "integer", "description": "ID del registro"},
                    "values": {"type": "object", "description": "Valores a actualizar"}
                },
                "required": ["model", "record_id", "values"]
            }
        ),
        # Herramienta para eliminar registros de Odoo
        Tool(
            name="delete_record",
            description="Eliminar un registro de Odoo",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Nombre del modelo"},
                    "record_id": {"type": "integer", "description": "ID del registro a eliminar"}
                },
                "required": ["model", "record_id"]
            }
        ),
        # Herramienta para inspeccionar la estructura de un modelo
        Tool(
            name="get_model_fields",
            description="Obtener información sobre los campos de un modelo",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Nombre del modelo"}
                },
                "required": ["model"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Ejecuta una herramienta solicitada por Claude
    
    Esta es la función principal que recibe las solicitudes de Claude
    y las traduce a operaciones en Odoo. Maneja:
    - Validación de conexión
    - Ejecución de operaciones CRUD
    - Formateo de respuestas
    - Manejo de errores
    
    Args:
        name: Nombre de la herramienta a ejecutar
        arguments: Argumentos para la herramienta
        
    Returns:
        List[TextContent]: Respuesta formateada para Claude
    """
    global odoo_client
    
    try:
        # Manejar conexión inicial a Odoo
        if name == "connect_odoo":
            success = await initialize_odoo()
            if success:
                return [TextContent(
                    type="text",
                    text="✅ Conectado exitosamente a Odoo"
                )]
            else:
                return [TextContent(
                    type="text",
                    text="❌ Error al conectar con Odoo. Verifica las credenciales."
                )]
        
        # Para todas las demás operaciones, verificar que hay conexión
        # Si no hay conexión, intentar conectar automáticamente
        if not odoo_client or not odoo_client.uid:
            await initialize_odoo()
            if not odoo_client or not odoo_client.uid:
                return [TextContent(
                    type="text",
                    text="❌ No hay conexión con Odoo. Usa 'connect_odoo' primero."
                )]
        
        # OPERACIÓN: Listar modelos disponibles en Odoo
        if name == "list_models":
            # Obtener lista de todos los modelos desde Odoo
            models = odoo_client.list_models()
            
            # Formatear respuesta para Claude (limitamos a 20 para legibilidad)
            result = "📋 Modelos disponibles:\n"
            for m in models[:20]:  # Mostrar solo los primeros 20
                result += f"  • {m['model']}: {m['name']}\n"
            result += f"\n(Mostrando 20 de {len(models)} modelos)"
            
            return [TextContent(type="text", text=result)]
        
        # OPERACIÓN: Buscar registros con filtros
        elif name == "search_records":
            # Extraer parámetros de la solicitud
            model = arguments["model"]                    # Modelo de Odoo (ej: res.partner)
            domain = arguments.get("domain", [])         # Filtros de búsqueda
            fields = arguments.get("fields", [])         # Campos específicos a obtener
            limit = arguments.get("limit", 10)           # Límite de registros
            
            # Ejecutar búsqueda en Odoo usando search_read
            records = odoo_client.search_read(model, domain, fields, limit)
            
            # Manejar caso sin resultados
            if not records:
                return [TextContent(type="text", text="No se encontraron registros")]
            
            # Formatear y devolver resultados como JSON
            result = f"🔍 Encontrados {len(records)} registros en {model}:\n"
            result += json.dumps(records, indent=2, ensure_ascii=False)
            
            return [TextContent(type="text", text=result)]
        
        # OPERACIÓN: Leer un registro específico por ID
        elif name == "read_record":
            # Extraer parámetros
            model = arguments["model"]                    # Modelo de Odoo
            record_id = arguments["record_id"]           # ID específico del registro
            fields = arguments.get("fields", [])         # Campos a obtener (todos si está vacío)
            
            # Leer el registro específico desde Odoo
            records = odoo_client.read(model, [record_id], fields)
            
            # Verificar si se encontró el registro
            if not records:
                return [TextContent(type="text", text=f"No se encontró el registro con ID {record_id}")]
            
            # Formatear y devolver el registro encontrado
            result = f"📖 Registro {model}/{record_id}:\n"
            result += json.dumps(records[0], indent=2, ensure_ascii=False)
            
            return [TextContent(type="text", text=result)]
        
        # OPERACIÓN: Crear un nuevo registro
        elif name == "create_record":
            # Extraer parámetros
            model = arguments["model"]                    # Modelo donde crear el registro
            values = arguments["values"]                  # Diccionario con los valores del nuevo registro
            
            # Crear el registro en Odoo y obtener su ID
            new_id = odoo_client.create(model, values)
            
            # Confirmar creación exitosa
            return [TextContent(
                type="text",
                text=f"✅ Registro creado exitosamente!\n📋 Modelo: {model}\n🆔 ID: {new_id}"
            )]
        
        # OPERACIÓN: Actualizar un registro existente
        elif name == "update_record":
            # Extraer parámetros
            model = arguments["model"]                    # Modelo del registro a actualizar
            record_id = arguments["record_id"]           # ID del registro a modificar
            values = arguments["values"]                  # Nuevos valores para el registro
            
            # Actualizar el registro en Odoo
            success = odoo_client.update(model, [record_id], values)
            
            # Verificar resultado de la actualización
            if success:
                return [TextContent(
                    type="text",
                    text=f"✅ Registro {model}/{record_id} actualizado exitosamente!"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ Error al actualizar el registro {model}/{record_id}"
                )]
        
        # OPERACIÓN: Eliminar un registro
        elif name == "delete_record":
            # Extraer parámetros
            model = arguments["model"]                    # Modelo del registro a eliminar
            record_id = arguments["record_id"]           # ID del registro a eliminar
            
            # Eliminar el registro de Odoo
            success = odoo_client.delete(model, [record_id])
            
            # Verificar resultado de la eliminación
            if success:
                return [TextContent(
                    type="text",
                    text=f"🗑️ Registro {model}/{record_id} eliminado exitosamente"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ Error al eliminar el registro {model}/{record_id}"
                )]
        
        # OPERACIÓN: Inspeccionar campos de un modelo
        elif name == "get_model_fields":
            # Extraer parámetros
            model = arguments["model"]                    # Modelo a inspeccionar
            
            # Obtener definición de campos desde Odoo
            fields = odoo_client.get_fields(model)
            
            # Formatear información de campos (limitamos a 15 para legibilidad)
            result = f"📊 Campos del modelo {model}:\n"
            for field_name, field_info in list(fields.items())[:15]:
                field_type = field_info.get('type', 'unknown')
                required = '⚠️' if field_info.get('required', False) else ''
                result += f"  • {field_name} ({field_type}) {required}\n"
                # Agregar ayuda si está disponible
                if field_info.get('help'):
                    result += f"    → {field_info['help'][:50]}...\n"
            
            return [TextContent(type="text", text=result)]
        
        # Manejar herramientas no reconocidas
        else:
            return [TextContent(
                type="text",
                text=f"❌ Herramienta desconocida: {name}"
            )]
            
    # Manejo global de errores
    except Exception as e:
        logger.error(f"Error ejecutando {name}: {e}")
        return [TextContent(
            type="text",
            text=f"❌ Error: {str(e)}"
        )]


async def main():
    """
    Función principal del servidor MCP
    
    Flujo de ejecución:
    1. Registra el inicio del servidor en los logs
    2. Intenta establecer conexión inicial con Odoo
    3. Inicia el servidor MCP usando stdio (entrada/salida estándar)
    4. Mantiene el servidor corriendo para recibir solicitudes de Claude
    
    El servidor funciona como un puente de comunicación:
    Claude → Solicitudes MCP → Este servidor → XML-RPC → Odoo
    Odoo → XML-RPC → Este servidor → Respuestas MCP → Claude
    """
    # Registrar inicio del servidor
    logger.info(f"🚀 Iniciando {config['mcp']['name']} v{config['mcp']['version']}")
    
    # Intentar conexión inicial con Odoo (no crítico si falla)
    await initialize_odoo()
    
    # Iniciar servidor MCP usando stdio (comunicación con Claude)
    # stdio_server permite la comunicación bidireccional con Claude Code
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,           # Canal para recibir solicitudes de Claude
            write_stream,          # Canal para enviar respuestas a Claude
            app.create_initialization_options()  # Opciones de configuración MCP
        )


# Punto de entrada del programa
if __name__ == "__main__":
    # Ejecutar el servidor de forma asíncrona
    asyncio.run(main())