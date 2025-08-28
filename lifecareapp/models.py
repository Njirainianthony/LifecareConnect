from django.db import models
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.core.validators import FileExtensionValidator
from django.utils import timezone

created_at = models.DateTimeField(default=timezone.now)  # TEMP



# Create your models here.
class Profile(models.Model):
    USER_TYPE_CHOICES = (
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='patient')
    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(
        upload_to='doctors/',  # or generalize it later
        blank=True
    )

    def __str__(self):
        return f'Profile of {self.user.username}'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class PatientProfile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_profiles')
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.CharField(max_length=255)
    gender = models.CharField(max_length=10)
    county = models.CharField(max_length=50)
    dob = models.DateField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    medical_conditions = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    preferred_care_type = models.CharField(max_length=100, blank=True)
    profile_pic = models.ImageField(upload_to='dashboard_patient/', blank=True, null=True)
    medical_history_pdf = models.FileField(upload_to='patient_medical_history/', blank=True, null=True, validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])])
    medical_history_uploaded_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.full_name} - Patient"

class DoctorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    professional_title = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50)
    qualifications = models.TextField()
    expertise = models.TextField()
    languages = models.TextField()
    available_location = models.CharField(max_length=100)
    contact = models.CharField(max_length=20)
    email = models.EmailField()
    charge_rates = models.FloatField(max_length=50)
    profile_pic = models.ImageField(upload_to='doctors/', blank=True, null=True)
    # Time slot fields
    #start_time = models.TimeField(default='08:00')
    #end_time = models.TimeField(default='17:00')
    #slot_duration = models.IntegerField(default=30, help_text="Duration in minutes")

    def __str__(self):
        return f"{self.full_name} - Doctor"


# models.py
class Booking(models.Model):
    APPOINTMENT_TYPE_CHOICES = [
        ('consultation', 'Consultation'),
        ('checkup', 'General Checkup'),
        ('follow_up', 'Follow-up'),
        ('emergency', 'Emergency'),
        ('specialist', 'Specialist Visit'),
        ('lab_test', 'Laboratory Test'),
        ('vaccination', 'Vaccination'),
        ('physical_therapy', 'Physical Therapy'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Core fields
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=timezone.now)
    
    # Appointment details
    appointment_type = models.CharField(
        max_length=50, 
        choices=APPOINTMENT_TYPE_CHOICES,
        default='consultation',
        help_text="Type of appointment"
    )
    date = models.DateField(null=True, blank=True, help_text="Appointment date")
    time = models.CharField(max_length=10, null=True, blank=True, help_text="Appointment time (HH:MM format)")
    cost = models.DecimalField(
        null=True,
        blank=True,
        max_digits=10, 
        decimal_places=2,
        help_text="Cost of appointment in KES"
    )
    queue_position = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Position in queue for the appointment"
    )

    class Meta:
        ordering = ['-created_at']
        unique_together = [['doctor', 'date', 'time']]  # Prevent double booking

    def __str__(self):
        return f"{self.patient.full_name} -> {self.doctor.full_name} ({self.date} at {self.time})"
    
    @property
    def formatted_date_time(self):
        """Return formatted date and time string"""
        if self.date and self.time:
            return f"{self.date.strftime('%B %d, %Y')} at {self.time}"
        return "Date/Time not set"


# models.py
class Payment(models.Model):
    user = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20)  # 'PAID' or 'FAILED'
    created_at = models.DateTimeField(auto_now_add=True)   # <- add this & migrate if you want time-series revenue

"""    
class Booking(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, null=True)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    date = models.DateField(default='2025-06-22')
    time = models.CharField(max_length=20, default='10:00 AM')
    status = models.CharField(max_length=20)  # 'BOOKED', 'CANCELLED'
"""

#Doctor Availability
class DoctorAvailability(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='availability_slots')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.IntegerField(default=30, help_text="Duration in minutes")
    created_at = models.DateTimeField(auto_now_add=True)

    def get_formatted_time_slots(self):
        """
        Generate time slots based on start_time, end_time, and slot_duration
        Returns a list of formatted time strings
        """
        from datetime import datetime, timedelta
        
        if not self.start_time or not self.end_time:
            return []
        
        slots = []
        current_time = datetime.combine(datetime.today(), self.start_time)
        end_time = datetime.combine(datetime.today(), self.end_time)
        
        while current_time < end_time:
            # Format time as HH:MM (24-hour) or use strftime('%I:%M %p') for 12-hour with AM/PM
            slots.append(current_time.strftime('%H:%M'))
            current_time += timedelta(minutes=self.slot_duration)
        
        return slots
    
    def get_available_slots_for_date(self, date):
        """
        Get available time slots for a specific date
        Returns slots that are not booked
        """

        from datetime import datetime
        
        all_slots = self.get_formatted_time_slots()
        
        # Get booked slots for this date
        booked_slots = Booking.objects.filter(
            doctor=self.doctor,
            date=date,
            status__in=['accepted', 'pending']
        ).values_list('time', flat=True)
        
        # Convert booked times to same format
        booked_times = [slot.strftime('%H:%M') for slot in booked_slots if slot]
        
        # Return available slots
        available_slots = [slot for slot in all_slots if slot not in booked_times]
        
        return available_slots

    class Meta:
        # Prevent a doctor from creating the exact same slot twice
        unique_together = ('doctor', 'date', 'start_time', 'end_time')
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"Dr. {self.doctor.full_name} - {self.date} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

#Equipment Leasing
class Equipment(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='equipment/', blank=True, null=True)
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)


    def __str__(self):
        return self.name