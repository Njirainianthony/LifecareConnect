from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required,user_passes_test
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from .models import PatientProfile, DoctorProfile, Profile, Booking, Payment, DoctorAvailability, Equipment, EquipmentRequest
from .forms import UserRegistrationForm, PatientProfileForm, DoctorProfileForm, UserEditForm, ProfileEditForm, EquipmentForm, DoctorAvailabilityForm, DoctorWorkingHoursForm
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
from django.utils.timezone import now
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count, Sum
from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import os





# Create your views here.
def index(request):
    return render(request, 'index.html')

def inner(request):
    return render(request, 'inner-page.html')

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

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
    from django.contrib.auth.forms import AuthenticationForm
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if user.is_superuser or user.is_staff:
                return redirect('admin_dashboard_home')

            try:
                profile = Profile.objects.get(user=user)
            except Profile.DoesNotExist:
                messages.error(request, "Profile not found.")
                return redirect('custom_login_view')

            if profile.user_type == 'doctor':
                if DoctorProfile.objects.filter(user=user).exists():
                    return redirect('dashboard_doctor')
                else:
                    return redirect('doctorform')

            elif profile.user_type == 'patient':
                return redirect('list_patient_profiles')

            else:
                messages.error(request, "User role is invalid.")
                return redirect('custom_login_view')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        # Clear any stale messages from previous sessions (e.g. admin messages,
        # profile updates, etc.) to prevent them from being shown to other users
        # on the login page. We directly flush the message storage.
        storage = messages.get_messages(request)
        storage.used = True
        # Also clear from session directly to be thorough
        if hasattr(request, '_messages'):
            del request._messages
        if '_messages' in request.session:
            del request.session['_messages']
            request.session.modified = True
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})


# Removed duplicate CustomLoginView class that was overwriting the function above


@login_required
def redirect_after_login(request):
    user = request.user

    if user.is_superuser or user.is_staff:
        return redirect('admin_dashboard_home')

    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        return redirect('custom_login_view')  # or somewhere else like profile setup

    if profile.user_type == 'doctor':
        if DoctorProfile.objects.filter(user=user).exists():
            return redirect('dashboard_doctor')
        else:
            return redirect('doctorform')

    elif profile.user_type == 'patient':
        return redirect('list_patient_profiles')

    return redirect('home')

    
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
def create_patient_profile(request):
    if request.method == 'POST':
        form = PatientProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            if profile.consent_accepted:
                profile.consent_date = timezone.now()
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

@login_required
def set_active_profile(request, profile_id):
    try:
        profile = PatientProfile.objects.get(id=profile_id, user=request.user)
        request.session["active_profile_id"] = profile.id  # 👈 save profile in session
    except PatientProfile.DoesNotExist:
        return redirect("list_patient_profiles")  # fallback if invalid id

    return redirect("dashboard_patient", profile_id=profile.id)  # or wherever you want to send them next


# --- Doctor Form View ---
@login_required
def doctor_form(request):
    if DoctorProfile.objects.filter(user=request.user).exists():
        return redirect('dashboard_doctor')

    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            
            # Record consent timestamp
            if profile.consent_accepted:
                profile.consent_date = timezone.now()
            
            # Handle available_days checkboxes - get all selected values and join with comma
            available_days_list = request.POST.getlist('available_days')
            if available_days_list:
                profile.available_days = ','.join(available_days_list)
            else:
                profile.available_days = 'monday,tuesday,wednesday,thursday,friday'  # default
            
            profile.save()
            return redirect('dashboard_doctor')
    else:
        form = DoctorProfileForm()

    return render(request, 'doctorform.html', {'form': form})


# --- Dashboard View ---
@login_required
def dashboard_patient(request, profile_id):
    profile = get_object_or_404(PatientProfile, id=profile_id)
    bookings = Booking.objects.filter(patient=profile).order_by('date', 'time')
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
        return redirect('addprofile')  # fallback in case no doctor profile yet

        
#Update booking status
@login_required
def update_appointment_status(request, booking_id):
    """
    Unified view to handle all appointment status updates from the doctor.
    Supports 'accept', 'decline', and 'complete' actions.
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Security check: Ensure only the assigned doctor can update the booking
    if request.user != booking.doctor.user:
        messages.error(request, "Unauthorized action.")
        return redirect('appointments')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accept':
            booking.status = Booking.AppointmentStatus.ACCEPTED
            messages.success(request, f"Appointment with {booking.patient.full_name} accepted.")
            
        elif action == 'decline':
            decline_reason = request.POST.get('decline_reason', '').strip()
            if not decline_reason:
                messages.error(request, "Please provide a reason for declining.")
                return redirect('appointments')
            
            booking.status = Booking.AppointmentStatus.DECLINED
            booking.decline_reason = decline_reason
            messages.success(request, f"Appointment with {booking.patient.full_name} declined.")
            
        elif action == 'complete':
            # Handle phone number for payment request
            phone_number = request.POST.get('payment_phone', '').strip()
            if not phone_number:
                phone_number = booking.patient.phone or ""
            
            # Format phone number to 254XXXXXXXXX format
            phone_number = phone_number.replace('+', '').replace(' ', '').replace('-', '')
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif phone_number and not phone_number.startswith('254'):
                phone_number = '254' + phone_number
                
            booking.status = Booking.AppointmentStatus.COMPLETED
            booking.save() # Save before initiating payment flow
            
            # Initiate payment via M-Pesa STK Push
            success, message = initiate_payment_for_booking(booking, phone_number)
            if success:
                messages.success(request, f"Appointment completed. {message}")
            else:
                messages.warning(request, f"Appointment completed, but payment request failed: {message}")
                
            return redirect('appointments')
            
        else:
            messages.error(request, "Invalid action.")
            return redirect('appointments')
            
        booking.save()
        
        # Send Notification to Patient
        try:
            notify_patient(booking)
            booking.patient_notified = True
            booking.save()
        except Exception as e:
            print(f"Error notifying patient: {e}")
            
    return redirect('appointments')


@login_required
def edit_patient_profile(request):
    profile_id = request.session.get("active_profile_id")
    if profile_id:
        try:
            profile = PatientProfile.objects.get(id=profile_id, user=request.user)
        except PatientProfile.DoesNotExist:
            profile = PatientProfile.objects.filter(user=request.user).first()
    else:
        profile = PatientProfile.objects.filter(user=request.user).first()
        
    if not profile:
        return redirect('patientform')

    if request.method == 'POST':
        form = PatientProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Patient profile updated successfully.")
            return redirect('dashboard_patient', profile_id=profile.id)
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
            updated_profile = form.save(commit=False)
            
            # Handle available_days checkboxes 
            available_days_list = request.POST.getlist('available_days')
            if available_days_list:
                updated_profile.available_days = ','.join(available_days_list)
            else:
                updated_profile.available_days = 'monday,tuesday,wednesday,thursday,friday'  # default
            
            updated_profile.save()
            messages.success(request, "Doctor profile updated successfully.")
            return redirect('dashboard_doctor')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DoctorProfileForm(instance=profile)

    # Pass the current available days for checkbox state
    current_days = profile.get_available_days_list()
    return render(request, 'edit_doctor_profile.html', {'form': form, 'current_days': current_days})

#Appointment View
"""
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
"""

def notify_doctor(booking):
    doctor_email = booking.doctor.user.email
    patient_name = booking.patient.full_name
    subject = f"New Appointment Request From {patient_name}"
    
    accept_url = f"https://lifecareconnect.com/booking/{booking.id}/accepted/"
    decline_url = f"https://lifecareconnect.com/booking/{booking.id}/declined/"
    
    message = (
        f"You have a new appointment request from {patient_name}.\n\n"
        f"Please log in to your dashboard to view the request and accept or decline it.\n\n"
        f"Booking ID: {booking.id}\n"
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
    # Check if the logged-in user has a doctor profile
    is_doctor = hasattr(request.user, 'doctorprofile')
    
    if is_doctor:
        # Doctor's view: Get all bookings for this doctor
        appointments = Booking.objects.filter(
            doctor=request.user.doctorprofile
        ).order_by('date', 'time')
    else:
        # Patient's view: Respect active profile selection
        profile_id = request.session.get("active_profile_id")
        if profile_id:
            try:
                patient_profile = PatientProfile.objects.get(
                    id=profile_id,
                    user=request.user
                )
                appointments = Booking.objects.filter(
                    patient=patient_profile
                ).order_by('date', 'time')
            except PatientProfile.DoesNotExist:
                appointments = []  # Graceful fallback if session invalid
        else:
            appointments = []  # No active profile selected

    context = {
        'appointments': appointments,
        'is_doctor': is_doctor
    }
    return render(request, 'appointments.html', context)




@login_required
def cancel_booking(request, booking_id):
    """Allow patient to cancel their booking"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Verify the patient owns this booking
    profile_id = request.session.get("active_profile_id")
    if not profile_id or booking.patient.id != profile_id:
        messages.error(request, "Unauthorized action.")
        return redirect('appointments')
    
    # Can only cancel pending or accepted bookings
    if booking.status in ['pending', 'accepted']:
        booking.status = Booking.AppointmentStatus.CANCELLED
        booking.save()
        
        # Notify doctor about cancellation
        try:
            notify_doctor_cancellation(booking)
            messages.success(request, "Appointment cancelled successfully. The doctor has been notified.")
        except Exception as e:
            print(f"Notification error: {e}")
            messages.success(request, "Appointment cancelled successfully.")
    else:
        messages.error(request, "This booking cannot be cancelled.")
    
    return redirect('appointments')


def notify_doctor_cancellation(booking):
    """Send email to doctor when patient cancels"""
    doctor_email = booking.doctor.email
    patient_name = booking.patient.full_name
    subject = f"Appointment Cancelled by {patient_name}"
    
    message = (
        f"Dear Dr. {booking.doctor.full_name},\n\n"
        f"The appointment scheduled for {booking.date} at {booking.time} "
        f"with {patient_name} has been cancelled by the patient.\n\n"
        "Best regards,\nLifecare Connect"
    )
    
    send_mail(
        subject,
        message,
        'noreply@lifecareconnect.com',
        [doctor_email],
        fail_silently=False
    )


@login_required
def view_patient_profile_for_doctor(request, patient_id, booking_id):
    """
    Allow doctor to view patient profile after a booking is made
    """
    booking = get_object_or_404(Booking, id=booking_id)
    
    # Security: Only the assigned doctor can view
    if request.user != booking.doctor.user:
        messages.error(request, "You are not authorized to view this profile.")
        return redirect('appointments')
    
    patient = get_object_or_404(PatientProfile, id=patient_id)
    
    # Ensure the patient in the URL matches the booking
    if booking.patient.id != patient.id:
        messages.error(request, "Invalid patient-booking combination.")
        return redirect('appointments')
    
    context = {
        'patient': patient,
        'booking': booking,
    }
    return render(request, 'patient_profile_detail.html', context)




        
@csrf_exempt
def initiate_stk_push(phone_number, amount, doctor, booking):
    """
    Function version of STK push you can call from complete_booking
    """
    try:
        cl = MpesaClient()
        account_reference = 'LifecarePayment'
        transaction_desc = f'Payment for services with Dr. {doctor.full_name}'
        callback_url = 'https://mydomain.com/path'

        # Actual STK push call
        response = cl.stk_push(phone_number, amount, account_reference, transaction_desc, callback_url)

        # Send notifications
        from .utils import notify_patient, notify_doctor
        notify_patient(booking)
        notify_doctor(booking)

        return True, response.text

    except Exception as e:
        print(f"Error in STK Push: {e}")
        return False, str(e)


@csrf_exempt
def mpesa_callback(request):
    """
    Handle M-Pesa STK Push callback.
    Updates Payment and Booking status when payment is confirmed.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("M-Pesa Callback received:", json.dumps(data, indent=2))
            
            # Extract callback data
            stk_callback = data.get('Body', {}).get('stkCallback', {})
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc', '')
            checkout_request_id = stk_callback.get('CheckoutRequestID', '')
            
            if result_code == 0:
                # Payment successful - extract metadata
                callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                
                amount = None
                phone = None
                mpesa_receipt = None
                
                for item in callback_metadata:
                    if item.get('Name') == 'Amount':
                        amount = item.get('Value')
                    elif item.get('Name') == 'MpesaReceiptNumber':
                        mpesa_receipt = item.get('Value')
                    elif item.get('Name') == 'PhoneNumber':
                        phone = item.get('Value')
                
                print(f"Payment SUCCESS: Amount={amount}, Phone={phone}, Receipt={mpesa_receipt}")
                
                # Find and update the pending payment by matching amount and phone
                # First try to find by phone number
                phone_str = str(phone) if phone else ''
                
                pending_payments = Payment.objects.filter(
                    status='PENDING',
                    amount=amount
                )
                
                if pending_payments.exists():
                    # Update the most recent pending payment
                    payment = pending_payments.order_by('-created_at').first()
                    payment.status = 'COMPLETED'
                    payment.mpesa_receipt = mpesa_receipt if hasattr(payment, 'mpesa_receipt') else None
                    payment.save()
                    
                    # Update the associated booking to PAID
                    if payment.booking:
                        payment.booking.status = Booking.AppointmentStatus.PAID
                        payment.booking.save()
                        print(f"Booking {payment.booking.id} updated to PAID")
                    
                    print(f"Payment {payment.id} marked as COMPLETED")
                else:
                    print(f"No pending payment found for amount {amount}")
                    
            else:
                # Payment failed or cancelled
                print(f"Payment FAILED: {result_desc}")
            
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
            
        except Exception as e:
            print(f"Error processing M-Pesa callback: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
    
    return JsonResponse({"ResultCode": 1, "ResultDesc": "Invalid request method"})


@csrf_exempt
def stk_push(patient_profile, doctor, amount, booking):
    try:
        # Call Safaricom API client directly
        cl = MpesaClient()
        account_reference = 'LifecarePayment'
        transaction_desc = 'Payment for services'
        callback_url = 'https://mydomain.com/path'

        response = cl.stk_push(
            phone_number=patient_profile.user.phone,
            amount=amount,
            account_reference=account_reference,
            transaction_desc=transaction_desc,
            callback_url=callback_url
        )

        # If API responded successfully
        if response.ok:
            payment = Payment.objects.create(
                user=patient_profile,
                doctor=doctor,
                amount=amount,
                status="PENDING"
            )

            booking.status = Booking.AppointmentStatus.PENDING_PAYMENT
            booking.save()

            # You can notify both doctor & patient here if needed
            notify_patient(booking)
            notify_doctor(booking)

            return True
        else:
            print("STK Push failed:", response.text)
            return False

    except Exception as e:
        print("STK Push error:", str(e))
        return False




#ADMIN STUff

# Check if user is admin (superuser)
def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def dashboard_admin(request):
    return render(request, 'admin/base_admin.html')

@login_required
def patient_profiles(request):
    query = request.GET.get('search')
    if query:
        patients = PatientProfile.objects.filter(
            Q(full_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query) |
            Q(county__icontains=query)
        )
    else:
        patients = PatientProfile.objects.all()

    return render(request, 'admin/patient_profiles.html', {'patients': patients, 'search_query': query})

@login_required
def doctor_profiles_list(request):
    query = request.GET.get('q')
    doctors = DoctorProfile.objects.all()

    if query:
        doctors = doctors.filter(
            Q(full_name__icontains=query) |
            Q(professional_title__icontains=query)
        )

    context = {
        'doctors': doctors,
        'query': query,
    }
    return render(request, 'admin/doctor_cards.html', context)

@login_required
def booking_list(request):
    query = request.GET.get('q')
    bookings = Booking.objects.select_related('patient', 'doctor')

    if query:
        bookings = bookings.filter(
            Q(patient__full_name__icontains=query) |
            Q(doctor__full_name__icontains=query)
        )

    context = {
        'bookings': bookings,
        'query': query
    }
    return render(request, 'admin/booking_cards.html', context)

@login_required
def mpesa_transactions(request):
    status_filter = request.GET.get('status')
    search_query = request.GET.get('search', '')

    transactions = Payment.objects.select_related('user', 'doctor').order_by('-id')

    if status_filter:
        transactions = transactions.filter(status=status_filter)

    if search_query:
        transactions = transactions.filter(
            Q(user__full_name__icontains=search_query) |
            Q(doctor__full_name__icontains=search_query)
        )

    return render(request, 'admin/mpesa_cards.html', {
        'transactions': transactions,
        'selected_status': status_filter,
        'search_query': search_query
    })
    

from django.contrib.auth import get_user_model
User = get_user_model()

@login_required
def user_list(request):
    filter_type = request.GET.get('type')  # Get the filter from the URL
    users = User.objects.all()

    if filter_type:
        users = users.filter(profile__user_type=filter_type)

    return render(request, 'admin/admin_user_list.html', {
        'users': users,
        'filter_type': filter_type
    })



@user_passes_test(lambda u: u.is_superuser)
@login_required
def toggle_user_status(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active  # toggle status
    user.save()
    
    status = "activated" if user.is_active else "deactivated"
    messages.success(request, f"User '{user.username}' has been {status}.")
    
    return redirect('user_list')


def edit_patient(request, pk):
    patient = get_object_or_404(PatientProfile, pk=pk)
    if request.method == 'POST':
        form = PatientProfileForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            form.save()
            return redirect('patient_profiles')
    else:
        form = PatientProfileForm(instance=patient)
    return render(request, 'admin/edit_patient.html', {'form': form})

def delete_patient(request, pk):
    patient = get_object_or_404(PatientProfile, pk=pk)
    patient.delete()
    return redirect('patient_profiles')


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    today = timezone.now().date()
    start_date = today - timedelta(days=29)

    # Bookings per day
    bookings_qs = Booking.objects.filter(created_at__date__gte=start_date)
    bookings_by_day = (
        bookings_qs
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    day_count_map = {item['day'].date(): item['count'] for item in bookings_by_day}
    bookings_labels = []
    bookings_counts = []
    for i in range(30):
        d = start_date + timedelta(days=i)
        bookings_labels.append(d.strftime('%b %d'))
        bookings_counts.append(day_count_map.get(d, 0))

    # 📊 Booking Status Breakdown (replacing appointment_type)
    status_qs = Booking.objects.values('status').annotate(count=Count('id'))
    status_label_map = dict(Booking.AppointmentStatus.choices)
    status_labels = []
    status_counts = []
    for item in status_qs:
        code = item['status']
        status_labels.append(status_label_map.get(code, code))
        status_counts.append(item['count'])

    # Top doctors by bookings
    top_docs_qs = (
        Booking.objects
        .values('doctor__id', 'doctor__full_name')
        .annotate(bookings_count=Count('id'))
        .order_by('-bookings_count')[:5]
    )
    top_docs_labels = [item['doctor__full_name'] for item in top_docs_qs]
    top_docs_counts = [item['bookings_count'] for item in top_docs_qs]

    # Payments summary
    payments_summary = Payment.objects.values('status').annotate(total=Sum('amount'))
    payments_labels = [p['status'] for p in payments_summary]
    payments_values = [float(p['total'] or 0) for p in payments_summary]

    # Stat cards
    total_bookings = Booking.objects.count()
    total_patients = PatientProfile.objects.count()
    total_doctors = DoctorProfile.objects.count()
    total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'bookings_labels': bookings_labels,
        'bookings_counts': bookings_counts,
        'status_labels': status_labels,   # ✅ updated
        'status_counts': status_counts,   # ✅ updated
        'top_docs_labels': top_docs_labels,
        'top_docs_counts': top_docs_counts,
        'payments_labels': payments_labels,
        'payments_values': payments_values,
        'total_bookings': total_bookings,
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_revenue': float(total_revenue),
    }
    return render(request, 'admin/admin_dashboard.html', context)


# --- Doctors ---
def edit_doctor(request, pk):
    doctor = get_object_or_404(DoctorProfile, pk=pk)
    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            return redirect('doctor_profiles')
    else:
        form = DoctorProfileForm(instance=doctor)
    return render(request, 'admin/edit_doctor.html', {'form': form})

def delete_doctor(request, pk):
    doctor = get_object_or_404(DoctorProfile, pk=pk)
    doctor.delete()
    return redirect('doctor_profiles')

'''
def edit_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST':
        form = BookingForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            return redirect('booking_list')  # adjust to your admin view name
    else:
        form = BookingForm(instance=booking)

    return render(request, 'admin/edit_booking.html', {'form': form, 'booking': booking})

def delete_booking(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id)
    booking.delete()
    return redirect('booking_list')  # Change to your booking list view name
'''

#Doctor Availability
@login_required
def manage_availability(request):
    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        messages.error(request, "Only doctors can manage availability.")
        return redirect('addprofile')

    if request.method == 'POST':
        form = DoctorWorkingHoursForm(request.POST, instance=doctor)
        if form.is_valid():
            # Handle available_days manually
            available_days_list = request.POST.getlist('available_days')
            if available_days_list:
                doctor.available_days = ','.join(available_days_list)
            
            form.save()
            messages.success(request, "Working hours and availability updated successfully.")
            return redirect('manage_availability')
    else:
        form = DoctorWorkingHoursForm(instance=doctor)

    # Show all of the doctor's availability slots
    slots = DoctorAvailability.objects.filter(doctor=doctor).order_by('date', 'start_time')
    current_days = doctor.get_available_days_list()
    
    return render(request, 'manage_availability.html', {
        'form': form, 
        'slots': slots, 
        'doctor': doctor,
        'current_days': current_days
    })
@login_required
def delete_availability(request, availability_id):
    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return redirect('addprofile')
    slot = get_object_or_404(DoctorAvailability, id=availability_id, doctor=doctor)
    slot.delete()
    messages.success(request, "Availability removed.")
    return redirect('manage_availability')



#Equipment Leasing
def equipment_list(request):
    q = (request.GET.get('q') or '').strip()
    qs = Equipment.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
        qs = qs.order_by('name')

    paginator = Paginator(qs, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'q': q,
    }
    
    # Use admin template for staff users, regular template for others
    if request.user.is_staff:
        return render(request, 'admin/equipment_list_admin.html', context)
    return render(request, 'equipment_list.html', context)


from django.db.models import Q

@login_required
def equipment_detail(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    patient_profiles = PatientProfile.objects.filter(user=request.user)

    # Check if there's already an approved/pending request for this equipment
    approved_exists = equipment.requests.filter(
        status__in=[EquipmentRequest.RequestStatus.APPROVED, EquipmentRequest.RequestStatus.AWAITING_DEPOSIT, 
                    EquipmentRequest.RequestStatus.DEPOSIT_PAID, EquipmentRequest.RequestStatus.DELIVERED]
    ).exists()

    if request.method == "POST":
        if approved_exists:
            messages.error(request, "This equipment is already approved for someone else.")
            return redirect("equipment_detail", pk=equipment.pk)

        profile_id = request.POST.get("patient_profile")
        profile = get_object_or_404(PatientProfile, id=profile_id, user=request.user)
        
        # Get new fields
        rental_days = int(request.POST.get("rental_days", 1))
        delivery_address = request.POST.get("delivery_address", "")
        
        # Calculate deposit (30% of total)
        total_cost = equipment.daily_rate * rental_days
        deposit_amount = round(float(total_cost) * 0.30, 2)

        equipment_request = EquipmentRequest.objects.create(
            equipment=equipment,
            patient=profile,
            status=EquipmentRequest.RequestStatus.PENDING,
            rental_days=rental_days,
            delivery_address=delivery_address,
            deposit_amount=deposit_amount
        )
        
        # Notify admin about the new equipment request
        notify_admin_new_equipment_request(equipment_request)
        
        messages.success(request, "Your equipment request has been submitted successfully! You will be notified by email once it's approved.")
        return redirect("equipment_detail", pk=equipment.pk)

    return render(
        request,
        "equipment_detail.html",
        {
            "equipment": equipment,
            "patient_profiles": patient_profiles,
            "approved_exists": approved_exists,
        }
    )




#Equipment form
@login_required
def equipment_create(request):
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('equipment_list')
    else:
        form = EquipmentForm()
    
    return render(request, 'add_equipment.html', {'form': form})



@user_passes_test(is_admin)
def equipment_requests_list(request):
    if request.method == "POST":
        req_id = request.POST.get("req_id")
        new_status = request.POST.get("status")

        request_obj = get_object_or_404(EquipmentRequest, id=req_id)
        request_obj.status = new_status
        request_obj.save()

        # If status is PAID, trigger payment workflow
        if new_status == EquipmentRequest.RequestStatus.PAID:
            success = initiate_payment_for_equipment(request_obj)
            if success:
                messages.success(request, f"Payment initiated for {request_obj.equipment.name}")
            else:
                messages.error(request, f"Failed to initiate payment for {request_obj.equipment.name}")

            return redirect("equipment_requests_list")
        

        if new_status == EquipmentRequest.RequestStatus.APPROVED:
            request_obj.equipment.available = False
            request_obj.equipment.save()
            equipment_approval_email(request_obj)

            messages.success(request, f"{request_obj.equipment.name} approved, marked unavailable, and email sent to {request_obj.patient.full_name}.")

            return redirect("equipment_requests_list")
        
        # For all other status changes, show success message
        messages.success(request, f"Status updated to {request_obj.get_status_display()}")
        return redirect("equipment_requests_list")

    requests_list = EquipmentRequest.objects.select_related('patient', 'equipment').order_by('-created_at')
    return render(request, 'admin/equipment_requests_list.html', {
        'requests_list': requests_list
    })


@login_required
@user_passes_test(is_admin)
def send_equipment_payment(request, req_id):
    """
    Admin initiates STK push for payment after equipment has been delivered.
    """
    equipment_request = get_object_or_404(EquipmentRequest, id=req_id)
    
    if equipment_request.status != EquipmentRequest.RequestStatus.DELIVERED:
        messages.error(request, "Payment can only be requested for delivered equipment.")
        return redirect("equipment_requests_list")
    
    success = initiate_payment_for_equipment(equipment_request)
    
    if success:
        messages.success(request, f"Payment request of KES {equipment_request.total_cost} sent to {equipment_request.patient.full_name}'s phone ({equipment_request.patient.phone})")
    else:
        messages.error(request, f"Failed to send payment request. Please check the patient's phone number and try again.")
    
    return redirect("equipment_requests_list")


def notify_admin_new_equipment_request(equipment_request):
    """Send email notification to admin when a new equipment request is submitted."""
    try:
        admin_email = settings.DEFAULT_FROM_EMAIL or 'admin@lifecareconnect.com'
        subject = f"New Equipment Request: {equipment_request.equipment.name}"
        message = (
            f"A new equipment request has been submitted.\n\n"
            f"Equipment: {equipment_request.equipment.name}\n"
            f"Patient: {equipment_request.patient.full_name}\n"
            f"Phone: {equipment_request.patient.phone}\n"
            f"Email: {equipment_request.patient.email}\n"
            f"Rental Days: {equipment_request.rental_days}\n"
            f"Total Cost: KES {equipment_request.total_cost}\n"
            f"Deposit: KES {equipment_request.deposit_amount}\n"
            f"Delivery Address: {equipment_request.delivery_address}\n\n"
            "Please log in to the admin dashboard to approve or decline this request."
        )
        send_mail(
            subject,
            message,
            'noreply@lifecareconnect.com',
            [admin_email],
            fail_silently=True
        )
    except Exception as e:
        print(f"Failed to send admin notification email: {e}")


@user_passes_test(is_admin)
def approve_equipment_request(request):
    """
    Admin marks an equipment request as approved
    and automatically sets the equipment to unavailable.
    Sends an approval email.
    """
    if request.method == "POST":
        req_id = request.POST.get("req_id")
        new_status = request.POST.get("status")

        request_obj = get_object_or_404(EquipmentRequest, id=req_id)
        request_obj.status = new_status
        request_obj.save()

        if new_status == EquipmentRequest.RequestStatus.APPROVED:
            request_obj.equipment.available = False
            request_obj.equipment.save()
            equipment_approval_email(request_obj)

        messages.success(request, f"{request_obj.equipment.name} approved, marked unavailable, and email sent to {request_obj.patient.full_name}.")

        return redirect("equipment_requests_list")


# Equipment approval email
def equipment_approval_email(request_object):
    recipient_email = request_object.patient.email
    
    subject = "Your Equipment Request was Approved"
    message = (
        f"Hi {request_object.patient.full_name},\n\n"
        f"Your request for {request_object.equipment.name} has been approved. "
        "Please log in to proceed with payment or pickup arrangements.\n\n"
        "Thank you!"
    )
    
    try:
        send_mail(
            subject,
            message,
            'noreply@lifecareconnect.com',  # must be a verified sender in your email backend
            [recipient_email],
            fail_silently=False
        )
    except Exception as e:
        print(f"Failed to send email: {e}")



# views.py - Update your view_doctor_profile function

@login_required
def view_doctor_profile(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    
    # Get doctor's available time slots
    doctor_time_slots = doctor.get_formatted_time_slots()
    
    # Get doctor's available days
    available_days = doctor.get_available_days_list()
    
    # Convert to JSON for JavaScript
    import json
    doctor_time_slots_json = json.dumps(doctor_time_slots)
    available_days_json = json.dumps(available_days)
    
    context = {
        'doctor': doctor,
        'doctor_time_slots': doctor_time_slots_json,
        'available_days': available_days,
        'available_days_json': available_days_json,
        'is_accepting': doctor.is_accepting_appointments,
        'commission': 50,  # Your commission
        'total_fee': int(doctor.charge_rates) + 50,  # Ensure integer for calculations
    }
    
    return render(request, 'doctor_profile.html', context)

# Add this new view to get available slots for a specific date
@login_required
def get_doctor_available_slots(request, doctor_id):
    """
    AJAX endpoint to get available slots for a specific date
    """
    if request.method == 'GET':
        date_str = request.GET.get('date')
        if not date_str:
            return JsonResponse({'error': 'Date parameter required'}, status=400)
        
        try:
            from datetime import datetime
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            doctor = get_object_or_404(DoctorProfile, id=doctor_id)
            
            available_slots = doctor.get_available_slots_for_date(date)
            
            return JsonResponse({
                'status': 'success',
                'available_slots': available_slots
            })
            
        except ValueError:
            return JsonResponse({'error': 'Invalid date format'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# Update your book_doctor_ajax function to handle date/time
@login_required  
def book_doctor_ajax(request, doctor_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)
    
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    
    profile_id = request.session.get("active_profile_id")
    if not profile_id:
        return JsonResponse({"status": "error", "message": "No active profile selected"}, status=400)

    try:
        patient = PatientProfile.objects.get(id=profile_id, user=request.user)
    except PatientProfile.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Invalid profile"}, status=400)


    # Get data from request
    try:
        import json
        data = json.loads(request.body)
        appointment_date = data.get('appointment_date')
        appointment_time = data.get('appointment_time')
        
        if not appointment_date or not appointment_time:
            return JsonResponse({'status': 'error', 'message': 'Date and time are required'}, status=400)
            
        # Convert date string to date object
        from datetime import datetime, date
        date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        
        # Validate: Cannot book on past dates
        if date_obj < date.today():
            return JsonResponse({'status': 'error', 'message': 'Cannot book an appointment on a past date'}, status=400)
        
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({'status': 'error', 'message': 'Invalid data format'}, status=400)

    # Check if slot is still available
    existing_booking = Booking.objects.filter(
        doctor=doctor,
        date=date_obj,
        time=appointment_time,
        status__in=['pending', 'accepted']
    ).first()
    
    if existing_booking:
        return JsonResponse({'status': 'error', 'message': 'This time slot is no longer available'})

    # Check if patient already has a pending/accepted booking with this doctor
    patient_booking = Booking.objects.filter(
        patient=patient,
        doctor=doctor,
        status__in=['pending', 'accepted']
    ).first()
    
    if patient_booking:
        return JsonResponse({'status': 'error', 'message': 'You already have a pending appointment with this doctor'})    
    # Create new booking
    booking = Booking.objects.create(
        patient=patient,
        doctor=doctor,
        date=date_obj,
        time=appointment_time,
        status='pending',
        cost=doctor.charge_rates + 50  # Include commission
    )
    
    try:
        # Send notifications
        notify_doctor(booking)
        notify_patient(booking)
        return JsonResponse({'status': 'success', 'message': 'Appointment request sent successfully'})
    except Exception as e:
        print(f"Email notification error: {str(e)}")
        # Don't delete booking if email fails, just return success
        return JsonResponse({'status': 'success', 'message': 'Appointment request sent successfully'})

# Add notification function for booking creation
def notify_patient(booking):
    patient_email = booking.patient.user.email
    status = booking.status
    doctor_name = f"Dr. {booking.doctor.full_name}"
    
    subject = 'Lifecare Connect - Appointment Update'
    
    if status == Booking.AppointmentStatus.ACCEPTED:
        message = (
            f'Dear {booking.patient.full_name},\n\n'
            f'Great news! Your appointment with {doctor_name} has been accepted.\n\n'
            f'Appointment Details:\n'
            f'- Date: {booking.date}\n'
            f'- Time: {booking.time}\n'
            f'- Cost: KES {booking.cost}\n\n'
            'Please ensure you are available at the scheduled time.\n\n'
            'Best regards,\nLifecare Connect'
        )
    elif status == Booking.AppointmentStatus.DECLINED:
        decline_reason = booking.decline_reason or "No reason provided."
        message = (
            f'Dear {booking.patient.full_name},\n\n'
            f'Unfortunately, your appointment request with {doctor_name} was declined.\n\n'
            f'Reason: {decline_reason}\n\n'
            'You may try booking with another healthcare provider or at a different time.\n\n'
            'Best regards,\nLifecare Connect'
        )
    elif status == Booking.AppointmentStatus.COMPLETED:
        message = (
            f'Dear {booking.patient.full_name},\n\n'
            f'Your appointment with {doctor_name} has been marked as completed.\n\n'
            'A payment request will be sent to you shortly.\n\n'
            'Thank you for using Lifecare Connect!'
        )
    elif status == Booking.AppointmentStatus.PENDING:
        message = (
            f'Dear {booking.patient.full_name},\n\n'
            f'Your appointment request with {doctor_name} has been received.\n\n'
            f'Appointment Details:\n'
            f'- Date: {booking.date}\n'
            f'- Time: {booking.time}\n\n'
            'The doctor will review and respond to your request soon.\n\n'
            'Best regards,\nLifecare Connect'
        )
    else:  # fallback
        message = f'Your appointment request to {doctor_name} is being processed.'
    
    send_mail(
        subject,
        message,
        'noreply@lifecareconnect.com',
        [patient_email],
        fail_silently=False
    )


def notify_doctor(booking):
    """Send email to doctor when patient makes a booking request"""
    doctor_email = booking.doctor.email
    patient_name = booking.patient.full_name
    status = booking.status
    
    subject = 'Lifecare Connect - New Appointment Request'
    
    if status == Booking.AppointmentStatus.PENDING:
        message = (
            f'Dear Dr. {booking.doctor.full_name},\n\n'
            f'You have received a new appointment request from {patient_name}.\n\n'
            f'Appointment Details:\n'
            f'- Patient: {patient_name}\n'
            f'- Date: {booking.date}\n'
            f'- Time: {booking.time}\n'
            f'- Phone: {booking.patient.phone}\n\n'
            'Please log in to your dashboard to accept or decline this request.\n\n'
            'Best regards,\nLifecare Connect'
        )
    elif status == Booking.AppointmentStatus.CANCELLED:
        subject = 'Lifecare Connect - Appointment Cancelled'
        message = (
            f'Dear Dr. {booking.doctor.full_name},\n\n'
            f'The appointment with {patient_name} scheduled for {booking.date} at {booking.time} '
            'has been cancelled by the patient.\n\n'
            'Best regards,\nLifecare Connect'
        )
    else:
        # Default/fallback message
        message = f'Appointment update for booking with {patient_name}.'
    
    send_mail(
        subject,
        message,
        'noreply@lifecareconnect.com',
        [doctor_email],
        fail_silently=False
    )


def initiate_payment_for_booking(booking, phone_number=None):
    
    try:
        # 1. Extract necessary information directly from the booking
        patient_profile = booking.patient
        doctor = booking.doctor
        amount = int(booking.cost)  # Ensure amount is an integer
        
        # Use provided phone number or fall back to patient's registered phone
        if not phone_number:
            phone_number = patient_profile.phone
        
        # Validate phone number format
        if not phone_number or len(phone_number) < 10:
            return False, "Invalid phone number format"
        
        print(f"Initiating STK Push: phone={phone_number}, amount={amount}")
        
        # 2. Prepare STK Push details
        cl = MpesaClient()
        account_reference = 'LifecarePayment'
        transaction_desc = f'Payment for appointment with Dr. {doctor.full_name}'
        callback_url = os.getenv('MPESA_CALLBACK_URL', 'https://your-domain.com/payments/callback/')

        print(f"Callback URL: {callback_url}")

        # 3. Call the Mpesa API
        response = cl.stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=account_reference,
            transaction_desc=transaction_desc,
            callback_url=callback_url
        )

        print(f"STK Push Response: {response.status_code} - {response.text}")

        # 4. Handle the API response
        if response.ok:
            # Check if the response contains success indicator
            response_data = response.json() if hasattr(response, 'json') else {}
            response_code = response_data.get('ResponseCode', '')
            
            if response_code == '0' or response.status_code == 200:
                # Create a payment record to track the transaction
                Payment.objects.create(
                    user=patient_profile,
                    doctor=doctor,
                    booking=booking,
                    amount=amount,
                    status="PENDING"
                )
                return True, "Payment request sent successfully"
            else:
                error_desc = response_data.get('ResponseDescription', 'Unknown error')
                print(f"STK Push failed: {error_desc}")
                return False, error_desc
        else:
            # Log the error if the API call itself fails
            error_text = response.text if hasattr(response, 'text') else str(response)
            print(f"STK Push API Error for booking {booking.id}: {error_text}")
            return False, f"API Error: {error_text[:100]}"

    except Exception as e:
        # Log any other exceptions during the process
        print(f"An exception occurred in initiate_payment_for_booking for booking {booking.id}: {e}")
        import traceback
        traceback.print_exc()
        return False, str(e)
    

def initiate_payment_for_equipment(equipment_request):
    try:
        # 1. Extract necessary information directly from the equipment request
        patient_profile = equipment_request.patient
        equipment = equipment_request.equipment
        # Use total cost (daily_rate * rental_days) instead of just daily_rate
        amount = int(equipment_request.total_cost)
        phone_number = patient_profile.phone

        # 2. Prepare STK Push details
        cl = MpesaClient()
        account_reference = 'LifecareEquipment'
        transaction_desc = f'Payment for {equipment.name} - {equipment_request.rental_days} days'
        callback_url = os.getenv('MPESA_CALLBACK_URL', 'https://your-domain.com/mpesa/callback/')

        # 3. Call the Mpesa API
        response = cl.stk_push(
            phone_number=phone_number,
            amount=amount,
            account_reference=account_reference,
            transaction_desc=transaction_desc,
            callback_url=callback_url
        )

        print(f"Equipment STK Push Response: {response.status_code} - {response.text}")

        # 4. Handle the API response
        if response.ok:
            # Create a payment record to track the transaction
            # Note: doctor field is required, so we need to handle this
            # For equipment payments, we'll set doctor to None or first available
            Payment.objects.create(
                user=patient_profile,
                doctor=DoctorProfile.objects.first(),  # Placeholder - equipment payments don't have a doctor
                equipment_request=equipment_request,
                amount=amount,
                status="PENDING"
            )
            
            # Don't update status to PAID here - wait for callback confirmation
            # equipment_request.status = EquipmentRequest.RequestStatus.PAID
            # equipment_request.save()

            return True
        else:
            print(f"STK Push API Error for equipment request {equipment_request.id}: {response.text}")
            return False

    except Exception as e:
        print(f"An exception occurred in initiate_payment_for_equipment for request {equipment_request.id}: {e}")
        return False

