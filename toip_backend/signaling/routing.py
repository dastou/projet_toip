from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/signaling/(?P<call_id>\w+)/$', consumers.SignalingConsumer.as_asgi()),
    re_path(r'ws/incoming-calls/$', consumers.IncomingCallConsumer.as_asgi()),
]