from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('jobs/<int:pk>/apply/', views.apply, name='apply'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('dashboard/', views.employer_dashboard, name='employer_dashboard'),
    path('dashboard/post/', views.post_job, name='post_job'),
    path('dashboard/edit/<int:pk>/', views.edit_job, name='edit_job'),
    path('dashboard/delete/<int:pk>/', views.delete_job, name='delete_job'),
    path('dashboard/applications/<int:pk>/', views.job_applications, name='job_applications'),
    path('dashboard/applications/<int:pk>/status/', views.update_application_status, name='update_application_status'),
    path('dashboard/toggle/<int:pk>/', views.toggle_job_active, name='toggle_job_active'),
]
