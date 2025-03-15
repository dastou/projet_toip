import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import SignalingMessage
from calls.models import Call

User = get_user_model()

class SignalingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.call_id = self.scope['url_route']['kwargs']['call_id']
        self.room_group_name = f'call_{self.call_id}'
        
        # Vérifier si l'utilisateur est authentifié
        if not self.scope['user'].is_authenticated:
            print(f"WebSocket - Refus de connexion: utilisateur non authentifié")
            await self.close()
            return
        
        # Vérifier si l'utilisateur fait partie de l'appel
        is_participant = await self.is_participant()
        if not is_participant:
            print(f"WebSocket - Refus de connexion: l'utilisateur {self.scope['user'].username} n'est pas participant à l'appel {self.call_id}")
            await self.close()
            return
        
        # Rejoindre le groupe d'appel
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        print(f"WebSocket - Connexion acceptée: utilisateur {self.scope['user'].username} pour l'appel {self.call_id}")
        await self.accept()
    
    async def disconnect(self, close_code):
        # Quitter le groupe d'appel
        print(f"WebSocket - Déconnexion: utilisateur {self.scope['user'].username} de l'appel {self.call_id}, code {close_code}")
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        print(f"WebSocket - Message reçu: type={message_type} de {self.scope['user'].username} pour l'appel {self.call_id}")
        
        # Stocker le message dans la base de données
        await self.save_signaling_message(data)
        
        # Envoyer le message au groupe (tous les participants de l'appel)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'signaling_message',
                'message': data,
                'sender_id': self.scope['user'].id
            }
        )
    
    async def signaling_message(self, event):
        message = event['message']
        sender_id = event['sender_id']
        
        # Ne pas renvoyer le message à l'expéditeur, seulement au destinataire
        if message.get('receiver') == self.scope['user'].id and sender_id != self.scope['user'].id:
            print(f"WebSocket - Transmission du message: type={message.get('type')} à {self.scope['user'].username}")
            await self.send(text_data=json.dumps(message))
    
    @database_sync_to_async
    def is_participant(self):
        try:
            call = Call.objects.get(id=self.call_id)
            user = self.scope['user']
            
            # Vérifier si l'utilisateur est l'initiateur ou un participant
            if call.initiator == user:
                return True
            
            return call.participants.filter(id=user.id).exists()
        except Call.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_signaling_message(self, data):
        message_type = data.get('type')
        receiver_id = data.get('receiver')
        content = {}
        
        # Stocker le contenu spécifique selon le type de message
        if message_type == 'offer' or message_type == 'answer':
            content = {'sdp': data.get('sdp', {})}
        elif message_type == 'ice-candidate':
            content = {'candidate': data.get('candidate', {})}
        else:
            content = data
        
        # Créer le message de signalisation
        SignalingMessage.objects.create(
            call_id=self.call_id,
            sender=self.scope['user'],
            receiver_id=receiver_id,
            message_type=message_type,
            content=content
        )

class IncomingCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Vérifier l'authentification
        if not self.scope['user'].is_authenticated:
            print(f"WebSocket IncomingCall - Refus de connexion: utilisateur non authentifié")
            await self.close()
            return
        
        # Groupe personnel pour l'utilisateur
        self.user_group = f'user_{self.scope["user"].id}'
        
        print(f"WebSocket IncomingCall - Connexion acceptée: utilisateur {self.scope['user'].username}")
        
        await self.channel_layer.group_add(
            self.user_group,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        print(f"WebSocket IncomingCall - Déconnexion: utilisateur {self.scope['user'].username}, code {close_code}")
        
        await self.channel_layer.group_discard(
            self.user_group,
            self.channel_name
        )
    
    async def incoming_call(self, event):
        print(f"WebSocket IncomingCall - Notification d'appel entrant à {self.scope['user'].username}: appel_id={event['call']['id']}")
        
        await self.send(text_data=json.dumps({
            'type': 'incoming_call',
            'call': event['call']
        }))