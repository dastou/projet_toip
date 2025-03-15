from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, UserStatus

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'phone_number', 'profile_image', 'online_status', 'last_seen', 'password']
        read_only_fields = ['id', 'online_status', 'last_seen']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserStatusSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserStatus
        fields = ['id', 'user', 'username', 'session_id', 'is_in_call', 'device_info', 'last_ping']
        read_only_fields = ['id', 'user']

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'}, trim_whitespace=False)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Ajouter des prints pour déboguer
            print(f"Tentative de connexion pour l'utilisateur: {username}")
            
            # Vérifier si l'utilisateur existe
            try:
                user_obj = User.objects.get(username=username)
                print(f"Utilisateur trouvé dans la base de données")
            except User.DoesNotExist:
                print(f"Utilisateur {username} n'existe pas dans la base de données")
            
            # Tenter l'authentification
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)
            
            if not user:
                print(f"Échec d'authentification pour {username}")
                msg = 'Impossible de se connecter avec les identifiants fournis.'
                raise serializers.ValidationError(msg, code='authorization')
            else:
                print(f"Authentification réussie pour {username}")
        else:
            msg = 'Les champs "username" et "password" sont requis.'
            raise serializers.ValidationError(msg, code='authorization')
        
        attrs['user'] = user
        return attrs