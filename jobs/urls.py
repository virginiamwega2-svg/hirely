from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
]
