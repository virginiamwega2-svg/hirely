from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Job, Application


# ── Model tests ───────────────────────────────────────────────────────

class JobModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('employer', 'e@test.com', 'pass')
        self.job = Job.objects.create(
            title='VA Role', company='Acme', schedule_type='flexible',
            is_remote=True, description='Test', posted_by=self.user
        )

    def test_flex_score_flexible_remote(self):
        self.assertEqual(self.job.flex_score, 2)

    def test_flex_score_fixed_onsite(self):
        self.job.schedule_type = 'fixed'
        self.job.is_remote = False
        self.assertEqual(self.job.flex_score, 1)

    def test_flex_score_anytime_remote(self):
        self.job.schedule_type = 'anytime'
        self.job.is_remote = True
        self.assertEqual(self.job.flex_score, 3)

    def test_flex_label_very_flexible(self):
        self.assertEqual(self.job.flex_label, 'Flexible')

    def test_flex_label_some_flex(self):
        self.job.schedule_type = 'fixed'
        self.job.is_remote = False
        self.assertEqual(self.job.flex_label, 'Some Flex')

    def test_flex_colour_success(self):
        self.assertEqual(self.job.flex_colour, 'primary')

    def test_flex_colour_secondary(self):
        self.job.schedule_type = 'fixed'
        self.job.is_remote = False
        self.assertEqual(self.job.flex_colour, 'secondary')

    def test_is_new_on_fresh_job(self):
        self.assertTrue(self.job.is_new)

    def test_str(self):
        self.assertEqual(str(self.job), 'VA Role at Acme')

    def test_active_by_default(self):
        self.assertTrue(self.job.is_active)


# ── Public view tests ─────────────────────────────────────────────────

class PublicViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.employer = User.objects.create_user('emp', 'emp@test.com', 'pass')
        self.job = Job.objects.create(
            title='Test Job', company='Co', schedule_type='anytime',
            description='Desc', posted_by=self.employer, is_active=True
        )

    def test_home_returns_200(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)

    def test_job_list_returns_200(self):
        self.assertEqual(self.client.get(reverse('job_list')).status_code, 200)

    def test_job_detail_returns_200(self):
        r = self.client.get(reverse('job_detail', args=[self.job.pk]))
        self.assertEqual(r.status_code, 200)

    def test_inactive_job_returns_404(self):
        self.job.is_active = False
        self.job.save()
        r = self.client.get(reverse('job_detail', args=[self.job.pk]))
        self.assertEqual(r.status_code, 404)

    def test_apply_redirects_unauthenticated(self):
        r = self.client.get(reverse('apply', args=[self.job.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r['Location'])

    def test_job_list_shows_active_jobs(self):
        r = self.client.get(reverse('job_list'))
        self.assertContains(r, 'Test Job')

    def test_job_list_filter_schedule_match(self):
        r = self.client.get(reverse('job_list') + '?schedule_type=anytime')
        self.assertContains(r, 'Test Job')

    def test_job_list_filter_schedule_no_match(self):
        r = self.client.get(reverse('job_list') + '?schedule_type=fixed')
        self.assertNotContains(r, 'Test Job')

    def test_job_list_search_match(self):
        r = self.client.get(reverse('job_list') + '?search=Test')
        self.assertContains(r, 'Test Job')

    def test_job_list_search_no_match(self):
        r = self.client.get(reverse('job_list') + '?search=zzznomatch')
        self.assertNotContains(r, 'Test Job')

    def test_dashboard_requires_login(self):
        r = self.client.get(reverse('employer_dashboard'))
        self.assertEqual(r.status_code, 302)

    def test_my_applications_requires_login(self):
        r = self.client.get(reverse('my_applications'))
        self.assertEqual(r.status_code, 302)

    def test_register_page_returns_200(self):
        self.assertEqual(self.client.get(reverse('register')).status_code, 200)

    def test_login_page_returns_200(self):
        self.assertEqual(self.client.get(reverse('login')).status_code, 200)


# ── Authenticated view tests ──────────────────────────────────────────

class AuthViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.employer  = User.objects.create_user('emp', 'emp@test.com', 'pass')
        self.applicant = User.objects.create_user('app', 'app@test.com', 'pass')
        self.job = Job.objects.create(
            title='Role', company='Co', schedule_type='flexible',
            description='Desc', posted_by=self.employer, is_active=True
        )

    def test_apply_creates_application(self):
        self.client.login(username='app', password='pass')
        self.client.post(reverse('apply', args=[self.job.pk]))
        self.assertTrue(Application.objects.filter(
            job=self.job, applicant=self.applicant
        ).exists())

    def test_apply_own_job_blocked(self):
        self.client.login(username='emp', password='pass')
        self.client.post(reverse('apply', args=[self.job.pk]))
        self.assertFalse(Application.objects.filter(job=self.job).exists())

    def test_duplicate_apply_blocked(self):
        self.client.login(username='app', password='pass')
        self.client.post(reverse('apply', args=[self.job.pk]))
        self.client.post(reverse('apply', args=[self.job.pk]))
        self.assertEqual(Application.objects.filter(job=self.job).count(), 1)

    def test_employer_dashboard_returns_200(self):
        self.client.login(username='emp', password='pass')
        r = self.client.get(reverse('employer_dashboard'))
        self.assertEqual(r.status_code, 200)

    def test_employer_can_post_job(self):
        self.client.login(username='emp', password='pass')
        self.client.post(reverse('post_job'), {
            'title': 'New Job', 'company': 'Co',
            'schedule_type': 'anytime', 'description': 'Test desc',
        })
        self.assertTrue(Job.objects.filter(title='New Job').exists())

    def test_employer_cannot_edit_others_job(self):
        other = User.objects.create_user('other', 'o@test.com', 'pass')
        self.client.login(username='other', password='pass')
        r = self.client.post(reverse('edit_job', args=[self.job.pk]), {'title': 'Hijacked'})
        self.assertEqual(r.status_code, 404)

    def test_employer_cannot_delete_others_job(self):
        other = User.objects.create_user('other2', 'o2@test.com', 'pass')
        self.client.login(username='other2', password='pass')
        r = self.client.post(reverse('delete_job', args=[self.job.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Job.objects.filter(pk=self.job.pk).exists())

    def test_my_applications_shows_applications(self):
        Application.objects.create(job=self.job, applicant=self.applicant)
        self.client.login(username='app', password='pass')
        r = self.client.get(reverse('my_applications'))
        self.assertContains(r, 'Role')

    def test_authenticated_redirected_from_login(self):
        self.client.login(username='app', password='pass')
        r = self.client.get(reverse('login'))
        self.assertEqual(r.status_code, 302)

    def test_authenticated_redirected_from_register(self):
        self.client.login(username='app', password='pass')
        r = self.client.get(reverse('register'))
        self.assertEqual(r.status_code, 302)


# ── Auth flow tests ───────────────────────────────────────────────────

class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        User.objects.create_user('testuser', 'test@test.com', 'password123')

    def test_register_creates_user(self):
        self.client.post(reverse('register'), {
            'email': 'new@test.com',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        })
        self.assertTrue(User.objects.filter(email='new@test.com').exists())

    def test_register_duplicate_email_blocked(self):
        self.client.post(reverse('register'), {
            'email': 'test@test.com',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        })
        self.assertEqual(User.objects.filter(email='test@test.com').count(), 1)

    def test_register_mismatched_passwords(self):
        self.client.post(reverse('register'), {
            'email': 'mismatch@test.com',
            'password1': 'StrongPass123',
            'password2': 'Different456',
        })
        self.assertFalse(User.objects.filter(email='mismatch@test.com').exists())

    def test_login_valid_credentials(self):
        r = self.client.post(reverse('login'), {
            'email': 'test@test.com', 'password': 'password123'
        })
        self.assertEqual(r.status_code, 302)

    def test_login_wrong_password(self):
        r = self.client.post(reverse('login'), {
            'email': 'test@test.com', 'password': 'wrongpass'
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Invalid')

    def test_login_nonexistent_email(self):
        r = self.client.post(reverse('login'), {
            'email': 'nobody@test.com', 'password': 'anything'
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Invalid')

    def test_open_redirect_blocked(self):
        r = self.client.post(
            reverse('login') + '?next=https://evil.com',
            {'email': 'test@test.com', 'password': 'password123'}
        )
        location = r.get('Location', '')
        self.assertFalse(location.startswith('https://evil.com'))

    def test_logout_redirects(self):
        self.client.login(username='testuser', password='password123')
        r = self.client.get(reverse('logout'))
        self.assertEqual(r.status_code, 302)
