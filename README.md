

# Gestión de Turnos para ATCS de Enaire

## Descripción
Este proyecto está diseñado para facilitar la gestión de turnos para los Controladores de Tránsito Aéreo (ATCS) de Enaire. Utiliza una aplicación Flask con una base de datos para almacenar y gestionar los turnos de los empleados, integrándose con Firebase para la autenticación y administración de usuarios.

## Características
- **Gestión de Turnos**: Registro y visualización de turnos asignados.
- **Autenticación**: Uso de Firebase Admin SDK para la verificación de usuarios.
- **Interfaz de Administración**: Integración con Flask-Admin para la gestión de datos.
- **Persistencia de Datos**: Soporte para bases de datos SQL, con opción para almacenar datos de forma persistente en servicios gestionados.

## Tecnologías Utilizadas
- **Flask**: Framework web para Python.
- **SQLAlchemy**: ORM para la gestión de la base de datos.
- **Firebase**: Servicios de autenticación y administración de usuarios.
- **Docker**: Contenerización de la aplicación para un despliegue flexible y escalable.

## Instalación y Configuración

### Clonar el Repositorio
```sh
git clone https://github.com/jtoledo1974/cambios.git
```

### Variables de entorno

Este proyecto utiliza el SDK de administración de Firebase para la autenticación y otros servicios de Firebase. El SDK se puede inicializar utilizando un archivo de credenciales o una cadena JSON pasada a través de variables de entorno, lo que lo hace flexible para diferentes entornos. Sólo se necesita una de las dos opciones para inicializar el SDK.

- `FIREBASE_CRED_FILE`: Ruta al archivo de credenciales de Firebase (el valor predeterminado es `cambios-firebase.json`).
- `FIREBASE_CRED_JSON`: Cadena JSON de las credenciales de Firebase.

Estas variables de entorno se utilizan para configurar la aplicación.

- `SQLALCHEMY_DATABASE_URI`: URI de la base de datos utilizada por SQLAlchemy. Si no se proporciona, se utilizará una base de datos SQLite por defecto.
- `SQLALCHEMY_TRACK_MODIFICATIONS`: Indica si se deben realizar seguimientos de modificaciones en la base de datos. Se recomienda desactivarlo en entornos de producción.
- `SECRET_KEY`: Clave secreta utilizada para la generación de tokens de seguridad. Si no se proporciona, se generará una clave aleatoria.
- `DEBUG`: Indica si el modo de depuración está habilitado. Se interpreta como verdadero si el valor es "true", "1" o "t" (ignorando mayúsculas y minúsculas).
- `HOST`: Dirección IP en la que se ejecutará la aplicación. Si no se proporciona, se utilizará localhost y no servirá clientes externos.
- `PORT`: Puerto en el que se ejecutará la aplicación. Si no se proporciona, se utilizará el puerto 80.
- `ENABLE_LOGGING`: Indica si se deben habilitar los registros de la aplicación en logs/

### Instalar imágenes precompiladas
```sh
docker run -d -p 80:80 toledo74/cambios
```

## Instrucciones para desarrolladores

### Crear un entorno virtual
```sh
python3 -m venv venv
source venv/bin/activate
```

### Instalar paquete y dependencias
```sh
pip install -e .[dev]
```
