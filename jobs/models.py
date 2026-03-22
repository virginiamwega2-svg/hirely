from django.db import models
from django.contrib.auth.models import User


class Job(models.Model):
    JOB_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('remote', 'Remote'),
        ('internship', 'Internship'),
        ('contract', 'Contract'),
    ]

    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default='full_time')
    description = models.TextField()
    requirements = models.TextField()
    salary = models.CharField(max_length=100, blank=True)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='jobs')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} at {self.company}'


class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    cover_letter = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_at']
        unique_together = ('job', 'applicant')

    def __str__(self):
        return f'{self.applicant.username} applied to {self.job.title}'
