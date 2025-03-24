import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import SignalingMessage
from calls.models import Call
import logging

# Utiliser deux loggers distincts
logger = logging.getLogger('signaling')
ws_logger = logging.getLogger('websocket')


User = get_user_model()

class SignalingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.call_id = self.scope['url_route']['kwargs']['call_id']
        self.room_group_name = f'call_{self.call_id}'
        self.username = self.scope['user'].username if self.scope['user'].is_authenticated else "Anonymous"

        if not self.scope['user'].is_authenticated:
            ws_logger.warning(f"Connexion refusée - utilisateur non authentifié - call_id={self.call_id}")
            await self.close(code=4003)
            return

        is_participant = await self.is_participant()
        if not is_participant:
            ws_logger.warning(
                f"Refus connexion: {self.username} non participant - call_id={self.call_id}")
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        ws_logger.info(f"Connexion acceptée: {self.username} - call_id={self.call_id}")
        await self.accept()

    async def disconnect(self, close_code):
        # Quitter le groupe d'appel
        ws_logger.info(f"Déconnexion: {self.username} - call_id={self.call_id} - code={close_code}")
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return  # Ignorer les messages binaires pour l'instant

        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if ws_logger.isEnabledFor(logging.DEBUG):
                ws_logger.debug(
                    f"Message reçu: {message_type} de {self.username} - call_id={self.call_id}")
            else:
                ws_logger.info(f"Message {message_type} reçu - call_id={self.call_id}")

            await self.save_signaling_message(data)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'signaling_message',
                    'message': data,
                    'sender_id': self.scope['user'].id
                }
            )
        except json.JSONDecodeError:
            ws_logger.error(f"Erreur JSON invalide - call_id={self.call_id}")
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Format JSON invalide'}))


    async def signaling_message(self, event):
        message = event['message']
        sender_id = event['sender_id']

        # Don't send the message back to the original sender
        if sender_id != self.scope['user'].id:
            # If there's a specific receiver, only send to them
            if 'receiver' in message and message['receiver'] is not None:
                # Convert to integer if needed for comparison
                receiver_id = int(message['receiver']) if isinstance(message['receiver'], str) else message['receiver']
                user_id = self.scope['user'].id

                if receiver_id == user_id:
                    logger.info(
                        f"WebSocket - Sending {message.get('type')} message to specific receiver: {self.scope['user'].username}")
                    await self.send(text_data=json.dumps(message))
            else:
                # If no specific receiver, broadcast to all in the room except sender
                logger.info(f"WebSocket - Broadcasting {message.get('type')} message to {self.scope['user'].username}")
                await self.send(text_data=json.dumps(message))


    @database_sync_to_async
    def is_participant(self):
        try:
            call = Call.objects.get(id=self.call_id)
            user = self.scope['user']
            user_id = user.id
            participants = call.participants.all()
            print(f"Participants: {[(p.id, p.username) for p in participants]}")

            print(f"Vérification si {self.scope['user'].username} est participant de l'appel {self.call_id}")
            print(f"Initiateur: {call.initiator.username}, Participants: {[p.username for p in call.participants.all()]}")
            # Vérifier si l'utilisateur est l'initiateur ou un participant
            if call.initiator.id == user_id:
                return True
            is_participant = call.participants.filter(id=user_id).exists()
            print(f"L'utilisateur {user.username} est participant: {is_participant}")
            return is_participant
        except Call.DoesNotExist:
            return False

    @database_sync_to_async
    def save_signaling_message(self, data):
        message_type = data.get('type')
        receiver_id = data.get('receiver')
        content = {}

        # Stocker le contenu spécifique selon le type de message
        if message_type in ['offer', 'answer']:
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
