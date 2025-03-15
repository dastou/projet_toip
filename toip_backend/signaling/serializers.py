from rest_framework import serializers
from .models import SignalingMessage

class SignalingMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignalingMessage
        fields = ['id', 'call', 'sender', 'receiver', 'message_type', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']

class OfferSerializer(serializers.Serializer):
    callId = serializers.IntegerField(source='call')
    sender = serializers.IntegerField()
    receiver = serializers.IntegerField()
    sdp = serializers.JSONField()
    type = serializers.CharField()

class AnswerSerializer(serializers.Serializer):
    callId = serializers.IntegerField(source='call')
    sender = serializers.IntegerField()
    receiver = serializers.IntegerField()
    sdp = serializers.JSONField()
    type = serializers.CharField()

class IceCandidateSerializer(serializers.Serializer):
    callId = serializers.IntegerField(source='call')
    sender = serializers.IntegerField()
    receiver = serializers.IntegerField()
    candidate = serializers.JSONField()
    type = serializers.CharField()