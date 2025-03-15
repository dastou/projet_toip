from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Call, CallParticipant, CallMessage
from .serializers import CallSerializer, CallParticipantSerializer, CallMessageSerializer
from users.models import User, UserStatus
from signaling.views import notify_incoming_call  # Nouvelle importation

class CallViewSet(viewsets.ModelViewSet):
    serializer_class = CallSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'scheduled_time', 'start_time']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        # Récupérer tous les appels où l'utilisateur est initiateur ou participant
        return Call.objects.filter(
            Q(initiator=user) | Q(participants=user)
        ).distinct()
    
    def create(self, request, *args, **kwargs):
        # Récupérer les participants de request.data
        participants = request.data.get('participants', [])
        
        print(f"Request data received: {request.data}")
        print(f"Participants extracted: {participants}")
        
        # Créer le serializer avec le contexte incluant les participants
        serializer = self.get_serializer(data=request.data, context={'participants': participants})
        
        if not serializer.is_valid():
            print(f"Serializer validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        
        # Après avoir créé l'appel, notifier tous les participants
        call = serializer.instance
        if call.status == 'in_progress':
            for participant_id in participants:
                # Notifier chaque participant via WebSocket
                notify_incoming_call(call, participant_id)
                print(f"Notification d'appel entrant envoyée à l'utilisateur {participant_id}")
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        # Plus besoin de gérer manuellement les participants ici
        # Le serializer s'en occupe dans sa méthode create()
        serializer.save(initiator=self.request.user)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        call = self.get_object()
        
        # Vérifier si l'utilisateur est l'initiateur ou un participant
        if call.initiator != request.user and not call.participants.filter(id=request.user.id).exists():
            return Response({"detail": "Vous n'êtes pas autorisé à démarrer cet appel."}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier si l'appel peut être démarré
        if call.status not in ['planned', 'cancelled']:
            return Response({"detail": f"L'appel ne peut pas être démarré car son statut est {call.status}."}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Démarrer l'appel
        call.status = 'in_progress'
        call.start_time = timezone.now()
        call.save()
        
        # Mettre à jour le statut de l'initiateur
        try:
            user_status = UserStatus.objects.get(user=request.user)
            user_status.is_in_call = True
            user_status.save()
        except UserStatus.DoesNotExist:
            pass
        
        # Si l'utilisateur est un participant, mettre à jour son statut
        participant = call.call_participants.filter(user=request.user).first()
        if participant:
            participant.joined_at = timezone.now()
            participant.has_accepted = True
            participant.save()
        
        # Notifier les participants que l'appel a commencé
        for participant in call.participants.all():
            if participant.id != request.user.id:
                notify_incoming_call(call, participant.id)
        
        serializer = self.get_serializer(call)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        call = self.get_object()
        
        # Vérifier si l'appel est en cours
        if call.status != 'in_progress':
            return Response({"detail": "L'appel n'est pas en cours."}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Terminer l'appel
        call.status = 'completed'
        call.end_time = timezone.now()
        call.save()
        
        # Mettre à jour le statut de tous les participants
        for participant in call.call_participants.filter(left_at__isnull=True):
            participant.left_at = timezone.now()
            participant.save()
            
            # Mettre à jour le statut WebRTC de l'utilisateur
            try:
                user_status = UserStatus.objects.get(user=participant.user)
                user_status.is_in_call = False
                user_status.save()
            except UserStatus.DoesNotExist:
                pass
        
        serializer = self.get_serializer(call)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        call = self.get_object()
        
        # Vérifier si l'appel est en cours
        if call.status != 'in_progress':
            return Response({"detail": "L'appel n'est pas en cours."}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier si l'utilisateur est un participant
        participant = call.call_participants.filter(user=request.user).first()
        if not participant:
            # Ajouter l'utilisateur comme participant si ce n'est pas déjà le cas
            participant = CallParticipant.objects.create(
                call=call,
                user=request.user,
                joined_at=timezone.now(),
                has_accepted=True
            )
        else:
            participant.joined_at = timezone.now()
            participant.has_accepted = True
            participant.left_at = None  # Réinitialiser si l'utilisateur rejoint à nouveau
            participant.save()
        
        # Mettre à jour le statut WebRTC de l'utilisateur
        try:
            user_status = UserStatus.objects.get(user=request.user)
            user_status.is_in_call = True
            user_status.save()
        except UserStatus.DoesNotExist:
            pass
        
        serializer = self.get_serializer(call)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        call = self.get_object()
        
        # Vérifier si l'appel est en cours
        if call.status != 'in_progress':
            return Response({"detail": "L'appel n'est pas en cours."}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        # Mettre à jour le statut du participant
        participant = call.call_participants.filter(user=request.user).first()
        if participant:
            participant.left_at = timezone.now()
            participant.save()
        
        # Mettre à jour le statut WebRTC de l'utilisateur
        try:
            user_status = UserStatus.objects.get(user=request.user)
            user_status.is_in_call = False
            user_status.save()
        except UserStatus.DoesNotExist:
            pass
        
        # Si tous les participants ont quitté, terminer l'appel
        if not call.call_participants.filter(left_at__isnull=True).exists():
            call.status = 'completed'
            call.end_time = timezone.now()
            call.save()
        
        serializer = self.get_serializer(call)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def scheduled(self, request):
        # Récupérer les appels planifiés à venir
        user = request.user
        now = timezone.now()
        scheduled_calls = Call.objects.filter(
            (Q(initiator=user) | Q(participants=user)),
            status='planned',
            scheduled_time__gt=now
        ).distinct().order_by('scheduled_time')
        
        serializer = self.get_serializer(scheduled_calls, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        # Récupérer l'historique des appels
        user = request.user
        completed_calls = Call.objects.filter(
            (Q(initiator=user) | Q(participants=user)),
            status__in=['completed', 'missed', 'cancelled']
        ).distinct().order_by('-end_time')
        
        serializer = self.get_serializer(completed_calls, many=True)
        return Response(serializer.data)
    
    # Cette action est commentée car nous utilisons WebSockets maintenant
    # @action(detail=False, methods=['get'])
    # def incoming(self, request):
    #     """Récupérer les appels entrants pour l'utilisateur actuel"""
    #     user = request.user
    #     
    #     # Trouver les appels en cours où l'utilisateur est participant mais n'a pas accepté
    #     incoming_calls = Call.objects.filter(
    #         participants=user,
    #         status='in_progress',
    #         call_participants__user=user,
    #         call_participants__has_accepted=False,
    #         call_participants__left_at__isnull=True
    #     ).distinct()
    #     
    #     serializer = self.get_serializer(incoming_calls, many=True)
    #     return Response(serializer.data)

class CallParticipantViewSet(viewsets.ModelViewSet):
    serializer_class = CallParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        call_id = self.kwargs.get('call_pk')
        if call_id:
            return CallParticipant.objects.filter(call_id=call_id)
        return CallParticipant.objects.none()
    
    def perform_create(self, serializer):
        call_id = self.kwargs.get('call_pk')
        call = get_object_or_404(Call, id=call_id)
        serializer.save(call=call)

class CallMessageViewSet(viewsets.ModelViewSet):
    serializer_class = CallMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        call_id = self.kwargs.get('call_pk')
        if call_id:
            return CallMessage.objects.filter(call_id=call_id).order_by('timestamp')
        return CallMessage.objects.none()
    
    def perform_create(self, serializer):
        call_id = self.kwargs.get('call_pk')
        call = get_object_or_404(Call, id=call_id)
        serializer.save(call=call, sender=self.request.user)