from rest_framework import serializers
from .models import Call, CallParticipant, CallMessage
from users.serializers import UserSerializer

class CallParticipantSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = CallParticipant
        fields = ['id', 'user', 'user_details', 'joined_at', 'left_at', 'has_accepted']
        read_only_fields = ['id', 'joined_at', 'left_at']

class CallMessageSerializer(serializers.ModelSerializer):
    sender_details = UserSerializer(source='sender', read_only=True)
    
    class Meta:
        model = CallMessage
        fields = ['id', 'sender', 'sender_details', 'content', 'timestamp']
        read_only_fields = ['id', 'timestamp']

class CallSerializer(serializers.ModelSerializer):
    initiator_details = UserSerializer(source='initiator', read_only=True)
    participants_details = CallParticipantSerializer(source='call_participants', many=True, read_only=True)
    messages = CallMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Call
        fields = ['id', 'initiator', 'initiator_details', 'participants_details', 
                  'call_type', 'is_group_call', 'title', 'status', 
                  'scheduled_time', 'start_time', 'end_time', 
                  'recording_path', 'created_at', 'updated_at', 'duration', 'messages']
        read_only_fields = ['id', 'created_at', 'updated_at', 'duration']

    def create(self, validated_data):
        participants_data = self.context.get('participants', [])
        call = Call.objects.create(**validated_data)
        print(f"Participants reçus dans le sérialiseur: {participants_data}")

        # Ajouter l'initiateur comme participant
        CallParticipant.objects.create(
            call=call,
            user=validated_data['initiator'],
            has_accepted=True
        )
        
        # Ajouter les autres participants
        for participant_id in participants_data:
            print(f"Tentative d'ajout du participant: {participant_id}")

            try:
                from users.models import User
                user = User.objects.get(id=participant_id)
                CallParticipant.objects.create(
                    call=call,
                    user=user,
                    has_accepted=False
                )
                print(f"Participant {user.username} ajouté avec succès à l'appel {call.id}")
            except User.DoesNotExist:
                pass
                
        return call