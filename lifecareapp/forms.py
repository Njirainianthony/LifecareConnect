from django import forms
from django.contrib.auth import get_user_model
from .models import PatientProfile, DoctorProfile, Profile

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
        exclude = ['user']  # user will be set in the view
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'medical_conditions': forms.Textarea(attrs={'rows': 2}),
            'allergies': forms.Textarea(attrs={'rows': 2}),
        }

class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        exclude = ['user']  # user will be set in the view
        widgets = {
            'qualifications': forms.Textarea(attrs={'rows': 2}),
            'expertise': forms.Textarea(attrs={'rows': 2}),
            'languages': forms.Textarea(attrs={'rows': 2}),
        }