from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from . import views

router = DefaultRouter()
router.register(r'', views.CallViewSet, basename='call')

# Routeurs imbriqués pour les participants et les messages
call_router = routers.NestedSimpleRouter(router, r'', lookup='call')
call_router.register(r'participants', views.CallParticipantViewSet, basename='call-participant')
call_router.register(r'messages', views.CallMessageViewSet, basename='call-message')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(call_router.urls)),
]