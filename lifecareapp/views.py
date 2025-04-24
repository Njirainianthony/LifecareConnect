from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
#from .models import PatientProfile, DoctorProfile
from .forms import UserRegistrationForm, PatientProfileForm, DoctorProfileForm
from django.contrib import messages

# Create your views here.
def index(request):
    return render(request, 'index.html')

def inner(request):
    return render(request, 'inner-page.html')

def signup(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            #Create a new user object but avoid saving it yet
            new_user = user_form.save(commit=False)
            #Set the chosen password
            new_user.set_password(
                user_form.cleaned_data['password']
            )
            #Save the user object
            new_user.save()
            return render(
                request,
                'signup_done.html',
                {'new_user': new_user}
            )
    else:
        user_form = UserRegistrationForm()
        return render(
            request,
            'signup.html',
            {'user_form': user_form}
        )

@login_required
def dashboard(request):
    return render(
        request,
        'dashboard_patient.html',
        {'section': 'dashboard'}
    )

def user_logout(request):
    logout(request)
    return redirect('login')

"""
@login_required
def add_profile(request):
    return render(request, 'addprofile.html')


# --- Patient Form View ---
@login_required
def patient_form(request):
    if PatientProfile.objects.filter(user=request.user).exists():
        return redirect('dashboard')

    if request.method == 'POST':
        form = PatientProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            return redirect('dashboard')
    else:
        form = PatientProfileForm()

    return render(request, 'patientform.html', {'form': form})


# --- Doctor Form View ---
@login_required
def doctor_form(request):
    if DoctorProfile.objects.filter(user=request.user).exists():
        return redirect('dashboard')

    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            return redirect('dashboard')
    else:
        form = DoctorProfileForm()

    return render(request, 'doctorform.html', {'form': form})


# --- Dashboard View ---
@login_required
def dashboard(request):
    try:
        profile = PatientProfile.objects.get(user=request.user)
        return render(request, 'dashboard_patient.html', {'profile': profile})
    except PatientProfile.DoesNotExist:
        try:
            profile = DoctorProfile.objects.get(user=request.user)
            return render(request, 'dashboard_doctor.html', {'profile': profile})
        except DoctorProfile.DoesNotExist:
            return redirect('add_profile')
        

@login_required
def edit_patient_profile(request):
    try:
        profile = PatientProfile.objects.get(user=request.user)
    except PatientProfile.DoesNotExist:
        return redirect('patientform')

    if request.method == 'POST':
        form = PatientProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Patient profile updated successfully.")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PatientProfileForm(instance=profile)

    return render(request, 'edit_patient_profile.html', {'form': form})


def edit_doctor_profile(request):
    try:
        profile = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return redirect('doctorform')

    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Doctor profile updated successfully.")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DoctorProfileForm(instance=profile)

    return render(request, 'edit_doctor_profile.html', {'form': form})

"""