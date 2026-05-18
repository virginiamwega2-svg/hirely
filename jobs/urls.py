from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('og-image.svg', views.og_image, name='og_image'),
    path('about/', views.about, name='about'),
    path('chat/', views.chat, name='chat'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('jobs/<int:pk>/ask/', views.ask_about_job, name='ask_about_job'),
    path('jobs/<int:pk>/apply/', views.apply, name='apply'),
    path('jobs/<int:pk>/draft-note/', views.draft_application_note, name='draft_application_note'),
    path('my-applications/', views.my_applications, name='my_applications'),
    path('me/', views.parent_profile, name='parent_profile'),
    path('dashboard/', views.employer_dashboard, name='employer_dashboard'),
    path('dashboard/post/', views.post_job, name='post_job'),
    path('dashboard/edit/<int:pk>/', views.edit_job, name='edit_job'),
    path('dashboard/delete/<int:pk>/', views.delete_job, name='delete_job'),
    path('dashboard/applications/<int:pk>/', views.job_applications, name='job_applications'),
    path('dashboard/applications/<int:pk>/status/', views.update_application_status, name='update_application_status'),
    path('dashboard/applications/<int:pk>/summarise/', views.summarise_application, name='summarise_application'),
    path('my-applications/<int:pk>/interview-prep/', views.interview_prep, name='interview_prep'),
    path('dashboard/toggle/<int:pk>/', views.toggle_job_active, name='toggle_job_active'),
    # Legal
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    # Save-for-later
    path('saved/', views.my_saved_jobs, name='my_saved_jobs'),
    path('jobs/<int:pk>/save/', views.toggle_save_job, name='toggle_save_job'),
    # AI job writer
    path('dashboard/draft-job/', views.draft_job_description, name='draft_job_description'),
    # Withdraw application
    path('my-applications/<int:pk>/withdraw/', views.withdraw_application, name='withdraw_application'),
    # Unsubscribe from digest
    path('unsubscribe/<str:token>/', views.unsubscribe_digest, name='unsubscribe_digest'),
    # SEO
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap_xml'),
]
