from django import template
from django.urls import reverse
from lifecareapp.models import Profile, DoctorProfile

register = template.Library()

@register.simple_tag
def get_dashboard_url(user):
    if user.is_superuser or user.is_staff:
        return reverse('admin_dashboard')  # Update with correct URL name
    try:
        profile = Profile.objects.get(user=user)
        if profile.user_type == 'doctor':
            return reverse('dashboard_doctor')
        elif profile.user_type == 'patient':
            return reverse('list_patient_profiles')
    except Profile.DoesNotExist:
        pass
    return "#"  # fallback

@register.simple_tag
def get_dashboard_label(user):
    if user.is_superuser or user.is_staff:
        return "My Dashboard"
    try:
        profile = Profile.objects.get(user=user)
        if profile.user_type == 'doctor':
            return "My Dashboard"
        elif profile.user_type == 'patient':
            return "My Profiles"
    except Profile.DoesNotExist:
        pass
    return "Dashboard"
