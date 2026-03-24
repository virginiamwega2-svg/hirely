from django.contrib import admin
from .models import Job, Application


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display  = ('title', 'company', 'schedule_type', 'hours_per_day', 'is_remote', 'is_active', 'created_at')
    list_filter   = ('schedule_type', 'is_remote', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('title', 'company', 'location')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Role', {
            'fields': ('title', 'company', 'location', 'description', 'requirements', 'salary'),
        }),
        ('Flexibility', {
            'fields': ('schedule_type', 'hours_per_day', 'is_remote'),
        }),
        ('Status', {
            'fields': ('posted_by', 'is_active', 'created_at', 'updated_at'),
        }),
    )


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display  = ('applicant', 'job', 'status', 'applied_at')
    list_filter   = ('status',)
    list_editable = ('status',)
    search_fields = ('applicant__email', 'job__title')
    readonly_fields = ('applied_at',)
