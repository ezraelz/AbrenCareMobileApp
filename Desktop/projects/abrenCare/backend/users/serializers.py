from rest_framework import serializers
from .models import User
try:
    from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
except Exception:
    # Fallback minimal base class if simplejwt is not available or unresolved by the analyzer.
    # Uses RefreshToken.for_user so CustomTokenObtainPairSerializer.super().get_token will work.
    from rest_framework_simplejwt.tokens import RefreshToken

    class TokenObtainPairSerializer:
        @classmethod
        def get_token(cls, user):
            return RefreshToken.for_user(user)


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'address',
                  'first_name', 'last_name', 'phone_number',
                  'profile_picture', 'date_of_birth', 
                  'date_joined', 'full_name', 'allergies',
                  'diagnoses', 'alarm_recipient', 'city',
                  'postal_code', 'role']
        read_only_fields = ['id']

    def get_full_name(self, obj):
        return obj.get_full_name()

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.role(role_name='patient')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'profile_picture', 'username', 'email', 'date_of_birth']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['is_superuser'] = user.is_superuser

        return token

