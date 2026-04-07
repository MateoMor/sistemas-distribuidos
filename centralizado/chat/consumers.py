"""
Consumer WebSocket para el chat.
Maneja conexiones, desconexiones, broadcast de mensajes globales y privados.
Incluye defensas: anti-spoofing, XSS, rate limiting, validación de flujo.
Incluye cifrado RSA: servidor descifra y re-encripta para cada destinatario.
"""

import json
import re
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.html import escape
from .models import PrivateMessage
from .crypto_utils import (
    server_public_key_pem,
    decrypt_with_server_key,
    encrypt_with_public_key,
)


# Registro global de usuarios conectados: {channel_name: username}
connected_users = {}
# Mapeo de username a channel_name para mensajes privados: {username: channel_name}
user_channels = {}
# Llaves públicas de cada cliente: {username: public_key_pem}
client_public_keys = {}

# Nombres reservados que no se pueden usar
RESERVED_NAMES = {"admin", "sistema", "server", "bot", "anónimo", "anonimo"}


class ChatConsumer(AsyncWebsocketConsumer):
    """Consumer que maneja la sala de chat y mensajes privados."""

    ROOM_GROUP = "chat_room"

    # ── Rate limiting config ───────────────────────────────
    RATE_LIMIT = 10    # máx mensajes permitidos
    WINDOW_SECS = 5    # por ventana de tiempo (segundos)

    async def connect(self):
        """Se ejecuta cuando un cliente WebSocket se conecta."""
        self.message_count = 0
        self.window_start = datetime.now().timestamp()
        self.joined = False

        await self.channel_layer.group_add(self.ROOM_GROUP, self.channel_name)
        await self.accept()

        # Mandar llave pública del servidor al cliente recién conectado
        await self.send(text_data=json.dumps({
            "type": "server_public_key",
            "public_key": server_public_key_pem
        }))

    async def disconnect(self, close_code):
        """Se ejecuta cuando un cliente WebSocket se desconecta."""
        username = connected_users.pop(self.channel_name, None)
        if username:
            user_channels.pop(username, None)
            client_public_keys.pop(username, None)

        await self.channel_layer.group_discard(self.ROOM_GROUP, self.channel_name)

        if username:
            await self.channel_layer.group_send(
                self.ROOM_GROUP,
                {
                    "type": "system_message",
                    "content": f"🔴 {username} ha abandonado el chat",
                    "timestamp": self._timestamp(),
                },
            )
            await self._broadcast_user_list()

    async def receive(self, text_data):
        """Se ejecuta cuando se recibe un mensaje del cliente."""
        # ── Defensa 1: Rate limiting ───────────────────────
        if self._check_rate_limit():
            await self.send(text_data=json.dumps({
                "type": "error",
                "content": "⚠️ Demasiados mensajes. Espera un momento.",
                "timestamp": self._timestamp(),
            }))
            return

        # ── Parsear JSON ───────────────────────────────────
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")

        # ── Defensa 2: Forzar flujo de join ───────────────
        if msg_type != "join" and not self.joined:
            await self.send(text_data=json.dumps({
                "type": "error",
                "content": "⚠️ Debes unirte al chat primero.",
                "timestamp": self._timestamp(),
            }))
            await self.close(code=4001)
            return

        if msg_type == "join":
            await self._handle_join(data)
        elif msg_type == "message":
            await self._handle_message(data)
        elif msg_type == "private_message":
            await self._handle_private_message(data)

    # ── Handlers de tipo de mensaje ────────────────────────

    async def _handle_join(self, data):
        """Procesa la solicitud de unirse al chat con validaciones."""
        username = data.get("username", "").strip()

        # ── Defensa 3: Validación de username ─────────────
        if not username or len(username) < 2 or len(username) > 20:
            await self.send(text_data=json.dumps({
                "type": "error",
                "content": "⚠️ El nombre debe tener entre 2 y 20 caracteres.",
                "timestamp": self._timestamp(),
            }))
            await self.close(code=4002)
            return

        if not re.match(r'^[\w\-]+$', username):
            await self.send(text_data=json.dumps({
                "type": "error",
                "content": "⚠️ El nombre solo puede contener letras, números, - y _",
                "timestamp": self._timestamp(),
            }))
            await self.close(code=4002)
            return

        if username.lower() in RESERVED_NAMES:
            await self.send(text_data=json.dumps({
                "type": "error",
                "content": "⚠️ Ese nombre está reservado.",
                "timestamp": self._timestamp(),
            }))
            await self.close(code=4002)
            return

        if username in user_channels:
            await self.send(text_data=json.dumps({
                "type": "error",
                "content": "⚠️ Ese nombre ya está en uso. Elige otro.",
                "timestamp": self._timestamp(),
            }))
            await self.close(code=4002)
            return

        # Guardar llave pública del cliente
        client_pub_key = data.get("public_key")
        if client_pub_key:
            client_public_keys[username] = client_pub_key

        # Registrar usuario
        connected_users[self.channel_name] = username
        user_channels[username] = self.channel_name
        self.joined = True

        await self.send(text_data=json.dumps({
            "type": "system",
            "content": f"¡Bienvenido al chat, {username}!",
            "timestamp": self._timestamp(),
        }))

        await self.channel_layer.group_send(
            self.ROOM_GROUP,
            {
                "type": "system_message",
                "content": f"🟢 {username} se ha unido al chat",
                "timestamp": self._timestamp(),
            },
        )
        await self._broadcast_user_list()

    async def _handle_message(self, data):
        """Procesa un mensaje global — descifra y re-encripta para cada usuario."""
        username = connected_users.get(self.channel_name, "???")

        # Descifrar mensaje con llave privada del servidor
        try:
            encrypted_content = data.get("content", "")
            content = decrypt_with_server_key(encrypted_content)
            content = escape(content.strip())
        except Exception:
            return

        if not content or len(content) > 500:
            return

        timestamp = self._timestamp()

        # Re-cifrar individualmente para cada cliente conectado
        for recipient_username, recipient_channel in list(user_channels.items()):
            recipient_pub_key = client_public_keys.get(recipient_username)
            if not recipient_pub_key:
                continue
            try:
                encrypted_for_recipient = encrypt_with_public_key(recipient_pub_key, content)
                await self.channel_layer.send(
                    recipient_channel,
                    {
                        "type": "chat_message",
                        "username": username,
                        "content": encrypted_for_recipient,
                        "timestamp": timestamp,
                        "sender_channel": self.channel_name,
                    }
                )
            except Exception:
                continue

    async def _handle_private_message(self, data):
        """Procesa un mensaje privado — descifra y re-encripta para el destinatario."""
        sender = connected_users.get(self.channel_name, "???")
        recipient = escape(data.get("recipient", "").strip())

        # Descifrar con llave privada del servidor
        try:
            encrypted_content = data.get("content", "")
            content = decrypt_with_server_key(encrypted_content)
            content = escape(content.strip())
        except Exception:
            return

        if not content or len(content) > 500 or not recipient:
            return

        if recipient == sender:
            await self.send(text_data=json.dumps({
                "type": "error",
                "content": "⚠️ No puedes enviarte mensajes a ti mismo.",
                "timestamp": self._timestamp(),
            }))
            return

        await self._save_private_message(sender, recipient, content)

        if recipient in user_channels:
            recipient_channel = user_channels[recipient]
            recipient_pub_key = client_public_keys.get(recipient)

            if recipient_pub_key:
                try:
                    encrypted_for_recipient = encrypt_with_public_key(recipient_pub_key, content)
                    await self.channel_layer.send(
                        recipient_channel,
                        {
                            "type": "private_message",
                            "sender": sender,
                            "content": encrypted_for_recipient,
                            "timestamp": self._timestamp(),
                        },
                    )
                except Exception:
                    pass

            # Confirmar al remitente con texto plano (es su propio mensaje)
            await self.send(text_data=json.dumps({
                "type": "private_message_sent",
                "recipient": recipient,
                "content": content,
                "timestamp": self._timestamp(),
            }))
        else:
            await self.send(text_data=json.dumps({
                "type": "system",
                "content": f"❌ {recipient} no está en línea",
                "timestamp": self._timestamp(),
            }))

    # ── Handlers de grupo ──────────────────────────────────

    async def chat_message(self, event):
        """Envía un mensaje de chat a este cliente."""
        await self.send(text_data=json.dumps({
            "type": "message",
            "username": event["username"],
            "content": event["content"],
            "timestamp": event["timestamp"],
            "is_own": event["sender_channel"] == self.channel_name,
        }))

    async def private_message(self, event):
        """Envía un mensaje privado a este cliente."""
        await self.send(text_data=json.dumps({
            "type": "private_message",
            "sender": event["sender"],
            "content": event["content"],
            "timestamp": event["timestamp"],
        }))

    async def system_message(self, event):
        """Envía un mensaje de sistema a este cliente."""
        await self.send(text_data=json.dumps({
            "type": "system",
            "content": event["content"],
            "timestamp": event["timestamp"],
        }))

    async def user_list_update(self, event):
        """Envía la lista actualizada de usuarios."""
        await self.send(text_data=json.dumps({
            "type": "user_list",
            "users": event["users"],
        }))

    # ── Utilidades ─────────────────────────────────────────

    def _check_rate_limit(self):
        """Retorna True si el usuario excedió el límite de mensajes."""
        now = datetime.now().timestamp()
        if now - self.window_start > self.WINDOW_SECS:
            self.message_count = 0
            self.window_start = now
        self.message_count += 1
        return self.message_count > self.RATE_LIMIT

    async def _broadcast_user_list(self):
        """Envía la lista de usuarios a todo el grupo."""
        users = list(connected_users.values())
        await self.channel_layer.group_send(
            self.ROOM_GROUP,
            {
                "type": "user_list_update",
                "users": users,
            },
        )

    async def _save_private_message(self, sender, recipient, content):
        """Guarda un mensaje privado en la BD de forma asíncrona."""
        from channels.db import database_sync_to_async

        @database_sync_to_async
        def save_msg():
            return PrivateMessage.objects.create(
                sender=sender,
                recipient=recipient,
                content=content,
            )

        await save_msg()

    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%H:%M:%S")