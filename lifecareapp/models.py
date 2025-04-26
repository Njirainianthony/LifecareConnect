from django.db import models
from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager


# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(
        upload_to='doctor_profiles/',
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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
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
    charge_rates = models.CharField(max_length=50)
    profile_pic = models.ImageField(upload_to='doctor_profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} - Doctor"
    
    

