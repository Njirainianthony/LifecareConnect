from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import PatientProfile, DoctorProfile, Profile
from .forms import UserRegistrationForm, PatientProfileForm, DoctorProfileForm, UserEditForm, ProfileEditForm
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q 
from django.core.paginator import Paginator


# Create your views here.
def index(request):
    return render(request, 'index.html')

def inner(request):
    return render(request, 'inner-page.html')

def about(request):
    return render(request, 'about.html')

def services(request):
    return render(request, 'services.html')

def departments(request):
    return render(request, 'departments.html')

def doctors(request):
    query = request.GET.get('q')
    doctors_list = DoctorProfile.objects.all()

    if query:
        doctors_list = doctors_list.filter(
            Q(full_name__icontains=query) |
            Q(expertise__icontains=query) |
            Q(available_location__icontains=query)
        )

    paginator = Paginator(doctors_list, 6)  # Show 6 doctors per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'doctors.html', {'page_obj': page_obj})

def contact(request):
    return render(request, 'contact.html')

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
            #Create the user profile
            Profile.objects.create(user=new_user)
            #Add a success message
            messages.success(request, "Your account has been successfully created. You can now log in.")
            return redirect(reverse('login'))
        #This handles invalid forms
        else:
            return render(
                request,
                'signup.html',
                {'user_form': user_form}
            )
    else:
        user_form = UserRegistrationForm()
        return render(
            request,
            'signup.html',
            {'user_form': user_form}
        )
    
@login_required
def edit(request):
    if request.method == 'POST':
        user_form = UserEditForm(
            instance=request.user,
            data=request.POST
        )
        profile_form = ProfileEditForm(
            instance=request.user.profile,
            data=request.POST,
            files=request.FILES
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)
        return render(
            request,
            'edit.html',
            {'user_form': user_form,
             'profile_form': profile_form
             }
        )

def user_logout(request):
    logout(request)
    return redirect('login')


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

