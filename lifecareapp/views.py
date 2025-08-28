from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required,user_passes_test
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from .models import PatientProfile, DoctorProfile, Profile, Booking, Payment, DoctorAvailability, Equipment
from .forms import UserRegistrationForm, PatientProfileForm, DoctorProfileForm, UserEditForm, ProfileEditForm, EquipmentForm, DoctorAvailabilityForm
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

            if user.is_superuser or user.is_staff:
                return redirect('admin_dashboard_home')  # Make sure this URL name exists!

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
            return redirect('custom_login_view')  # Redirect after failed login

    # ⚠️ Handle GET separately so we don't accidentally re-render on POST
    return render(request, 'registration/login.html')

from django.contrib.auth.views import LoginView

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

custom_login_view = CustomLoginView.as_view()


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
        return redirect('dashboard_doctor')

    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            return redirect('dashboard_doctor')
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
        return redirect('addprofile')  # fallback in case no doctor profile yet

        
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
            return redirect('dashboard_patient')
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
            return redirect('dashboard_doctor')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DoctorProfileForm(instance=profile)

    return render(request, 'edit_doctor_profile.html', {'form': form})

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
    patient_name = booking.patient.user.get_full_name()
    subject = f"New Appointment Request From {patient_name}"
    
    accept_url = f"https://lifecareconnect.com/booking/{booking.id}/accepted/"
    decline_url = f"https://lifecareconnect.com/booking/{booking.id}/declined/"
    
    message = (
        f"You have a new appointment request from {patient_name}.\n\n"
        f"Please log in to your dashboard to view the request and accept or decline it.\n\n"
        f"Booking ID: {booking.id}\n"
        f"Patient Profile: https://lifecareconnect.com/patient/{booking.patient.id}/profile/\n\n"
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

#def view_doctor_profile(request, doctor_id):
#    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
#   charge_rate = float(doctor.charge_rates)
#    commission = float(doctor.charge_rates) * 0.2
#    total_fee = charge_rate + commission
#    return render(request, 'doctor_profile.html', {
#        'doctor': doctor, 
#        'commission': commission, 
#        'charge_rate': charge_rate,
#        'total_fee': total_fee,})

        
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

        success = initiate_stk_push(request)

        if success:
            try:
                doctor = DoctorProfile.objects.get(id=doctor_id)

                # Get one of the user's patient profiles
                patient_profiles = PatientProfile.objects.filter(user=request.user)
                if not patient_profiles.exists():
                    return JsonResponse({"status": "error", "message": "Patient profile not found."})
                
                patient_profile = patient_profiles.first()  # 👈 Use logic as needed

                payment = Payment.objects.create(
                    user=patient_profile,
                    doctor=doctor,
                    amount=amount,
                    status="PAID"
                )

                booking = Booking.objects.create(
                    patient=patient_profile,
                    doctor=doctor,
                    date=date,
                    time=time,
                    status="pending"
                )

                handler = PaymentEventHandler(payment, booking)
                handler.handle_success()

                return JsonResponse({"status": "success"})

            except DoctorProfile.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Doctor not found."})
            except Exception as e:
                return JsonResponse({"status": "error", "message": f"Something went wrong: {str(e)}"})

        return JsonResponse({"status": "fail", "message": "STK Push failed"})



#ADMIN STUUUUFFF!!!!!!!!!🤖🤖🤖

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
    # --- Time window for trends (last 30 days) ---
    today = timezone.now().date()
    start_date = today - timedelta(days=29)  # inclusive 30 days

    # Bookings per day for last 30 days
    bookings_qs = Booking.objects.filter(created_at__date__gte=start_date)
    bookings_by_day = (
        bookings_qs
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    # Map dates to counts for continuous series
    day_count_map = {item['day'].date(): item['count'] for item in bookings_by_day}
    bookings_labels = []
    bookings_counts = []
    for i in range(30):
        d = start_date + timedelta(days=i)
        bookings_labels.append(d.strftime('%b %d'))     # e.g. "Aug 11"
        bookings_counts.append(day_count_map.get(d, 0))

    # Appointment-type distribution (pie)
    type_qs = Booking.objects.values('appointment_type').annotate(count=Count('id'))
    # convert to label/value arrays (use readable labels from choices)
    type_label_map = dict(Booking.APPOINTMENT_TYPE_CHOICES)
    types_labels = []
    types_counts = []
    for item in type_qs:
        code = item['appointment_type']
        types_labels.append(type_label_map.get(code, code))
        types_counts.append(item['count'])

    # Top doctors by bookings (top 5)
    top_docs_qs = (
        Booking.objects
        .values('doctor__id', 'doctor__full_name')
        .annotate(bookings_count=Count('id'))
        .order_by('-bookings_count')[:5]
    )
    top_docs_labels = [item['doctor__full_name'] for item in top_docs_qs]
    top_docs_counts = [item['bookings_count'] for item in top_docs_qs]

    # Payments summary by status (sum amount per status)
    payments_summary = Payment.objects.values('status').annotate(total=Sum('amount'))
    payments_labels = [p['status'] for p in payments_summary]
    payments_values = [float(p['total'] or 0) for p in payments_summary]

    # Quick stat cards
    total_bookings = Booking.objects.count()
    total_patients = PatientProfile.objects.count()
    total_doctors = DoctorProfile.objects.count()
    total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'bookings_labels': bookings_labels,
        'bookings_counts': bookings_counts,
        'types_labels': types_labels,
        'types_counts': types_counts,
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
        # Use the new form
        form = DoctorAvailabilityForm(request.POST)
        if form.is_valid():
            # The form now correctly creates a DoctorAvailability instance
            slot = form.save(commit=False)
            slot.doctor = doctor

            # Check for overlaps using the attributes from the 'slot' instance
            overlap = DoctorAvailability.objects.filter(
                doctor=doctor,
                date=slot.date,
                start_time__lt=slot.end_time, # (start < new_end)
                end_time__gt=slot.start_time   # (end > new_start)
            ).exists()

            if overlap:
                messages.error(request, "This time slot overlaps with an existing one.")
            else:
                slot.save()
                messages.success(request, "New availability slot has been added.")
                return redirect('manage_availability')
        # If form is not valid, it will fall through and re-render with errors
    else:
        # Use the new form for GET requests too
        form = DoctorAvailabilityForm()

    # Show all of the doctor's availability slots
    slots = DoctorAvailability.objects.filter(doctor=doctor).order_by('date', 'start_time')
    
    return render(request, 'manage_availability.html', {'form': form, 'slots': slots})
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
    return render(request, 'equipment_list.html')

def equipment_detail(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    return render(request, 'equipment_detail.html', {'equipment': equipment})

#Equipmentform

@login_required
def equipment_create(request):
    if request.method == 'POST':
        form = EquipmentForm(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        return redirect('equipment_list')
    else:
        form = EquipmentForm()
    return render(request, 'equipment_form.html', {'form': form})







# views.py - Update your view_doctor_profile function

@login_required
def view_doctor_profile(request, doctor_id):
    doctor = get_object_or_404(DoctorProfile, id=doctor_id)
    
    # Get doctor's available time slots
    doctor_time_slots = doctor.get_formatted_time_slots()
    
    # Convert to JSON for JavaScript
    import json
    doctor_time_slots_json = json.dumps(doctor_time_slots)
    
    context = {
        'doctor': doctor,
        'doctor_time_slots': doctor_time_slots_json,
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
    
    try:
        patient = PatientProfile.objects.get(user=request.user)
    except PatientProfile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Patient profile not found'}, status=400)

    # Get data from request
    try:
        import json
        data = json.loads(request.body)
        appointment_date = data.get('appointment_date')
        appointment_time = data.get('appointment_time')
        
        if not appointment_date or not appointment_time:
            return JsonResponse({'status': 'error', 'message': 'Date and time are required'}, status=400)
            
        # Convert date string to date object
        from datetime import datetime
        date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        
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