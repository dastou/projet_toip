from rest_framework import serializers
from .models import Contact, ContactGroup
from users.serializers import UserSerializer
from django.utils import timezone
import humanize
from datetime import datetime


class ContactGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactGroup
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']


class ContactSerializer(serializers.ModelSerializer):
    contact_user_details = UserSerializer(source='contact_user', read_only=True)
    groups = ContactGroupSerializer(many=True, read_only=True)
    # New fields to match desired output format
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    online = serializers.SerializerMethodField()
    favorite = serializers.SerializerMethodField()
    lastContact = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = [
            'id', 'contact_user', 'contact_user_details', 'nickname',
            'groups', 'is_favorite', 'notes', 'created_at',
            # New fields for frontend
            'name', 'email', 'avatar', 'phone', 'online',
            'favorite', 'lastContact', 'tags'
        ]
        read_only_fields = ['id', 'created_at']

    def get_name(self, obj):
        """Return either nickname or full name from contact_user"""
        if obj.nickname:
            return obj.nickname

        user = obj.contact_user
        if user.first_name or user.last_name:
            return f"{user.first_name} {user.last_name}".strip()
        return user.username

    def get_email(self, obj):
        return obj.contact_user.email

    def get_avatar(self, obj):
        return obj.contact_user.profile_image.url if obj.contact_user.profile_image else ""

    def get_online(self, obj):
        return obj.online

    def get_favorite(self, obj):
        return obj.is_favorite

    def get_lastContact(self, obj):
        if not obj.last_contact:
            return ""

        # Format as "Yesterday, 2:15 PM" or similar
        now = timezone.now()
        if now.date() == obj.last_contact.date():
            return f"Today, {obj.last_contact.strftime('%I:%M %p')}"
        elif (now.date() - obj.last_contact.date()).days == 1:
            return f"Yesterday, {obj.last_contact.strftime('%I:%M %p')}"
        else:
            return obj.last_contact.strftime('%b %d, %I:%M %p')

    def get_tags(self, obj):
        return obj.tags