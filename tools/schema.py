tools_schema = [
    {
        "type": "function",
        "name": "read_file",
        "description": "Recibe una ruta de archivo y devuelve en un solo string todas las líneas del archivo",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Ruta del archivo a leer"}
            },
            "required": ["path"]
        }
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Recibe la ruta del archivo y el contenido que debe ir en él. Sobrescribe el archivo completo.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Ruta del archivo a escribir"},
                "content": {"type": "string", "description": "Contenido completo que reemplazará el archivo"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "type": "function",
        "name": "run_in_shell",
        "description": "Recibe un comando de shell como string y lo ejecuta, devolviendo stdout, stderr y código de salida",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Comando de shell a ejecutar"}
            },
            "required": ["command"]
        }
    }
]   
