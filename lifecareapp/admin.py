from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import path
from django.template.response import TemplateResponse
from django.contrib.auth.admin import UserAdmin

from .models import Profile,PatientProfile,DoctorProfile,BaseUserManager,UserManager,Booking
from django.utils.translation import gettext_lazy as _

admin.site.site_header = _("Lifecare Management Admin")
admin.site.site_title = _("Lifecare Admin")
admin.site.index_title = _("Welcome to Lifecare Admin Portal")

# Register your models here.
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'date_of_birth', 'photo']
    raw_id_fields = ['user']



# Register models using the new admin
from .models import PatientProfile, DoctorProfile, Booking,Profile

admin.site.register(DoctorProfile)
admin.site.register(PatientProfile)

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'patient_full_name', 
        'doctor_full_name', 
        'appointment_type', 
        'status', 
        'date', 
        'queue_position',
        'cost',
        'created_at'
    )
    list_filter = (
        'status', 
        'appointment_type', 
        'date',
        'doctor__full_name',
    )
    search_fields = (
        'patient__full_name',
        'doctor__full_name',
        'appointment_type',
        'status',
    )
    ordering = ('-created_at',)

    def patient_full_name(self, obj):
        return obj.patient.full_name if obj.patient else "No patient"
    patient_full_name.short_description = 'Patient'

    def doctor_full_name(self, obj):
        return obj.doctor.full_name if obj.doctor else "No doctor"
    doctor_full_name.short_description = 'Doctor'


admin.site.register(Profile, ProfileAdmin)


