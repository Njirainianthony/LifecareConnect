from django.contrib import admin
from .models import Profile,PatientProfile,DoctorProfile,BaseUserManager,UserManager,Booking

# Register your models here.
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'date_of_birth', 'photo']
    raw_id_fields = ['user']

admin.site.register(PatientProfile)
admin.site.register(Booking)
admin.site.register(DoctorProfile)
#admin.site.register(UserManager)


