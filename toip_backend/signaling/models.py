from django.db import models
from users.models import User
from calls.models import Call

class SignalingMessage(models.Model):
    MESSAGE_TYPES = (
        ('offer', 'Offer'),
        ('answer', 'Answer'),
        ('ice-candidate', 'ICE Candidate'),
    )
    
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name='signaling_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES)
    content = models.JSONField()  # Contient le SDP ou le candidat ICE
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.message_type} from {self.sender.username} to {self.receiver.username}"