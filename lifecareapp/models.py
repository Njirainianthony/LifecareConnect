from django.db import models
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager


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
        upload_to='doctor_profiles/',  # or generalize it later
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
    profile_pic = models.ImageField(upload_to='patient_profiles/', blank=True, null=True)
    medical_history_pdf = models.FileField(upload_to='patient_medical_history/', blank=True, null=True)
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
    profile_pic = models.ImageField(upload_to='doctor_profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} - Doctor"


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
    
    # Existing fields
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # New fields to match your table headers
    appointment_type = models.CharField(
        max_length=50, 
        choices=APPOINTMENT_TYPE_CHOICES,
        default='consultation',
        help_text="Type of appointment"
    )
    date = models.DateField(null=True, blank=True, help_text="Appointment date")
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


# models.py
class Payment(models.Model):
    user = models.ForeignKey(PatientProfile, on_delete=models.CASCADE)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20)  # 'PAID' or 'FAILED'

"""    
class Booking(models.Model):
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, null=True)
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    date = models.DateField(default='2025-06-22')
    time = models.CharField(max_length=20, default='10:00 AM')
    status = models.CharField(max_length=20)  # 'BOOKED', 'CANCELLED'
"""