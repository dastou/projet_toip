from django.db import models
from users.models import User

class ContactGroup(models.Model):
    """Groupe de contacts pour organiser les contacts"""
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contact_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Contact(models.Model):
    """Contact dans le répertoire d'un utilisateur"""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    contact_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='is_contact_of')
    nickname = models.CharField(max_length=100, blank=True, null=True)
    groups = models.ManyToManyField(ContactGroup, blank=True, related_name='contacts')
    is_favorite = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Assurer qu'un utilisateur ne peut pas ajouter le même contact plusieurs fois
        unique_together = ('owner', 'contact_user')
    
    def __str__(self):
        nickname = self.nickname or self.contact_user.username
        return f"{self.owner.username}'s contact: {nickname}"