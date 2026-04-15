import asyncio
import websockets
import json
import random
import socket
import ssl
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

BROADCAST_PORT = 1111  

class P2PNode:
    def __init__(self, host, port, peers=None):
        self.host = host
        self.port = port
        self.peers = peers if peers else []
        self.connections = {}
        self.connected_peers = set()
        real_ip = socket.gethostbyname(socket.gethostname())
        self.node_id = f"{real_ip}:{port}"
        self.known_nodes = {}
        self.peer_public_keys = {}
        self.messages = []
        self.webrtc_signals = []
        self.loop = None

        # Generar par de llaves RSA
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        self.public_key = self.private_key.public_key()
        self.public_key_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')

    def get_load(self):
        return random.randint(1, 100)

    async def handler(self, websocket):
        node_id = None
        try:
            async for message in websocket:
                data = json.loads(message)
                node_id = data.get("node_id")
                if node_id:
                    self.connections[node_id] = websocket
                await self.process_message(data)
        finally:
            if node_id and self.connections.get(node_id) is websocket:
                del self.connections[node_id]

    async def process_message(self, data):
        msg_type = data.get("type", "status")

        if msg_type == "status":
            node_id = data["node_id"]
            self.known_nodes[node_id] = data
            if "public_key" in data and node_id not in self.peer_public_keys:
                self.peer_public_keys[node_id] = serialization.load_pem_public_key(
                    data["public_key"].encode('utf-8')
                )

        elif msg_type == "chat":
            try:
                encrypted_bytes = base64.b64decode(data["text"])
                decrypted_text = self.private_key.decrypt(
                    encrypted_bytes,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                ).decode('utf-8')
            except Exception as e:
                decrypted_text = "[Error desencriptando mensaje]"

            self.messages.append({
                "from": data["from"],
                "to": self.node_id,     
                "text": decrypted_text,
                "direction": "received"
            })

        elif msg_type == "webrtc_signal":
            sender = data.get("from")
            signal_type = data.get("signal_type")
            signal_data = data.get("signal_data")
            if sender and signal_type and signal_data is not None:
                self.webrtc_signals.append({
                    "from": sender,
                    "to": self.node_id,
                    "signal_type": signal_type,
                    "signal_data": signal_data,
                })

    async def connect_to_new_peer(self, peer_url):
        if peer_url in self.connected_peers:
            return {"ok": True}

        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            ws = await websockets.connect(peer_url, ssl=ssl_context)
            # extraer node_id del URL: wss://host:port → host:port
            peer_id = peer_url.replace("wss://", "")
            self.connections[peer_id] = ws
            self.connected_peers.add(peer_url)
            self.peers.append(peer_url)
            asyncio.create_task(self.listen(ws, peer_id))
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def listen(self, websocket, peer_id):
        try:
            async for message in websocket:
                data = json.loads(message)
                await self.process_message(data)
        except:
            pass
        finally:
            # limpiar si se cae la conexión
            self.connections.pop(peer_id, None)
            ws_url = f"wss://{peer_id}"
            self.connected_peers.discard(ws_url)
            self.known_nodes.pop(peer_id, None)

    async def send_to(self, target_node_id, text):
        ws = self.connections.get(target_node_id)

        if not ws:
            # intentar conectar primero
            ws_url = f"wss://{target_node_id}"
            result = await self.connect_to_new_peer(ws_url)
            if not result["ok"]:
                return {"ok": False, "error": f"Nodo {target_node_id} no disponible"}
            ws = self.connections.get(target_node_id)

        target_pub_key = self.peer_public_keys.get(target_node_id)
        if not target_pub_key:
            return {"ok": False, "error": "Llave pública del nodo no encontrada. Espera a que anuncie su estado."}

        try:
            encrypted_bytes = target_pub_key.encrypt(
                text.encode('utf-8'),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            encrypted_text_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')

            message = json.dumps({
                "type": "chat",
                "from": self.node_id,
                "to": target_node_id,
                "text": encrypted_text_b64
            })
            await ws.send(message)
            self.messages.append({
                "from": self.node_id,
                "to": target_node_id,
                "text": text,
                "direction": "sent"
            })
            return {"ok": True}
        except Exception as e:
            # nodo caído: limpiar y notificar
            self.connections.pop(target_node_id, None)
            self.connected_peers.discard(f"wss://{target_node_id}")
            self.known_nodes.pop(target_node_id, None)
            return {"ok": False, "error": f"Nodo {target_node_id} caído, mensaje descartado"}

    async def send_webrtc_signal(self, target_node_id, signal_type, signal_data):
        ws = self.connections.get(target_node_id)

        if not ws:
            ws_url = f"wss://{target_node_id}"
            result = await self.connect_to_new_peer(ws_url)
            if not result["ok"]:
                return {"ok": False, "error": f"Nodo {target_node_id} no disponible"}
            ws = self.connections.get(target_node_id)

        try:
            message = json.dumps({
                "type": "webrtc_signal",
                "from": self.node_id,
                "to": target_node_id,
                "signal_type": signal_type,
                "signal_data": signal_data,
            })
            await ws.send(message)
            return {"ok": True}
        except Exception:
            self.connections.pop(target_node_id, None)
            self.connected_peers.discard(f"wss://{target_node_id}")
            self.known_nodes.pop(target_node_id, None)
            return {"ok": False, "error": f"Nodo {target_node_id} caído, señal descartada"}


    async def send_status(self):
        while True:
            message = json.dumps({
                "type": "status",
                "node_id": self.node_id,
                "load": self.get_load(),
                "hostname": socket.gethostname(),
                "ws_url": f"wss://{self.node_id}",
                "public_key": self.public_key_pem
            })
            dead = []
            for nid, ws in list(self.connections.items()):
                try:
                    await ws.send(message)
                except:
                    dead.append(nid)
            for nid in dead:
                self.connections.pop(nid, None)
                self.known_nodes.pop(nid, None)
            await asyncio.sleep(2)

    async def udp_broadcast(self):
        """Anuncia este nodo en la red local cada 3 segundos vía UDP."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setblocking(False)

        payload = json.dumps({
            "type": "discovery",
            "node_id": self.node_id,
            "ws_url": f"wss://{self.node_id}",
            "hostname": socket.gethostname(),
            "public_key": self.public_key_pem
        }).encode()

        loop = asyncio.get_event_loop()
        while True:
            try:
                await loop.run_in_executor(
                    None,
                    lambda: sock.sendto(payload, ("<broadcast>", BROADCAST_PORT))
                )
            except:
                pass
            await asyncio.sleep(3)

    async def udp_listener(self):
        """Escucha broadcasts UDP de otros nodos y los registra."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", BROADCAST_PORT))
        sock.setblocking(False)

        loop = asyncio.get_event_loop()
        while True:
            try:
                data, addr = await loop.run_in_executor(None, lambda: sock.recvfrom(1024))
                msg = json.loads(data.decode())

                if msg.get("type") == "discovery":
                    node_id = msg["node_id"]
                    if node_id != self.node_id:  
                        self.known_nodes[node_id] = {
                            "node_id": node_id,
                            "ws_url": msg["ws_url"],
                            "hostname": msg["hostname"],
                            "load": "?",
                            "discovered_via": "udp"
                        }
                        if "public_key" in msg and node_id not in self.peer_public_keys:
                            self.peer_public_keys[node_id] = serialization.load_pem_public_key(
                                msg["public_key"].encode('utf-8')
                            )
            except:
                await asyncio.sleep(0.1)


    async def connect_to_peers(self):
        for peer in self.peers:
            await self.connect_to_new_peer(peer)

    async def start(self):
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain("cert.pem", "key.pem")

        server = await websockets.serve(self.handler, self.host, self.port, ssl=ssl_context)
        await self.connect_to_peers()
        await asyncio.gather(
            self.send_status(),
            self.udp_broadcast(),
            self.udp_listener(),
            server.wait_closed()
        )