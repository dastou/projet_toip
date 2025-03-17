from django.db import models
from users.models import User
from django.utils import timezone


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
    # New fields
    phone = models.CharField(max_length=20, blank=True, null=True)
    last_contact = models.DateTimeField(blank=True, null=True)

    class Meta:
        # Assurer qu'un utilisateur ne peut pas ajouter le même contact plusieurs fois
        unique_together = ('owner', 'contact_user')

    def __str__(self):
        nickname = self.nickname or self.contact_user.username
        return f"{self.owner.username}'s contact: {nickname}"

    @property
    def online(self):
        """Return online status from the contact_user"""
        return self.contact_user.online_status if hasattr(self.contact_user, 'online_status') else False

    @property
    def tags(self):
        """Return group names as tags"""
        return [group.name for group in self.groups.all()]