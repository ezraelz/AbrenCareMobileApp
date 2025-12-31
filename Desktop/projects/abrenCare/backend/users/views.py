from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from rest_framework import generics, permissions
from rest_framework import status
from .models import User
from .serializers import UserSerializer, UserCreateSerializer, UserUpdateSerializer, CustomTokenObtainPairSerializer
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


class UsersListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserProfileView(APIView):
    permission_classess = [permissions.IsAuthenticated]
    
    def get(self, request, pk=None, *args, **kwargs):
        if pk:
            try:
                user = User.objects.get(id=pk)
            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=404)
        else:
            user = request.user

        serializer = UserSerializer(user)
        return Response(serializer.data)
     
    def put(self, reqeust, pk=None):
        user = User.objects.get(id=pk)
        serializer = UserSerializer(user, data=reqeust.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
    def delete(self, request, pk):
        user = User.objects.get(id=pk)
        user.delete()
        return Response('user removed successfuly!')
        
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class TokenRefreshView(TokenRefreshView):
    pass


class RegisterUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

class LoginUserView(APIView): 
    permission_classes = [permissions.AllowAny]
    
    def post(self, request): 
        username = request.data.get('username') 
        password = request.data.get('password') 
        user = authenticate(username=username, password=password) 
        profile_image = None
        if hasattr(user, "profile_image") and user.get_profile_picture_url():
            profile_image = request.build_absolute_uri(user.profile_picture)

        if user is not None: 
            login(request, user) 
            refresh = RefreshToken.for_user(user) 
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "is_superuser": user.is_superuser,
                "id": user.id,
                "username": user.username,
                "profile_picture": profile_image,
        })
        else: return Response({'error': 'Invalid credentials'}, status=400)
 

class LogoutUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        request.user.auth_token.delete()
        logout(request)
        return Response({"success": "Logged out successfully"})
    
