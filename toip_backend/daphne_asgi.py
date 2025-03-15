import os
import sys
import django

# Ajoutez le répertoire du projet à sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurez les paramètres Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'toip_backend.settings')
django.setup()

# Maintenant que Django est initialisé, importez les modules dépendants
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Importez middleware et routage seulement après initialisation
from signaling.middleware import TokenAuthMiddleware
from signaling.routing import websocket_urlpatterns

# Application ASGI
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenAuthMiddleware(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})