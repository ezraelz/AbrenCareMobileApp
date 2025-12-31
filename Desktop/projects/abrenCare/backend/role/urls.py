from django.urls import path
from . import views

urlpatterns = [
    path('roles', views.RoleView.as_view(), name='view-roles'),
    path('roles/<int:pk>/', views.RoleDetailView.as_view(), name='role-detail')
]
