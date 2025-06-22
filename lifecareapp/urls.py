"""
URL configuration for LifecareConnect project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib.auth import views as auth_views
from django.urls import include, path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('inner/', views.inner, name='inner'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('departments/', views.departments, name='departments'),
    path('doctors/', views.doctors, name='doctors'),
    path('contact/', views.contact, name='contact'),
    path('', include('django.contrib.auth.urls')),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('signup/', views.signup, name='signup'),
    path('edit/', views.edit, name='edit'),
    path('addprofile/', views.add_profile, name='add_profile'),
    path('patientform/', views.patient_form, name='patientform'),
    path('doctorform/', views.doctor_form, name='doctorform'),
    path('edit-patient-profile/', views.edit_patient_profile, name='edit_patient_profile'),
    path('edit-doctor-profile/', views.edit_doctor_profile, name='edit_doctor_profile'),
    path('book-doctor/<int:doctor_id>/', views.book_doctor_ajax, name='book_doctor_ajax'),
    path('booking/<int:booking_id>/<str:decision>/', views.update_booking_status, name='update_booking_status'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('appointments/', views.appointments, name='appointments'),
    path('doctor_profile/<int:doctor_id>', views.view_doctor_profile, name='doctor-profile'),
    path('mpesa/stk/', views.initiate_stk_push, name='stk_push'),
    path('stk-push', views.stk_push, name='process_stk_push'),
    #path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),

]
