from django.contrib import admin
from .models import Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'role_name',
        'created_at'
    ]
    search_fields = [
        'role_name'
    ]
