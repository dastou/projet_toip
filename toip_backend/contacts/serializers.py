from rest_framework import serializers
from .models import Contact, ContactGroup
from users.serializers import UserSerializer

class ContactGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactGroup
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']

class ContactSerializer(serializers.ModelSerializer):
    contact_user_details = UserSerializer(source='contact_user', read_only=True)
    groups = ContactGroupSerializer(many=True, read_only=True)
    
    class Meta:
        model = Contact
        fields = ['id', 'contact_user', 'contact_user_details', 'nickname', 
                  'groups', 'is_favorite', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']