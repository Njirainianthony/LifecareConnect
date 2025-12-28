from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import path
from django.template.response import TemplateResponse
from django.contrib.auth.admin import UserAdmin

from .models import Profile,PatientProfile,DoctorProfile,BaseUserManager,UserManager,Booking, Equipment
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
        'date', 
        'time',  # Use the 'time' field which exists
        'status', 
        'cost',
        'created_at'
    )
    list_filter = (
        'status', 
        'date',
        'doctor', # Filter by the foreign key relationship directly
    )
    search_fields = (
        'patient__username', # Search by username on the related User model
        'doctor__full_name', # Search by full_name on the related DoctorProfile model
        'status',
    )
    ordering = ('-date', 'time')

    def patient_full_name(self, obj):
        # Use get_full_name() for the default User model or fallback to username
        return obj.patient.get_full_name() or obj.patient.username
    patient_full_name.short_description = 'Patient'

    def doctor_full_name(self, obj):
        return obj.doctor.full_name if obj.doctor else "No doctor"
    doctor_full_name.short_description = 'Doctor'

admin.site.register(Profile, ProfileAdmin)


#Equipment
@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'daily_rate', 'available')
    list_filter = ('available',)
    search_fields = ('name',)