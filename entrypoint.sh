#!/bin/bash

# Verificar si SSH_HOST está definido y no está vacío
if [ -n "${SSH_HOST}" ]; then
    echo "SSH_HOST is defined, attempting to establish SSH tunnel..."
    echo -n "Waiting for SSH tunnel to be ready"
    # Iniciar el script de monitorización en segundo plano
    python monitor.py &
    
    # Esperar a que el archivo de señalización exista
    while [ ! -f /tmp/tunnel_ready ]; do
        echo -n "."
        sleep 2
    done

    echo ""
    echo "SSH tunnel is ready."
else
    echo "SSH_HOST is not defined or is empty, skipping SSH tunnel setup."
fi

# Ejecutar la aplicación Flask con Gunicorn
echo "Starting Gunicorn..."
gunicorn --bind 127.0.0.1:8000 --error-logfile - --workers=3 --capture-output  atcapp.wsgi:app &
GUNICORN_PID=$!

# Función para verificar si Gunicorn está listo
function wait_for_gunicorn {
    while true; do
        if curl -s http://127.0.0.1:8000 > /dev/null; then
            return 0
        else
            sleep 1
        fi
    done
}

# Esperar hasta que Gunicorn esté completamente iniciado
echo "Waiting for Gunicorn to be fully started..."
wait_for_gunicorn
echo "Gunicorn started successfully."

# Iniciar Nginx
echo "Starting Nginx..."
service nginx start

sleep 5

# Verificar que Nginx se haya iniciado correctamente
if ! pgrep -x "nginx" > /dev/null; then
    echo "Nginx failed to start."
    exit 1
fi
echo "Nginx started successfully."

# Mantener el script en ejecución para que Docker no lo finalice
wait $GUNICORN_PID
