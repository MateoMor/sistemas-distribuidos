# Proyecto de Chat P2P (Red de nodos interconectados)

Este proyecto simula un entorno Peer-to-Peer (P2P). Los nodos en la red deben ejecutarse individualmente con sus propios puertos para conectarse entre sí, manteniendo un servidor de WebSockets P2P separado del servidor web de Django de cada nodo.

## Instrucciones de uso para Windows (usando `set`)

Para probar la comunicación P2P es ideal contar con por lo menos 2 a 3 nodos. Debes abrir múltiples terminales (una para cada nodo).

1. Ingresa a la carpeta de este proyecto en una terminal:
   ```bash
   cd p2p_project
   ```

2. Instala las dependencias necesarias:
   Es muy recomendable utilizar un entorno virtual para correr el proyecto:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Para Linux/macOS
   # .venv\Scripts\activate   # Para Windows
   pip install -r requirements.txt
   ```

3. (Opcional) Realiza las migraciones:
   ```bash
   python manage.py migrate
   ```

4. **Inicia el Primer Nodo:**
   Se levantará en el entorno web en el puerto `8000` y expone el socket TCP P2P en el puerto `8767`.
   ```cmd
   set RUN_MAIN=true && set P2P_PORT=8767 && python manage.py runserver 8000
   ```

5. **Inicia el Segundo Nodo:**
   Abre una segunda terminal, navega a `p2p_project`, asegúrate de activar el entorno virtual, y ejecuta:
   ```cmd
   set RUN_MAIN=true && set P2P_PORT=8768 && python manage.py runserver 8001
   ```

6. **Inicia un Tercer Nodo (Opcional):**
   Abre otra terminal más en la misa ruta (activando el entorno) y ejecuta:
   ```cmd
   set RUN_MAIN=true && set P2P_PORT=8769 && python manage.py runserver 8002
   ```

## Instrucciones de uso para Linux / macOS

Si estás en un sistema basado en UNIX te recomendamos definir las variables de entorno de la siguiente manera (habiéndo activado antes el entorno `.venv`):

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

*(Alternativamente, puedes ejecutarlos en una sola línea como: `RUN_MAIN=true P2P_PORT=8767 python manage.py runserver 8000`)*

## Recomendaciones Generales P2P
- Verifica tener puertos disponibles en tu computadora.
- Cada instancia de Django debe de correr sobre un puerto distinto (8000, 8001, 8002...).
- Cada variable `P2P_PORT` debe reflejar un puerto TCP libre distinto (8767, 8768, 8769...).
