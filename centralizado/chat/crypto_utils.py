"""
Utilidades criptográficas para el chat centralizado.
Maneja el par de llaves RSA del servidor y las operaciones de cifrado/descifrado.
"""

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
import base64

# Par de llaves del servidor — se generan una vez al arrancar
server_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)
server_public_key = server_private_key.public_key()
server_public_key_pem = server_public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')


def decrypt_with_server_key(encrypted_b64: str) -> str:
    """Descifra un mensaje cifrado con la llave pública del servidor."""
    encrypted_bytes = base64.b64decode(encrypted_b64)
    return server_private_key.decrypt(
        encrypted_bytes,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    ).decode('utf-8')


def encrypt_with_public_key(public_key_pem: str, text: str) -> str:
    """Cifra un mensaje con la llave pública de un cliente."""
    pub_key = serialization.load_pem_public_key(public_key_pem.encode())
    encrypted = pub_key.encrypt(
        text.encode('utf-8'),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(encrypted).decode('utf-8')