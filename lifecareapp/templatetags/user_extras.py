from django import template
from lifecareapp.models import PatientProfile, DoctorProfile

register = template.Library()

@register.simple_tag
def get_dashboard_url(user):
    try:
        patient_profile = PatientProfile.objects.filter(user=user).first()
        if patient_profile:
            return f"/dashboard/patient/{patient_profile.id}/"
    except:
        pass

    try:
        doctor_profile = DoctorProfile.objects.get(user=user)
        return "/dashboard/doctor/"
    except:
        pass

    return "/"
