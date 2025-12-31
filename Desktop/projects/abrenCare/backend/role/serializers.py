from rest_framework import serializers
from .models import Role

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = [
            'id',
            'role_name',
            'description',
            'created_at'
        ]
        read_only_fields = [
            'id', 'created_at'
        ]
