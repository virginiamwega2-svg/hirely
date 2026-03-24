from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Count
from django.conf import settings
from .models import Job, Application
from .forms import RegisterForm, JobForm, ApplicationForm


def home(request):
    active_jobs = Job.objects.filter(is_active=True)
    featured_jobs = active_jobs.select_related('posted_by')[:6]
    total_jobs = active_jobs.count()
    type_counts = {
        row['schedule_type']: row['count']
        for row in active_jobs.values('schedule_type').annotate(count=Count('id'))
    }
    return render(request, 'jobs/home.html', {
        'jobs': featured_jobs,
        'total_jobs': total_jobs,
        'type_counts': type_counts,
    })


def job_list(request):
    jobs = Job.objects.filter(is_active=True).select_related('posted_by')
    schedule_type = request.GET.get('schedule_type', '')
    remote_only   = request.GET.get('remote_only', '')
    location      = request.GET.get('location', '')

    if schedule_type:
        jobs = jobs.filter(schedule_type=schedule_type)
    if remote_only:
        jobs = jobs.filter(is_remote=True)
    if location:
        jobs = jobs.filter(location__icontains=location)

    return render(request, 'jobs/job_list.html', {
        'jobs': jobs,
        'schedule_type': schedule_type,
        'remote_only': remote_only,
        'location': location,
        'schedule_choices': Job.SCHEDULE_CHOICES,
    })


def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk, is_active=True)
    has_applied = False
    if request.user.is_authenticated:
        has_applied = Application.objects.filter(job=job, applicant=request.user).exists()
    return render(request, 'jobs/job_detail.html', {'job': job, 'has_applied': has_applied})


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Welcome to Hirely! Start finding your flexible role.')
            return redirect('job_list')
    else:
        form = RegisterForm()
    return render(request, 'jobs/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        email    = request.POST.get('email', '')
        password = request.POST.get('password', '')
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None
        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'jobs/login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def apply(request, pk):
    job = get_object_or_404(Job, pk=pk, is_active=True)

    if job.posted_by == request.user:
        messages.error(request, 'You cannot apply to your own job posting.')
        return redirect('job_detail', pk=pk)

    if Application.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, 'You have already applied for this job.')
        return redirect('job_detail', pk=pk)

    if request.method == 'POST':
        form = ApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.applicant = request.user
            application.save()

            send_mail(
                subject=f'New application for "{job.title}"',
                message=(
                    f'Hi {job.posted_by.username},\n\n'
                    f'{request.user.email} has applied for your flexible role '
                    f'"{job.title}" at {job.company}.\n\n'
                    f'View their application:\n'
                    f'http://127.0.0.1:8000/dashboard/applications/{job.pk}/\n\n'
                    f'— Hirely Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[job.posted_by.email],
                fail_silently=True,
            )

            messages.success(request, f'Applied to {job.title}! The employer has been notified.')
            return redirect('my_applications')
    else:
        form = ApplicationForm()
    return render(request, 'jobs/apply.html', {'form': form, 'job': job})


@login_required
def my_applications(request):
    applications = (
        Application.objects
        .filter(applicant=request.user)
        .select_related('job', 'job__posted_by')
    )
    return render(request, 'jobs/my_applications.html', {'applications': applications})


# ── Employer views ────────────────────────────────────────────────────

@login_required
def employer_dashboard(request):
    jobs = (
        Job.objects
        .filter(posted_by=request.user)
        .annotate(application_count=Count('applications'))
    )
    return render(request, 'jobs/employer_dashboard.html', {'jobs': jobs})


@login_required
def post_job(request):
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.save()
            messages.success(request, 'Your flexible role is live!')
            return redirect('employer_dashboard')
    else:
        form = JobForm()
    return render(request, 'jobs/job_form.html', {'form': form, 'action': 'Post'})


@login_required
def edit_job(request, pk):
    job = get_object_or_404(Job, pk=pk, posted_by=request.user)
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Role updated.')
            return redirect('employer_dashboard')
    else:
        form = JobForm(instance=job)
    return render(request, 'jobs/job_form.html', {'form': form, 'action': 'Edit'})


@login_required
def delete_job(request, pk):
    job = get_object_or_404(Job, pk=pk, posted_by=request.user)
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Role removed.')
        return redirect('employer_dashboard')
    return render(request, 'jobs/delete_job.html', {'job': job})


@login_required
def job_applications(request, pk):
    job = get_object_or_404(Job, pk=pk, posted_by=request.user)
    applications = job.applications.select_related('applicant')
    return render(request, 'jobs/job_applications.html', {'job': job, 'applications': applications})
