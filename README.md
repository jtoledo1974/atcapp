

# ATCApp: Gestión de Turnos para ATCS de Enaire

Este proyecto está diseñado para facilitar la gestión de turnos para los Controladores de Tránsito Aéreo (ATCS) de Enaire. Utiliza una aplicación Flask con una base de datos para almacenar y gestionar los turnos de los empleados, integrándose con Firebase para la autenticación y administración de usuarios.

## Características
- **Gestión de Turnos**: Registro y visualización de turnos asignados.
- **Autenticación**: Uso de Firebase Admin SDK para la verificación de usuarios.
- **Interfaz de Administración**: Integración con Flask-Admin para la gestión de datos.
- **Persistencia de Datos**: Soporte para bases de datos SQL, con opción para almacenar datos de forma persistente en servicios gestionados.

### Tecnologías Utilizadas
- **Flask**: Framework web para Python.
- **SQLAlchemy**: ORM para la gestión de la base de datos.
- **Firebase**: Servicios de autenticación y administración de usuarios.
- **Docker**: Contenerización de la aplicación para un despliegue flexible y escalable.

## Instalación y Configuración

### Clonar el Repositorio
```sh
git clone https://github.com/jtoledo1974/cambios.git
```

### Crear un entorno virtual
```sh
python3 -m venv venv
source venv/bin/activate
```

### Instalar paquete y dependencias
```sh
pip install -e ".[dev]"
```

Suponiendo que el entorno está cargado (mirar más abajo), se puede arrancar la aplicación con el siguiente comando:
```sh
python -m cambios.app
```


### Instalar imágenes precompiladas
El docker es de particular interés para ejecutar la aplicación en un entorno de producción. Se puede utilizar la imagen precompilada de Docker Hub para ejecutar la aplicación en un contenedor Docker.
```sh
docker run -d -p 80:80 toledo74/cambios
```

### Variables de entorno

No es estrictamente necesario utilizar variables de entorno para 
ejecutar la aplicación, pero sin un archivo atcapp.json en el directorio raíz que contenga las credenciales de Firebase, la aplicación no hará nada útil.

#### Firebase

Este proyecto utiliza el SDK de administración de Firebase para la autenticación. El SDK se puede inicializar utilizando un archivo de credenciales o una cadena JSON pasada a través de variables de entorno, lo que lo hace flexible para diferentes entornos. Sólo se necesita una de las dos opciones para inicializar el SDK.

- `FIREBASE_CRED_FILE`: Ruta al archivo de credenciales de Firebase (el valor predeterminado es `atcapp.json`).
- `FIREBASE_CRED_JSON`: Cadena JSON codificada en BASE64 de las credenciales de Firebase.


#### Flask y general

Estas variables de entorno se utilizan para configurar la aplicación.

- `FLASK_SQLALCHEMY_DATABASE_URI`: URI de la base de datos utilizada por SQLAlchemy. Si no se proporciona, se utilizará una base de datos SQLite por defecto. Si se está utilizando SSH_HOST para
utilizar un túnel SSH el host del DATABASE_URI deberá ser localhost
- `FLASK_SQLALCHEMY_TRACK_MODIFICATIONS`: Indica si se deben realizar seguimientos de modificaciones en la base de datos. Se recomienda desactivarlo en entornos de producción.
- `FLASK_SECRET_KEY`: Clave secreta utilizada para la generación de tokens de seguridad. Si no se proporciona, se generará una clave aleatoria.
- `FLASK_DEBUG`: Indica si el modo de depuración está habilitado. Se interpreta como verdadero si el valor es "true", "1" o "t" (ignorando mayúsculas y minúsculas).
- `FLASK_HOST`: Dirección IP en la que se ejecutará la aplicación. Si no se proporciona, se utilizará localhost y no servirá clientes externos.
- `FLASK_PORT`: Puerto en el que se ejecutará la aplicación. Si no se proporciona, se utilizará el puerto 80.
- `ENABLE_LOGGING`: Indica si se deben habilitar los registros de la aplicación en logs/
- `LOG_LEVEL`: Nivel de registro de la aplicación. Los valores válidos son DEBUG, INFO, WARNING, ERROR y CRITICAL.
- `TZ`: Zona horaria utilizada por la aplicación. Si no se proporciona, se utilizará "Europe/Madrid".

#### Acceso remoto a la base de datos para contenedores Docker

De aplicación para producción en la nube, se puede configurar una
base de datos accesible a través de un túnel SSH. Para ello, se pueden utilizar las siguientes variables de entorno.

- `SSH_HOST`: Hostname o dirección IP del servidor SSH.
- `SSH_PORT`: Puerto del servidor SSH. Por defecto, es 22.
- `SSH_USER`: Usuario SSH. Por defecto, es root.
- `SSH_PRIVATE_KEY`: Clave privada SSH (texto plano, *no BASE64*).
- `DB_HOST`: Hostname o dirección IP de la base de datos accesible desde el servidor de ssh. Por defecto, es mariadb.
- `DB_PORT`: Puerto de la base de datos. Por defecto, es 3306.


## Referencia de desarrollo

### Actualizar la imagen de docker en docker hub
    
```sh
docker build -t toledo74/cambios:latest .
docker login
docker push toledo74/cambios:latest
```

### Arranque en pruebas con un contenedor en local
Copiar la clave privada del servidor de ssh en id_rsa y las credenciales en atcapp.json
 
```sh
SSH_PRIVATE_KEY=$(cat id_rsa)
CRED=$(cat atcapp.json | base64)
```
Prepara un archivo .env con el resto de variables de entorno. Por ejemplo, suponiendo una pasarela ssh para acceder al servidor de base de datos y un servidor de base de datos mariadb en el puerto 3306, el archivo .env podría ser algo así:

```sh
SSH_HOST=192.168.1.76
SSH_PORT=2222
FLASK_SQLALCHEMY_DATABASE_URI=mysql+pymysql://myuser:mypassword@localhost:3306/mydatabase
FLASK_PORT=1512
FLASK_HOST=0.0.0.0
FLASK_SECRET_KEY=clave_secreta
ENABLE_LOGGING=true
LOG_LEVEL=DEBUG
DB_HOST=mariadb
DB_PORT=3306
```

Arrancar el contenedor con el siguiente comando:

```sh
docker run --rm -e SSH_PRIVATE_KEY="$SSH_PRIVATE_KEY" -e FIREBASE_CRED_JSON="$CRED" --env-file .env -p 1512:1512 toledo74/cambios
```

### Ejemplo de despliegue en google cloud

Google cloud utiliza un archivo .yml para almacenar las variables de entorno. Por ejemplo, un archivo env.yml podría ser algo así (nótese los \n en SSH_PRIVATE_KEY y FIREBASE_CRED_JSON):
```sh
SSH_HOST: mybastion.example.com
SSH_PRIVATE_KEY: "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAA....dRkAQ==\n-----END OPENSSH PRIVATE KEY-----"
FIREBASE_CRED_JSON: "ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOiAiYXRjYXBwLXdl\nYiIsCiAg....iCn0K"
FLASK_SQLALCHEMY_DATABASE_URI: mysql+pymysql://myuser:mypassword@localhost:3306/mydatabase
FLASK_PORT: 8080
FLASK_HOST: 0.0.0.0
```

Y arrancar 

```sh
gcloud run deploy my_gcr_service \
    --image docker.io/toledo74/cambios:latest \
    --platform managed \
    --region europe-west1 \
    --allow-unauthenticated \
    --env-vars-file env.yml
```


