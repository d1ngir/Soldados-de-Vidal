# Soldados-de-Vidal

Programa: Servidor

Autores: Bautista Hurtado Lázaro, Castro Franco José Emiliano, Pérez Flores Miguel Ángel


La aplicación desarrollada en este proyecto consiste en un servicio de mensajería donde tú y otros usuarios conectados al mismo servidor pueden charlar entre si, ya sea por mensaje directo, grupal, general o enterarse de noticias de un usuario en particular a través de un canal de difusión que maneje. Contarán con identificadores como nombre de usuario y foto de perfil seleccionable al iniciar sesión.

El sistema es compatible y se puede ejecutar en **Windows, Linux y macOS**. Solo necesitas tener instalado:
- Python 3.8 o superior.
- Paquete gráfico de Python para Tkinter.

**Si eres usuario de Linux/UBUNTU, asegúrate de tener instalado el paquete gráfico Tkinter**
Script para la instalación en terminal: "sudo apt install python3-tk"


Para conectarte como cliente para pruebas, sigue los siguientes pasos:

1. Crea una carpeta donde se encuentren los archivos "cliente.py" y la carpeta de avatares que descargaste al clonar este repositorio.
2. En la terminal del equipo, ubicado en el directorio donde guardaste los dos archivos (probablemente "cd desktop/"nombre de la carpeta que creaste" "), ejecuta el siguiente script: "python3 cliente.py"
3. Una vez desplegada la interfaz gráfica, piensa bien en un usuario y contraseña que recuerdes, pues serán los que utilizarás posteriormente para cada inicio de sesión **NOTA: En caso de olvidar tus credenciales, deberás crear otro usuario, pues no hay modo de recuperarlas...**. Introdúcelos en los campos solicitados y haz clic en "Registrarse".
4. Una vez registrado, con las mismas credenciales introducidas en los mismos dos campos, haz clic en "Iniciar sesión".
5. Procede a seleccionar tu ávatar en la sección de avatares que verás a continuación y entra.
6. ¡Socializa, por favor!


Si deseas levantar el servidor desde cero, también requerirás de un gestor de bases de datos de tu preferencia, utilizando forzosamente el motor de **SQLServer**
En ese caso, sigue los siguientes pasos antes de la conexión como cliente.

1. Despliega en tu gestor de bases de datos el script de la base del programa y ejecútalo.
2. Ejecuta el siguiente script en la terminal:
   "python3 servidor.py"
3. Procede con las instrucciones detalladas para la conexión como cliente...


