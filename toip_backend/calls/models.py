from django.db import models
from users.models import User

class Call(models.Model):
    """Modèle d'appel individuel ou de groupe"""
    CALL_TYPES = (
        ('audio', 'Audio Call'),
        ('video', 'Video Call'),
    )
    CALL_STATUS = (
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('cancelled', 'Cancelled'),
    )
    
    initiator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_calls')
    participants = models.ManyToManyField(User, related_name='participated_calls', through='CallParticipant')
    call_type = models.CharField(max_length=10, choices=CALL_TYPES)
    is_group_call = models.BooleanField(default=False)
    title = models.CharField(max_length=255, blank=True, null=True)  # Pour les appels de groupe
    status = models.CharField(max_length=20, choices=CALL_STATUS, default='planned')
    scheduled_time = models.DateTimeField(blank=True, null=True)  # Pour les appels planifiés
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    recording_path = models.CharField(max_length=255, blank=True, null=True)  # Pour sauvegarder les enregistrements
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        call_type = "Group call" if self.is_group_call else "Call"
        title = self.title or f"{call_type} initiated by {self.initiator.username}"
        return title
    
    @property
    def duration(self):
        """Calcule la durée de l'appel en secondes"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

class CallParticipant(models.Model):
    """Modèle pour les participants à un appel"""
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='call_participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='call_participations')
    joined_at = models.DateTimeField(blank=True, null=True)
    left_at = models.DateTimeField(blank=True, null=True)
    has_accepted = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} in {self.call}"

class CallMessage(models.Model):
    """Messages échangés pendant un appel (chat pendant l'appel)"""
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_call_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Message from {self.sender.username} in {self.call}"