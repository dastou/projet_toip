from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, UserStatus


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'phone_number', 'profile_image', 'online_status', 'last_seen', 'password']
        read_only_fields = ['id', 'online_status', 'last_seen']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        # Extraire le mot de passe s'il est présent
        password = validated_data.pop('password', None)

        # Mettre à jour les autres champs
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Si un mot de passe est fourni, le définir séparément
        if password:
            instance.set_password(password)

        instance.save()
        return instance

class UserStatusSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserStatus
        fields = ['id', 'user', 'username', 'session_id', 'is_in_call', 'device_info', 'last_ping']
        read_only_fields = ['id', 'user']


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(label="Username ou Email")
    password = serializers.CharField(style={'input_type': 'password'}, trim_whitespace=False)

    def validate(self, attrs):
        username_or_email = attrs.get('username')
        password = attrs.get('password')

        if username_or_email and password:
            # Ajouter des prints pour déboguer
            print(f"Tentative de connexion pour: {username_or_email}")

            # Vérifier si l'entrée est un email ou un username
            if '@' in username_or_email:
                # C'est probablement un email, on cherche l'utilisateur par email
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    print(f"Utilisateur trouvé par email: {user_obj.username}")
                    # Si on trouve l'utilisateur par email, on utilise son username pour l'authentification
                    user = authenticate(request=self.context.get('request'),
                                        username=user_obj.username, password=password)
                except User.DoesNotExist:
                    print(f"Aucun utilisateur trouvé avec l'email: {username_or_email}")
                    user = None
            else:
                # C'est probablement un username
                print(f"Tentative d'authentification avec username: {username_or_email}")
                user = authenticate(request=self.context.get('request'),
                                    username=username_or_email, password=password)

            if not user:
                print(f"Échec d'authentification pour {username_or_email}")
                msg = 'Impossible de se connecter avec les identifiants fournis.'
                raise serializers.ValidationError(msg, code='authorization')
            else:
                print(f"Authentification réussie pour {user.username}")
        else:
            msg = 'Les champs "username" et "password" sont requis.'
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs