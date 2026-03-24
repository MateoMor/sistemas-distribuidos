# Sistemas Distribuidos - Chat Websockets

Este repositorio contiene las soluciones para el laboratorio de Sistemas Distribuidos, implementando chat en tiempo real utilizando WebSockets en Django. El repositorio cuenta con dos proyectos distintos implementados de forma independiente.

A continuación, puedes consultar la lógica y las instrucciones de ejecución específicas en los siguientes enlaces (o entrando directamente a cada carpeta y leyendo el `README.md` interno):

1. **[Chat Centralizado](./centralizdo/README.md)** (`centralizdo/`)
   - Arquitectura tradicional cliente-servidor.
   - Centraliza los mensajes de WebSocket (generalmente usando Redis).

2. **[Chat Peer-to-Peer (P2P)](./p2p_project/README.md)** (`p2p_project/`)
   - Arquitectura distribuida P2P.
   - Red de nodos interconectados con su propio servidor web y socket independiente.
