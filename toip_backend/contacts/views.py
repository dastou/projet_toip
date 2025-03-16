from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Contact, ContactGroup
from .serializers import ContactSerializer, ContactGroupSerializer
from users.models import User


class ContactGroupViewSet(viewsets.ModelViewSet):
    serializer_class = ContactGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ContactGroup.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nickname', 'contact_user__username', 'contact_user__email',
                     'contact_user__first_name', 'contact_user__last_name', 'phone']

    def get_queryset(self):
        return Contact.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'])
    def favorites(self, request):
        favorites = self.get_queryset().filter(is_favorite=True)
        serializer = self.get_serializer(favorites, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        contact = self.get_object()
        contact.is_favorite = not contact.is_favorite
        contact.save()
        serializer = self.get_serializer(contact)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_to_group(self, request, pk=None):
        contact = self.get_object()
        group_id = request.data.get('group_id')
        if not group_id:
            return Response({'error': 'group_id est requis'}, status=400)

        group = get_object_or_404(ContactGroup, id=group_id, owner=request.user)
        contact.groups.add(group)
        serializer = self.get_serializer(contact)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def remove_from_group(self, request, pk=None):
        contact = self.get_object()
        group_id = request.data.get('group_id')
        if not group_id:
            return Response({'error': 'group_id est requis'}, status=400)

        group = get_object_or_404(ContactGroup, id=group_id, owner=request.user)
        contact.groups.remove(group)
        serializer = self.get_serializer(contact)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_group(self, request):
        group_id = request.query_params.get('group_id')
        if not group_id:
            return Response({'error': 'group_id est requis'}, status=400)

        group = get_object_or_404(ContactGroup, id=group_id, owner=request.user)
        contacts = self.get_queryset().filter(groups=group)
        serializer = self.get_serializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def record_contact(self, request, pk=None):
        """Record when the last contact happened"""
        contact = self.get_object()
        contact.last_contact = timezone.now()
        contact.save()
        serializer = self.get_serializer(contact)
        return Response(serializer.data)