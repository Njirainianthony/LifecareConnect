from django import forms
from django.contrib.auth import get_user_model
from .models import PatientProfile, DoctorProfile, Profile, DoctorAvailability, Equipment
from datetime import time, datetime, timedelta

class UserEditForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['date_of_birth', 'photo']

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label='Repeat password',
        widget=forms.PasswordInput
    )

    USER_TYPE_CHOICES = [
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
    ]
    user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES, label='I am a')

    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'email']

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError("Passwords don't match.")
        return cd['password2']


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        exclude = ['user']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'medical_conditions': forms.Textarea(attrs={'rows': 2}),
            'allergies': forms.Textarea(attrs={'rows': 2}),
            'medical_history_pdf': forms.FileInput(attrs={
            'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png',
            'class': 'form-control'
            }),
        }

    def clean_medical_history_pdf(self):
        f = self.cleaned_data.get('medical_history_pdf')
        if f:
            allowed_exts = ('.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png')
        if not f.name.lower().endswith(allowed_exts):
            raise forms.ValidationError('Allowed file types: PDF, DOC, DOCX, JPG, JPEG, PNG.')
        if f.size > 5 * 1024 * 1024:  # 5MB
            raise forms.ValidationError('File size must be no more than 5MB.')
        return f



class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        exclude = ['user']  # user will be set in the view
        widgets = {
            'qualifications': forms.Textarea(attrs={'rows': 2}),
            'expertise': forms.Textarea(attrs={'rows': 2}),
            'languages': forms.Textarea(attrs={'rows': 2}),
        }

#Generate Intervals
def generate_time_choices(start_hour=8, end_hour=18, interval_minutes=60):
    """
    Returns a list of tuples for Select choices:
    [('08:00', '08:00'), ('08:30', '08:30'), ...]
    From start_hour to end_hour inclusive of start, exclusive of end by default.
    """
    choices = []
    current = datetime(2000, 1, 1, start_hour, 0)
    end = datetime(2000, 1, 1, end_hour, 0)
    delta = timedelta(minutes=interval_minutes)
    while current <= end:
        label = current.strftime('%H:%M') # use '%I:%M %p' for AM/PM labels
        choices.append((label, label))
        current += delta
    return choices

TIME_CHOICES = generate_time_choices(start_hour=8, end_hour=17, interval_minutes=30)

#Doctorforms
class DateInput(forms.DateInput):
    input_type = 'date'

class DoctorAvailabilityForm(forms.ModelForm):
    start_time = forms.ChoiceField(choices=TIME_CHOICES)
    end_time = forms.ChoiceField(choices=TIME_CHOICES)

    class Meta:
        model = DoctorAvailability
        fields = ['date', 'start_time', 'end_time']
        widgets = {
            'date': DateInput(attrs={'min': datetime.today().date().isoformat()}),
        }

    def clean(self):
        cleaned = super().clean()
        # Convert selected strings to time objects
        start_str = cleaned.get('start_time')
        end_str = cleaned.get('end_time')
        if start_str:
            cleaned['start_time'] = datetime.strptime(start_str, '%H:%M').time()
        if end_str:
            cleaned['end_time'] = datetime.strptime(end_str, '%H:%M').time()

        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        if start and end and end <= start:
            raise forms.ValidationError("End time must be after start time.")
        return cleaned

#Equipment
class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['name', 'description', 'image', 'daily_rate', 'available']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
