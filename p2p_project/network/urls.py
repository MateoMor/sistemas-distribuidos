from django.urls import path
from .views import (
    index,
    connect_peer,
    send_to,
    get_messages,
    get_nodes,
    send_webrtc_signal,
    get_webrtc_signals,
    send_typing_signal,
    get_typing_status,
)

urlpatterns = [
    path('', index),
    path('connect/', connect_peer),
    path('send/', send_to),
    path('messages/', get_messages),
    path('nodes/', get_nodes),
    path('webrtc/signal/', send_webrtc_signal),
    path('webrtc/signals/', get_webrtc_signals),
    path('typing/send/', send_typing_signal, name='typing_send'),
    path('typing/status/', get_typing_status, name='typing_status'),
]