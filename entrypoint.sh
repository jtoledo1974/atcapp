#!/bin/bash

# Verificar si SSH_HOST está definido y no está vacío
if [ -n "${SSH_HOST}" ]; then
    echo "SSH_HOST is defined, attempting to establish SSH tunnel..."

    # Iniciar el script de monitorización en segundo plano
    python monitor.py &

    # Esperar un momento para asegurarse de que el túnel esté establecido
    sleep 3
else
    echo "SSH_HOST is not defined or is empty, skipping SSH tunnel setup."
fi

# Ejecutar la aplicación Flask
exec python -m cambios.app
