# Proyecto de Chat Centralizado (Arquitectura Cliente-Servidor)

Este proyecto despliega un chat de arquitectura tradicional, en donde todos los clientes se conectan a un mismo servidor que centraliza los mensajes de WebSocket (generalmente a través de Redis y Django Channels).

## Instrucciones de uso

1. Ingresa a la carpeta del proyecto centralizado:
   ```bash
   cd centralizdo
   ```

2. Instala las dependencias necesarias:
   Es altamente recomendable crear un entorno virtual previamente.
   ```bash
   python -m venv .venv
   #source .venv/bin/activate  # Para Linux/macOS
   .venv\Scripts\activate   # Para Windows
   pip install -r requirements.txt
   ```

3. (Opcional) Realiza las migraciones de la base de datos si es la primera vez que lo corres:
   ```bash
   python manage.py migrate
   ```

4. Levanta el servidor de Django:
   ```bash
   python manage.py runserver
   ```
   Tu aplicación estará corriendo en `http://localhost:8000/`.
