from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.urls import reverse
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme
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
    search        = request.GET.get('search', '')
    sort          = request.GET.get('sort', '')

    if schedule_type:
        jobs = jobs.filter(schedule_type=schedule_type)
    if remote_only:
        jobs = jobs.filter(is_remote=True)
    if location:
        jobs = jobs.filter(location__icontains=location)
    if search:
        jobs = jobs.filter(Q(title__icontains=search) | Q(company__icontains=search))

    sort_map = {
        'flex': ['-flex_score'],   # computed property — can't use in DB sort
        'oldest': ['created_at'],
    }
    if sort == 'flex':
        # flex_score is a Python property, so sort in Python after slicing would miss records;
        # approximate with schedule_type ordering instead (anytime > flexible > fixed)
        from django.db.models import Case, When, IntegerField
        jobs = jobs.annotate(
            _flex=Case(
                When(schedule_type='anytime', then=3),
                When(schedule_type='flexible', then=2),
                When(schedule_type='fixed', then=1),
                output_field=IntegerField(),
            )
        ).order_by('-_flex', '-created_at')
    elif sort == 'oldest':
        jobs = jobs.order_by('created_at')
    else:
        jobs = jobs.order_by('-created_at')

    total_count = jobs.count()
    paginator = Paginator(jobs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'jobs/job_list.html', {
        'page_obj': page_obj,
        'total_count': total_count,
        'schedule_type': schedule_type,
        'remote_only': remote_only,
        'location': location,
        'search': search,
        'sort': sort,
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
            next_url = request.POST.get('next') or request.GET.get('next') or ''
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect(reverse('home'))
        messages.error(request, 'Invalid email or password.')
        return render(request, 'jobs/login.html', {'has_error': True, 'next': request.POST.get('next', '')})
    return render(request, 'jobs/login.html', {'next': request.GET.get('next', '')})


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

            employer_url = request.build_absolute_uri(
                reverse('job_applications', args=[job.pk])
            )
            applicant_url = request.build_absolute_uri(reverse('my_applications'))

            send_mail(
                subject=f'New application for "{job.title}"',
                message=(
                    f'Hi {job.posted_by.username},\n\n'
                    f'{request.user.email} has applied for your flexible role '
                    f'"{job.title}" at {job.company}.\n\n'
                    f'View their application:\n'
                    f'{employer_url}\n\n'
                    f'— Hirely Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[job.posted_by.email],
                fail_silently=True,
            )

            send_mail(
                subject=f'Application sent — {job.title} at {job.company}',
                message=(
                    f'Hi,\n\n'
                    f'Your application for "{job.title}" at {job.company} has been received.\n\n'
                    f"You'll hear back if the employer is interested. Good luck!\n\n"
                    f'View all your applications:\n'
                    f'{applicant_url}\n\n'
                    f'— Hirely Team'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
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
    applications = job.applications.select_related('applicant').order_by('-applied_at')
    paginator = Paginator(applications, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'jobs/job_applications.html', {'job': job, 'page_obj': page_obj})


@login_required
def toggle_job_active(request, pk):
    if request.method == 'POST':
        job = get_object_or_404(Job, pk=pk, posted_by=request.user)
        job.is_active = not job.is_active
        job.save(update_fields=['is_active', 'updated_at'])
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'is_active': job.is_active})
    return redirect('employer_dashboard')


@login_required
def update_application_status(request, pk):
    app = get_object_or_404(Application, pk=pk, job__posted_by=request.user)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in dict(Application.STATUS_CHOICES):
            app.status = status
            app.save()
    page = request.POST.get('page', '')
    url = reverse('job_applications', args=[app.job.pk])
    if page:
        url += f'?page={page}'
    return redirect(url)
