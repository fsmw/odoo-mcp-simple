# 🚀 Servidor MCP Simple para Odoo

Conecta Claude (o cualquier LLM compatible con MCP) con Odoo 18 SaaS.

## 📦 Instalación

```bash
# Instalar dependencias
pip install mcp

# Configurar credenciales
edit config.json
```

## 🔧 Configuración

Edita `config.json` con tus credenciales:

```json
{
    "odoo": {
        "url": "https://tu-instancia.odoo.com",
        "database": "tu-database",
        "username": "tu@email.com",
        "password": "tu-password"
    }
}
```

## 🎮 Uso

### Iniciar el servidor:

```bash
python server.py
```

### Configurar en Claude Desktop:

Añade a tu `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "odoo-simple": {
      "command": "python",
      "args": ["/ruta/a/odoo-mcp-simple/server.py"]
    }
  }
}
```

## 🛠️ Herramientas Disponibles

- `connect_odoo` - Conectar con Odoo
- `list_models` - Listar modelos disponibles
- `search_records` - Buscar registros
- `read_record` - Leer un registro específico
- `create_record` - Crear nuevo registro
- `update_record` - Actualizar registro
- `delete_record` - Eliminar registro
- `get_model_fields` - Ver campos de un modelo

## 📝 Ejemplos

### Buscar clientes:
```
search_records(model="res.partner", domain=[["is_company", "=", true]])
```

### Crear contacto:
```
create_record(model="res.partner", values={"name": "John Doe", "email": "john@example.com"})
```

## 🤝 Contribuir

¡PRs bienvenidos! Este es un proyecto de demo educativo.

## 📄 Licencia

MIT