from django.db import models

class PrivateMessage(models.Model):
    """Modelo para almacenar mensajes privados entre usuarios."""
    sender = models.CharField(max_length=100)
    recipient = models.CharField(max_length=100)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['sender', 'recipient']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"{self.sender} -> {self.recipient}: {self.content[:50]}"
