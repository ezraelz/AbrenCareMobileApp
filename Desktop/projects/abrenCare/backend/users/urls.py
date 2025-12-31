from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterUserView.as_view(), name='register'),
    path('login/', views.LoginUserView.as_view(), name='login'),
    path('logout/', views.LogoutUserView.as_view(), name='logout'),
    path('users/', views.UsersListView.as_view(), name='user_list'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('profile/<int:pk>/', views.UserProfileView.as_view(), name='profile_detail'),
    path("token/", views.CustomTokenObtainPairView.as_view()),
    path("token/refresh/", views.TokenRefreshView.as_view()),
]