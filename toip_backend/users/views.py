from rest_framework import viewsets, generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.utils import timezone
from rest_framework.decorators import action

from .models import User, UserStatus
from .serializers import UserSerializer, UserStatusSerializer, LoginSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        """Mettre à jour le profil de l'utilisateur connecté"""
        user = request.user

        # Utilisez partial=True pour PATCH (mise à jour partielle)
        if request.method == 'PATCH':
            serializer = self.get_serializer(user, data=request.data, partial=True)
        else:
            serializer = self.get_serializer(user, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)    # Méthode pour définir les permissions selon l'action
    def get_permissions(self):
        if self.action == 'create':  # Pour l'inscription (POST)
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        queryset = User.objects.all()
        username = self.request.query_params.get('username', None)
        if username:
            queryset = queryset.filter(username__icontains=username)
        return queryset


class UserStatusViewSet(viewsets.ModelViewSet):
    queryset = UserStatus.objects.all()
    serializer_class = UserStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserStatus.objects.filter(user=self.request.user)


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)

        # Mettre à jour le statut en ligne
        user.online_status = True
        user.last_seen = timezone.now()
        user.save()

        # Créer ou récupérer le token
        token, created = Token.objects.get_or_create(user=user)

        # Créer ou mettre à jour le statut WebRTC
        status, created = UserStatus.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email
        })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    # Mettre à jour le statut en ligne
    request.user.online_status = False
    request.user.last_seen = timezone.now()
    request.user.save()

    # Mettre à jour le statut WebRTC
    try:
        status = UserStatus.objects.get(user=request.user)
        status.is_in_call = False
        status.session_id = None
        status.save()
    except UserStatus.DoesNotExist:
        pass

    logout(request)
    return Response({"detail": "Déconnexion réussie."})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_me(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)