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


# ─────────────────────────────────────────────────────────────────────
# "Talk to Hirely" — conversational agent powered by Claude with a
# search_jobs tool grounded in our own Job table.
# ─────────────────────────────────────────────────────────────────────

import json
import logging
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

CHAT_MODEL = 'claude-haiku-4-5-20251001'  # fast + cheap, plenty for this task

SEARCH_JOBS_TOOL = {
    'name': 'search_jobs',
    'description': (
        "Search Hirely's active flexible job listings. Call this once you "
        "have at least one concrete signal (hours, remote/on-site, schedule "
        "pattern, or keywords). Be lenient — partial matches are fine. "
        "Results are sorted by recency."
    ),
    'input_schema': {
        'type': 'object',
        'properties': {
            'keywords': {
                'type': 'string',
                'description': 'Free-text keywords matched against title, company, and description.',
            },
            'schedule_type': {
                'type': 'string',
                'enum': ['fixed', 'flexible', 'anytime'],
                'description': (
                    'fixed = employer sets specific days/hours, '
                    'flexible = total hours agreed but parent picks when, '
                    'anytime = fully async, no required hours.'
                ),
            },
            'is_remote': {
                'type': 'boolean',
                'description': 'True to filter to remote-only roles.',
            },
            'max_hours_per_day': {
                'type': 'integer',
                'description': 'Maximum hours/day the parent can work (e.g. 4 for mornings only).',
            },
        },
        'required': [],
    },
}

SYSTEM_PROMPT = """You are Hirely — a warm, briefly-spoken assistant on a job board for busy parents.

Tone:
- Friendly like a knowledgeable friend, never corporate.
- Concise. 1–3 short sentences per turn. No lectures.
- Validate parent realities (school runs, naps, term-time) as normal.

Behaviour:
- If you have at least one concrete signal, call search_jobs.
- If the request is vague, ask ONE quick clarifying question — never a list.
- After search_jobs returns, mention how many fit in one sentence. The UI renders the cards, so DO NOT list every job in prose.
- If zero results, suggest widening one specific constraint.
- Never invent jobs or details — only refer to what search_jobs returned.
"""


def _job_to_card(job):
    """Serialise a Job for the chat UI."""
    return {
        'id': job.id,
        'title': job.title,
        'company': job.company,
        'location': job.location or '',
        'salary': job.salary or '',
        'schedule_type': job.get_schedule_type_display(),
        'is_remote': job.is_remote,
        'hours_per_day': job.hours_per_day,
        'flex_label': job.flex_label,
        'flex_colour': job.flex_colour,
        'url': reverse('job_detail', args=[job.id]),
        'description': (job.description or '')[:160],
    }


def _run_search_jobs(params):
    """Execute the search_jobs tool against the Job table."""
    qs = Job.objects.filter(is_active=True).select_related('posted_by')

    keywords = (params.get('keywords') or '').strip()
    if keywords:
        qs = qs.filter(
            Q(title__icontains=keywords)
            | Q(company__icontains=keywords)
            | Q(description__icontains=keywords)
        )

    schedule_type = params.get('schedule_type')
    if schedule_type in {'fixed', 'flexible', 'anytime'}:
        qs = qs.filter(schedule_type=schedule_type)

    if params.get('is_remote') is True:
        qs = qs.filter(is_remote=True)

    max_hpd = params.get('max_hours_per_day')
    if isinstance(max_hpd, int) and max_hpd > 0:
        # Include unspecified (NULL) hours_per_day too — they may still fit.
        qs = qs.filter(Q(hours_per_day__lte=max_hpd) | Q(hours_per_day__isnull=True))

    jobs = list(qs.order_by('-created_at')[:6])
    return {
        'count': len(jobs),
        'jobs': [_job_to_card(j) for j in jobs],
    }


@require_POST
def chat(request):
    """
    POST JSON: { "messages": [ {role, content}, ... ] }
    Returns JSON: { "reply": str, "jobs": [card,...] }
    """
    if not settings.ANTHROPIC_API_KEY:
        return JsonResponse(
            {'reply': "I'm not connected to my brain yet — the site owner needs to set ANTHROPIC_API_KEY.", 'jobs': []},
            status=200,
        )

    try:
        body = json.loads(request.body or b'{}')
        messages = body.get('messages') or []
        if not isinstance(messages, list) or not messages:
            return JsonResponse({'error': 'messages required'}, status=400)
        # Sanity-cap turn count to keep cost bounded.
        messages = messages[-20:]
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid json'}, status=400)

    # Lazy import so the SDK isn't required at startup if the key is unset.
    from anthropic import Anthropic
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    from anthropic import APIError

    collected_jobs = []
    # Tool-use loop — at most 2 rounds (the agent should rarely need more).
    for _ in range(3):
        try:
            resp = client.messages.create(
                model=CHAT_MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                tools=[SEARCH_JOBS_TOOL],
                messages=messages,
            )
        except APIError as e:
            logger.warning('Anthropic API error: %s', e)
            msg = str(getattr(e, 'message', '') or e)
            if 'credit balance' in msg.lower():
                friendly = "I'm temporarily resting — the site needs to top up its Anthropic credits. Try again shortly."
            else:
                friendly = "I'm having a moment — try again in a few seconds?"
            return JsonResponse({'reply': friendly, 'jobs': collected_jobs}, status=200)

        if resp.stop_reason == 'tool_use':
            # Append the assistant's tool_use turn.
            messages.append({'role': 'assistant', 'content': resp.content})

            # Execute every tool_use block, collect results.
            tool_results = []
            for block in resp.content:
                if block.type == 'tool_use' and block.name == 'search_jobs':
                    try:
                        result = _run_search_jobs(block.input or {})
                    except Exception:
                        logger.exception('search_jobs failed')
                        result = {'count': 0, 'jobs': [], 'error': 'search failed'}
                    collected_jobs = result['jobs']  # keep the latest set
                    tool_results.append({
                        'type': 'tool_result',
                        'tool_use_id': block.id,
                        'content': json.dumps({'count': result['count'], 'jobs': result['jobs']}),
                    })

            messages.append({'role': 'user', 'content': tool_results})
            continue  # let the model speak again with results in hand

        # end_turn / max_tokens / stop_sequence — final assistant reply.
        reply_text = ''.join(
            block.text for block in resp.content if getattr(block, 'type', None) == 'text'
        ).strip()
        return JsonResponse({'reply': reply_text, 'jobs': collected_jobs})

    # Safety net if the loop runs away.
    return JsonResponse({'reply': "Hmm, I got a bit tangled — try rephrasing?", 'jobs': collected_jobs})


# ─────────────────────────────────────────────────────────────────────
# Application assistant — drafts an optional short personal note for
# the parent. Tone-controlled, fully editable, 1–2 sentences max.
# ─────────────────────────────────────────────────────────────────────

DRAFT_TONES = {
    'warm':       'warm and personable — like writing to someone you trust',
    'confident':  'confident and capable — quietly self-assured, no bragging',
    'brief':      'very brief and direct — just the essentials, one sentence',
}

DRAFT_SYSTEM_PROMPT = """You help busy parents write a short, optional personal note on a job application.

Rules:
- Output ONLY the note text. No greeting, no sign-off, no quotation marks, no preamble.
- 1–2 sentences. Maximum 300 characters.
- Sound like a real parent — not a corporate cover letter. Plain words.
- Reference one concrete fit between the parent's situation and the role (schedule, remote, hours, skills).
- Never invent specifics about the parent. If the user-provided seed is empty, write something universally true and warm.
- Never apologise for being a parent or for needing flexibility — frame it as normal.
"""


@login_required
@require_POST
def draft_application_note(request, pk):
    """POST JSON: { "tone": "warm|confident|brief", "seed": "optional user text" }
    Returns: { "note": "..." }"""
    job = get_object_or_404(Job, pk=pk, is_active=True)

    if not settings.ANTHROPIC_API_KEY:
        return JsonResponse({'note': '', 'error': "AI assistant isn't connected yet."}, status=200)

    try:
        body = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'invalid json'}, status=400)

    tone_key = body.get('tone', 'warm')
    tone_desc = DRAFT_TONES.get(tone_key, DRAFT_TONES['warm'])
    seed = (body.get('seed') or '').strip()[:400]

    user_prompt = (
        f"Role: {job.title} at {job.company}\n"
        f"Schedule: {job.get_schedule_type_display()}"
        f"{' · Remote' if job.is_remote else ''}"
        f"{f' · {job.hours_per_day} hrs/day' if job.hours_per_day else ''}\n"
        f"What they're hiring for: {(job.description or '')[:500]}\n\n"
        f"Tone: {tone_desc}\n"
    )
    if seed:
        user_prompt += f"\nWhat the parent said (use as a seed, don't invent beyond it):\n{seed}\n"
    user_prompt += "\nWrite the note now."

    from anthropic import Anthropic, APIError
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        resp = client.messages.create(
            model=CHAT_MODEL,
            max_tokens=200,
            system=DRAFT_SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_prompt}],
        )
    except APIError as e:
        logger.warning('draft_application_note API error: %s', e)
        msg = str(getattr(e, 'message', '') or e)
        friendly = (
            "AI is resting — the site needs to top up Anthropic credits."
            if 'credit balance' in msg.lower()
            else "Couldn't draft right now — try again in a moment."
        )
        return JsonResponse({'note': '', 'error': friendly}, status=200)

    note = ''.join(b.text for b in resp.content if getattr(b, 'type', None) == 'text').strip()
    # Strip any stray quotes the model might have wrapped.
    if note.startswith(('"', "'")) and note.endswith(('"', "'")):
        note = note[1:-1].strip()
    return JsonResponse({'note': note[:400]})


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
