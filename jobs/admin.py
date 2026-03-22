from django.contrib import admin
from .models import Job, Application


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'location', 'job_type', 'is_active', 'created_at')
    list_filter = ('job_type', 'is_active')
    search_fields = ('title', 'company', 'location')
    list_editable = ('is_active',)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'job', 'status', 'applied_at')
    list_filter = ('status',)
    search_fields = ('applicant__username', 'job__title')
    list_editable = ('status',)
