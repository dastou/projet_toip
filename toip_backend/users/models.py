from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    Modèle utilisateur personnalisé avec des champs supplémentaires 
    pour les fonctionnalités VoIP
    """
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    online_status = models.BooleanField(default=False)
    last_seen = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
    
    def __str__(self):
        return self.username
        
class UserStatus(models.Model):
    """
    Modèle pour stocker le statut de connexion WebRTC et les métadonnées
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='webrtc_status')
    session_id = models.CharField(max_length=100, blank=True, null=True)
    is_in_call = models.BooleanField(default=False)
    device_info = models.JSONField(blank=True, null=True)
    last_ping = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {'In Call' if self.is_in_call else 'Available'}"