from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from .models import PatientProfile, DoctorProfile, Profile, Booking, Payment
from .forms import UserRegistrationForm, PatientProfileForm, DoctorProfileForm, UserEditForm, ProfileEditForm
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q 
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.http import HttpResponse
from django_daraja.mpesa.core import MpesaClient
import requests
import json
from django.views.decorators.csrf import csrf_exempt



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

@login_required
def add_profile(request):
    return render(request,'addprofile.html')


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
            # Create user but don't save yet
            new_user = user_form.save(commit=False)
            new_user.set_password(user_form.cleaned_data['password'])
            new_user.save()

            # Get the user_type from the cleaned form data
            user_type = user_form.cleaned_data.get('user_type')

            # Create their general Profile and save user_type
            Profile.objects.create(user=new_user, user_type=user_form.cleaned_data['user_type'])


            # Automatically log the user in
            login(request, new_user)

            # Redirect based on user_type
            return redirect('addprofile')  # we’ll handle view logic there based on user_type
        else:
            return render(request, 'signup.html', {'user_form': user_form})
    else:
        user_form = UserRegistrationForm()
        return render(request, 'signup.html', {'user_form': user_form})
    

def custom_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Check if the user has a PatientProfile
            if PatientProfile.objects.filter(user=user).exists():
                return redirect('list_patient_profiles')  # correct redirect for patient
            # Check if the user has a DoctorProfile
            elif DoctorProfile.objects.filter(user=user).exists():
                return redirect('dashboard_doctor')
            # If neither profile exists, send them to create one
            else:
                return redirect('addprofile')

        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')
    
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
@login_required
def create_patient_profile(request):
    if request.method == 'POST':
        form = PatientProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            return redirect('list_patient_profiles')  # A view that shows all profiles for this user
    else:
        form = PatientProfileForm()

    return render(request, 'patientform.html', {'form': form})

#FOR SHOWING ALL THE PATIENT PROFILES
@login_required
def list_patient_profiles(request):
    profiles = PatientProfile.objects.filter(user=request.user)
    return render(request, 'list_patients_profile.html', {'profiles': profiles})



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
def dashboard_patient(request, profile_id):
    profile = get_object_or_404(PatientProfile, id=profile_id, user=request.user)
    bookings = Booking.objects.filter(patient=profile)
    return render(request, 'dashboard_patient.html', {
        'profile': profile,
        'bookings': bookings,
    })

@login_required
def dashboard_doctor(request):
    try:
        profile = DoctorProfile.objects.get(user=request.user)
        bookings = Booking.objects.filter(doctor=profile, status='pending')
        return render(request, 'dashboard_doctor.html', {
            'profile': profile,
            'bookings': bookings,
        })
    except DoctorProfile.DoesNotExist:
        return redirect('add_profile')  # fallback in case no doctor profile yet

        
#Update booking status
@login_required
def update_booking_status(request, booking_id, decision):
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Security check: Ensure only the doctor associated with this booking can update it
    if request.user != booking.doctor.user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    if decision in ['accepted', 'declined']:
        booking.status = decision
        booking.save()
        
        # Notify the patient
        try:
            notify_patient(booking)
        except Exception as e:
            print(f"Error sending notification to patient: {str(e)}")
            # Continue anyway, don't block the status update
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'booking_status': booking.status})
    
    # If not AJAX, redirect to dashboard
    return redirect('dashboard')    

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

#Appointment View
@login_required
def book_doctor_ajax(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    
    try:
        patient = PatientProfile.objects.get(user=request.user)  # Fixed typo: object -> objects
    except PatientProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Patient profile not found'}, status=400)

    # Check if a pending or accepted booking already exists
    existing_booking = Booking.objects.filter(
        patient=patient,
        doctor=doctor,
        status__in=['pending', 'accepted']
    ).first()
    
    if existing_booking:
        return JsonResponse({'status': 'already_pending'})
    
    # Create new booking
    booking = Booking.objects.create(
        patient=patient,
        doctor=doctor,
        status='pending'
    )
    
    try:
        notify_doctor(booking)
        return JsonResponse({'status': 'pending'})
    except Exception as e:
        # Log the error and return a more detailed message
        print(f"Email notification error: {str(e)}")
        booking.delete()  # Rollback booking if email fails
        return JsonResponse({'status': 'error', 'message': 'Could not send notification email'}, status=500)


def notify_patient(booking):
    patient_email = booking.patient.user.email
    status = booking.status
    doctor_name = f"Dr. {booking.doctor.user.get_full_name()}"
    
    subject = 'Appointment Update'
    message = f'Your appointment request to {doctor_name} was {status}.'
    
    if booking.status == 'accepted':
        message += '\n\nPlease contact the doctor for further details.'
    elif booking.status == 'declined':
        message += '\n\nYou may try booking with another healthcare provider.'
    
    send_mail(
        subject,
        message,
        'noreply@lifecareconnect.com',
        [patient_email],
        fail_silently=False
    )

def notify_doctor(booking):
    doctor_email = booking.doctor.user.email
    patient_name = booking.patient.user.get_full_name()
    subject = f"New Appointment Request From {patient_name}"
    
    accept_url = f"https://lifecareconnect.com/booking/{booking.id}/accepted/"
    decline_url = f"https://lifecareconnect.com/booking/{booking.id}/declined/"
    
    message = (
        f"You have a new appointment request from {patient_name}.\n\n"
        f"Please log in to your dashboard to view the request and accept or decline it.\n\n"
        f"Booking ID: {booking.id}\n"
        f"Patient Profile: https://lifecareconnect.com/patient/{booking.patient.id}/profile/\n\n"
        f"Quick actions:\n"
        f"Accept: {accept_url}\n"
        f"Decline: {decline_url}"
    )
    
    send_mail(
        subject,
        message,
        'noreply@lifecareconnect.com',
        [doctor_email],
        fail_silently=False
    )

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        return redirect('home')
    return redirect('dashboard')

@login_required
def appointments(request):
    patient_profile = PatientProfile.objects.get(user=request.user)
    appointments = Booking.objects.filter(patient=patient_profile)
    return render(request, 'appointments.html', {'appointments': appointments})

@login_required
def view_doctor_profile(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    charge_rate = float(doctor.charge_rates)
    commission = float(doctor.charge_rates) * 0.2
    total_fee = charge_rate + commission
    return render(request, 'doctor_profile.html', {
        'doctor': doctor, 
        'commission': commission, 
        'charge_rate': charge_rate,
        'total_fee': total_fee,})

@csrf_exempt
def initiate_stk_push(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone')
            amount = int(data.get('amount'))
            doctor_id = data.get('doctor_id')

            # Get user and doctor
            user = request.user
            doctor = DoctorProfile.objects.get(id=doctor_id)

            print(f"STK Request received: {phone_number}, amount={amount}")

            cl = MpesaClient()
            account_reference = 'LifecarePayment'
            transaction_desc = 'Payment for services'
            callback_url = 'https://mydomain.com/path'

            response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)

            # === Booking: either get from request or create here ===
            from lifecareapp.models import Booking  # if not already imported
            booking = Booking.objects.create(
                doctor=doctor,
                patient=user.patientprofile,  # adjust if your PatientProfile is accessed differently
                status='pending'
            )

            # === Email Notification Functions ===
            def notify_patient(booking):
                patient_email = booking.patient.user.email
                doctor_name = f"Dr. {booking.doctor.user.get_full_name()}"

                subject = 'Appointment Request Sent'
                message = f'Your appointment request to {doctor_name} has been received and is pending review.\n\nYou will be notified once the doctor responds.'

                send_mail(
                    subject,
                    message,
                    'noreply@lifecareconnect.com',
                    [patient_email],
                    fail_silently=False
                )

            def notify_doctor(booking):
                doctor_email = booking.doctor.user.email
                patient_name = booking.patient.user.get_full_name()
                subject = f"New Appointment Request from {patient_name}"

                accept_url = f"https://lifecareconnect.com/booking/{booking.id}/accepted/"
                decline_url = f"https://lifecareconnect.com/booking/{booking.id}/declined/"

                message = (
                    f"You have a new appointment request from {patient_name}.\n\n"
                    f"Please log in to your dashboard to respond.\n\n"
                    f"Booking ID: {booking.id}\n"
                    f"Patient Profile: https://lifecareconnect.com/patient/{booking.patient.id}/profile/\n\n"
                    f"Quick actions:\n"
                    f"Accept: {accept_url}\n"
                    f"Decline: {decline_url}"
                )

                send_mail(
                    subject,
                    message,
                    'noreply@lifecareconnect.com',
                    [doctor_email],
                    fail_silently=False
                )

            # === Actually send the emails ===
            notify_patient(booking)
            notify_doctor(booking)

            return JsonResponse({'status': 'success', 'response': response.text})

        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

'''
@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        print("M-Pesa Callback received:", data)  # Optional: for testing

        # Here you can extract info like amount, phone number, result code, etc.
        result_code = data['Body']['stkCallback']['ResultCode']
        if result_code == 0:
            # Payment successful
            amount = data['Body']['stkCallback']['CallbackMetadata']['Item'][0]['Value']
            phone = data['Body']['stkCallback']['CallbackMetadata']['Item'][4]['Value']
            print(f"Payment received: {amount} from {phone}")
            # You can save this info to your database

        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
'''

@csrf_exempt
def stk_push(request):
    if request.method == "POST":
        data = json.loads(request.body)
        phone = data.get("phone")
        amount = data.get("amount")
        doctor_id = data.get("doctor_id")
        date = data.get("appointment_date")
        time = data.get("appointment_time")

        #Call STK push logic
        success = initiate_stk_push(request)

        if success:
            #Save payment and appointment details
            doctor = DoctorProfile.objects.get(id=doctor_id)
            patient_profile = PatientProfile.objects.get(user=request.user)
            user = request.user  # Or however you're managing logged-in users

            payment = Payment.objects.create(
                user=patient_profile,
                doctor=doctor,
                amount=amount,
                status="PAID"
            )

            appointment = Booking.objects.create(
                user=user,
                doctor=doctor,
                date=date,
                time=time,
                status="BOOKED"
            )

            # 3. Trigger post-payment logic
            handler = PaymentEventHandler(payment, appointment)
            handler.handle_success()

            return JsonResponse({"status": "success"})

        return JsonResponse({"status": "fail", "message": "STK Push failed"})