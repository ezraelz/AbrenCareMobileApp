from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'email', 'address',
                  'first_name', 'last_name', 'phone_number',
                  'profile_picture', 'date_of_birth', 
                  'date_joined', 'allergies',
                  'diagnoses', 'alarm_recipient', 'city',
                  'postal_code']

    search_fields = ['username', 'email', 'first_name', 'last_name']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    ordering = ['id']
    readonly_fields = ['date_joined']

