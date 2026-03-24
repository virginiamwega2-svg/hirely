from django import forms
from django.contrib.auth.models import User
from .models import Job, Application


class RegisterForm(forms.Form):
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords don't match.")
        return cleaned_data

    def save(self):
        email = self.cleaned_data['email']
        password = self.cleaned_data['password1']
        base = email.split('@')[0][:20]
        username = base
        n = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{n}'
            n += 1
        return User.objects.create_user(username=username, email=email, password=password)


class JobForm(forms.ModelForm):
    """
    Employer-facing form.  hours_per_day is an integer so it validates
    correctly and can be filtered later (unlike the old free-text CharField).
    """

    hours_per_day = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=12,
        label='Hours per Day',
        help_text='Typical hours per working day (1–12). Leave blank if it varies.',
        widget=forms.NumberInput(attrs={'placeholder': 'e.g. 4', 'class': 'form-control'}),
    )

    class Meta:
        model = Job
        fields = [
            'title', 'company', 'location',
            'schedule_type', 'hours_per_day', 'is_remote',
            'description', 'requirements', 'salary',
        ]
        help_texts = {
            'location':      'City, region, or leave blank for remote-only roles.',
            'schedule_type': 'Choose the pattern that best describes when this role is worked.',
            'is_remote':     'Tick if the parent can work from home — even part of the time.',
            'salary':        'e.g. "£15/hr", "£25,000 pro-rata". Be transparent — parents budget carefully.',
        }
        widgets = {
            'description':  forms.Textarea(attrs={'rows': 5}),
            'requirements': forms.Textarea(attrs={'rows': 3}),
        }


class ApplicationForm(forms.ModelForm):
    """Single optional field — no cover letter, by design."""

    class Meta:
        model = Application
        fields = ['resume']
