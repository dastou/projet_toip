from django.urls import path
from . import views

urlpatterns = [
    path('offer/', views.send_offer, name='send-offer'),
    path('answer/', views.send_answer, name='send-answer'),
    path('ice-candidate/', views.send_ice_candidate, name='send-ice-candidate'),
    path('poll/<int:call_id>/', views.poll_messages, name='poll-messages'),
]