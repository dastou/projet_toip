from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import SignalingMessage
from calls.models import Call
from calls.serializers import CallSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_offer(request):
    """Envoie une offre SDP à un autre utilisateur"""
    from .serializers import OfferSerializer  # Import local pour éviter les imports circulaires
    
    serializer = OfferSerializer(data=request.data)
    if serializer.is_valid():
        # Vérifier que l'appel existe et que l'utilisateur est autorisé
        call_id = serializer.validated_data['call']
        call = get_object_or_404(Call, id=call_id)
        
        # Vérifier que l'utilisateur est l'initiateur ou un participant
        user_id = request.user.id
        if call.initiator.id != user_id and not call.participants.filter(id=user_id).exists():
            return Response({"detail": "Vous n'êtes pas autorisé à envoyer des messages pour cet appel."}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier que le destinataire est un participant
        receiver_id = serializer.validated_data['receiver']
        if call.initiator.id != receiver_id and not call.participants.filter(id=receiver_id).exists():
            return Response({"detail": "Le destinataire n'est pas un participant de cet appel."}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Créer le message de signalisation
        message = SignalingMessage(
            call_id=call_id,
            sender_id=user_id,
            receiver_id=receiver_id,
            message_type='offer',
            content={'sdp': serializer.validated_data['sdp']}
        )
        message.save()
        
        return Response({"detail": "Offre envoyée avec succès."}, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_answer(request):
    """Envoie une réponse SDP à un autre utilisateur"""
    from .serializers import AnswerSerializer  # Import local
    
    serializer = AnswerSerializer(data=request.data)
    if serializer.is_valid():
        # Vérifier que l'appel existe et que l'utilisateur est autorisé
        call_id = serializer.validated_data['call']
        call = get_object_or_404(Call, id=call_id)
        
        # Vérifier que l'utilisateur est l'initiateur ou un participant
        user_id = request.user.id
        if call.initiator.id != user_id and not call.participants.filter(id=user_id).exists():
            return Response({"detail": "Vous n'êtes pas autorisé à envoyer des messages pour cet appel."}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier que le destinataire est un participant
        receiver_id = serializer.validated_data['receiver']
        if call.initiator.id != receiver_id and not call.participants.filter(id=receiver_id).exists():
            return Response({"detail": "Le destinataire n'est pas un participant de cet appel."}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Créer le message de signalisation
        message = SignalingMessage(
            call_id=call_id,
            sender_id=user_id,
            receiver_id=receiver_id,
            message_type='answer',
            content={'sdp': serializer.validated_data['sdp']}
        )
        message.save()
        
        return Response({"detail": "Réponse envoyée avec succès."}, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_ice_candidate(request):
    """Envoie un candidat ICE à un autre utilisateur"""
    from .serializers import IceCandidateSerializer  # Import local
    
    serializer = IceCandidateSerializer(data=request.data)
    if serializer.is_valid():
        # Vérifier que l'appel existe et que l'utilisateur est autorisé
        call_id = serializer.validated_data['call']
        call = get_object_or_404(Call, id=call_id)
        
        # Vérifier que l'utilisateur est l'initiateur ou un participant
        user_id = request.user.id
        if call.initiator.id != user_id and not call.participants.filter(id=user_id).exists():
            return Response({"detail": "Vous n'êtes pas autorisé à envoyer des messages pour cet appel."}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier que le destinataire est un participant
        receiver_id = serializer.validated_data['receiver']
        if call.initiator.id != receiver_id and not call.participants.filter(id=receiver_id).exists():
            return Response({"detail": "Le destinataire n'est pas un participant de cet appel."}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Créer le message de signalisation
        message = SignalingMessage(
            call_id=call_id,
            sender_id=user_id,
            receiver_id=receiver_id,
            message_type='ice-candidate',
            content={'candidate': serializer.validated_data['candidate']}
        )
        message.save()
        
        return Response({"detail": "Candidat ICE envoyé avec succès."}, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def poll_messages(request, call_id):
    """Récupère les messages de signalisation non traités destinés à l'utilisateur"""
    # Vérifier que l'appel existe et que l'utilisateur est autorisé
    call = get_object_or_404(Call, id=call_id)
    
    # Vérifier que l'utilisateur est l'initiateur ou un participant
    user_id = request.user.id
    if call.initiator.id != user_id and not call.participants.filter(id=user_id).exists():
        return Response({"detail": "Vous n'êtes pas autorisé à recevoir des messages pour cet appel."}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    # Récupérer les messages non traités destinés à l'utilisateur
    messages = SignalingMessage.objects.filter(
        call_id=call_id,
        receiver_id=user_id,
        is_processed=False
    )
    
    # Ajouter des logs
    print(f"User {user_id} polling for messages for call {call_id}")
    print(f"Found {messages.count()} unprocessed messages")
    
    # Formater les messages pour le client
    formatted_messages = []
    for msg in messages:
        message_data = {
            'type': msg.message_type,
            'sender': msg.sender_id,
            'receiver': msg.receiver_id,
            'callId': call_id
        }
        
        # Ajouter le contenu spécifique au type de message
        if msg.message_type == 'offer' or msg.message_type == 'answer':
            message_data['sdp'] = msg.content.get('sdp', {})
        elif msg.message_type == 'ice-candidate':
            message_data['candidate'] = msg.content.get('candidate', {})
        
        formatted_messages.append(message_data)
        
        # Marquer le message comme traité
        msg.is_processed = True
        msg.save()
    
    return Response(formatted_messages)

# Nouvelle fonction pour la notification WebSocket
def notify_incoming_call(call, user_id):
    """
    Notifie un utilisateur d'un appel entrant via WebSocket
    """
    channel_layer = get_channel_layer()
    
    # Sérialiser l'appel
    serializer = CallSerializer(call)
    
    try:
        async_to_sync(channel_layer.group_send)(
            f'user_{user_id}',
            {
                'type': 'incoming_call',
                'call': serializer.data
            }
        )
        print(f"Notification d'appel entrant envoyée à l'utilisateur {user_id}")
        return True
    except Exception as e:
        print(f"Erreur lors de la notification d'appel entrant: {e}")
        return False