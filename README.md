# Sistemas Distribuidos - Chat Websockets

Este repositorio contiene las soluciones para el laboratorio de Sistemas Distribuidos, implementando chat en tiempo real utilizando WebSockets en Django. El repositorio cuenta con dos proyectos distintos:

1. **Chat Centralizado** (`centralizdo/`)
2. **Chat Peet-to-Peer (P2P)** (`p2p_project/`)

A continuación, se detallan las instrucciones necesarias para levantar ambos proyectos y ponerlos a funcionar.

---

## 1. Proyecto de Chat Centralizado (Arquitectura Cliente-Servidor)

Este proyecto despliega un chat de arquitectura tradicional, en donde todos los clientes se conectan a un mismo servidor que centraliza los mensajes de WebSocket (generalmente a través de Redis y Django Channels).

### Instrucciones de uso:

1. Ingresa a la carpeta del proyecto centralizado:
   ```bash
   cd centralizdo
   ```

2. (Opcional) Realiza las migraciones de la base de datos si es la primera vez que lo corres:
   ```bash
   python manage.py migrate
   ```

3. Levanta el servidor de Django:
   ```bash
   python manage.py runserver
   ```
   Tu aplicación estará corriendo en `http://localhost:8000/`.

---

## 2. Proyecto de Chat P2P (Red de nodos interconectados)

Este proyecto simula un entorno Peer-to-Peer (P2P). Los nodos en la red deben ejecutarse individualmente con sus propios puertos para conectarse entre sí, manteniendo un servidor de WebSockets P2P separado del servidor web de Django de cada nodo.

### Instrucciones de uso para Windows (usando `set`):

Para probar la comunicación P2P es ideal contar con por lo menos 2 a 3 nodos. Debes abrir múltiples terminales (una para cada nodo).

1. Ingresa a la carpeta de este proyecto en una terminal:
   ```bash
   cd p2p_project
   ```

2. (Opcional) Realiza las migraciones:
   ```bash
   python manage.py migrate
   ```

3. **Inicia el Primer Nodo:**
   Se levantará en el entorno web en el puerto `8000` y expone el socket TCP P2P en el puerto `8767`.
   ```cmd
   set RUN_MAIN=true && set P2P_PORT=8767 && python manage.py runserver 8000
   ```

4. **Inicia el Segundo Nodo:**
   Abre una segunda terminal, navega a `p2p_project` y ejecuta:
   ```cmd
   set RUN_MAIN=true && set P2P_PORT=8768 && python manage.py runserver 8001
   ```

5. **Inicia un Tercer Nodo (Opcional):**
   Abre otra terminal más en la misa ruta y ejecuta:
   ```cmd
   set RUN_MAIN=true && set P2P_PORT=8769 && python manage.py runserver 8002
   ```

### Instrucciones de uso para Linux / macOS (usando `export` u variables inline):

Si estás en un sistema basado en UNIX te recomendamos definir las variables de entorno de la siguiente manera:

- **Nodo 1:**
  ```bash
  export RUN_MAIN=true
  export P2P_PORT=8767
  python manage.py runserver 8000
  ```
- **Nodo 2:**
  ```bash
  export RUN_MAIN=true
  export P2P_PORT=8768
  python manage.py runserver 8001
  ```

### Recomendaciones Generales P2P:
- Verifica tener puertos disponibles en tu computadora.
- Cada instancia de Django debe de correr sobre un puerto distinto (8000, 8001, 8002...).
- Cada variable `P2P_PORT` debe reflejar un puerto TCP libre distinto (8767, 8768, 8769...).
