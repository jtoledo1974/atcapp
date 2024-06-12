#!/bin/bash

# Variables de entorno
SSH_HOST=${SSH_HOST}
SSH_PORT=${SSH_PORT}
SSH_USER=${SSH_USER}
SSH_PRIVATE_KEY=${SSH_PRIVATE_KEY}
SSH_KEY_PATH=${SSH_KEY_PATH}

DB_HOST=mariadb
DB_PORT=3306

# Verificar si SSH_HOST está definido y no está vacío
if [ -n "${SSH_HOST}" ]; then
    echo "SSH_HOST is defined, attempting to establish SSH tunnel..."

    # Crear el archivo de clave privada SSH
    mkdir -p $(dirname ${SSH_KEY_PATH})
    echo "${SSH_PRIVATE_KEY}" > ${SSH_KEY_PATH}
    chmod 600 ${SSH_KEY_PATH}
    ls -l ${SSH_KEY_PATH}

    # Establecer el túnel SSH
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -N -L ${DB_PORT}:${DB_HOST}:${DB_PORT} -p ${SSH_PORT} ${SSH_USER}@${SSH_HOST} -i ${SSH_KEY_PATH} &

    # Esperar un momento para asegurarse de que el túnel esté establecido
    sleep 2
else
    echo "SSH_HOST is not defined or is empty, skipping SSH tunnel setup."
fi

# Ejecutar la aplicación Flask
exec python -m cambios.app
