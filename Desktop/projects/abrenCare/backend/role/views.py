from django.shortcuts import render
from rest_framework.view import APIView
from rest_framework.response import Response
from rest_framework.status import status
from rest_framework.permissions import IsAuthenticated

from .models import Role
from .serializers import RoleSerializer


class RoleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roles = Role.objects.all()
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        serializer = RoleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class RoleDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        role = Role.objects.get(id=pk)
        serializer = RoleSerializer(role)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, pk):
        role = Role.objects.get(id=pk)
        serializer = RoleSerializer(role, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        role = Role.objects.get(id=pk)
        role.delete()
        return Response('Role deleted successfuly!')

