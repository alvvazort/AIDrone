# AIDrone
Modelos de inteligencia artificial para resolver tareas con drones.

## Guía de instalación

### Prerrequisitos

- Ubuntu 18.04 LTS o Ubuntu 20.04 LTS
- GitHub

### Instalación PX4 con JMAVSim y Gazebo

Para ello hay que clonar el Firmware de PX4 e instalarlo.

`git clone https://github.com/PX4/Firmware.git --recursive`

Cambiamos a la carpeta Firmware e instalamos.

`cd Firmware
bash ./Tools/setup/ubuntu.sh`

Deberemos reiniciar para que se apliquen los cambios correctamente:

`sudo reboot now`

Una vez reiniciado volveremos a una terminal dentro de la carpeta Firmware y ejecutaremos lo siguiente:

`make px4_sitl gazebo`

Con ello se compilará el entorno y una vez terminado se iniciará la interfaz de Gazebo con el drone funcionando, en la terminal podremos utilizar comandos de vuelo como `commander takeoff` y `commander land` para comprobar que funciona todo correctamente. Para ejecutar este entorno de nuevo utilizaremos `make px4_sitl gazebo`, como ya estará compilado no habrá que esperar tanto tiempo como la primera vez.

### Instalación MAVSDK

Instalamos con pip MAVSDK y clonamos su repositorio.

`pip3 install mavsdk
cd ~/ # To download the repository in your home directory
git clone https://github.com/mavlink/MAVSDK-Python.git`

### Instalación QGroundControl

Primero ejecutamos esto en una terminal:

`sudo usermod -a -G dialout $USER
sudo apt-get remove modemmanager -y
sudo apt install gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl -y
sudo apt install libqt5gui5 -y
sudo apt install libfuse2 -y`

Descargar el archivo en el siguiente enlace: https://d176tv9ibo4jno.cloudfront.net/latest/QGroundControl.AppImage

Por último deberemos darle permisos de escritura, para ello podemos ejecutar el siguiente comando:

`chmod +x ./QGroundControl.AppImage`

## Como usar el entorno

Por un lado, deberemos tener una terminal en la que ejecutemos `make px4_sitl gazebo`. Esto iniciará el drone en Gazebo, por otro lado, ejecutaremos el archivo de QGroundControl, el cual nos desplegará una interfaz con el mapa en la posición en la que se encuentre el drone. Por último, ejecutaremos un archivo .py de este repositorio que ejecute un modelo de IA para realizar una tarea.
