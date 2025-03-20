from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import SignupForm, LoginForm

# Create your views here.
def index(request):
    return render(request, 'index.html')

def inner(request):
    return render(request, 'inner-page.html')

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('addprofile')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form' : form})

def user_signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form' : form})

def user_logout(request):
    logout(request)
    return redirect('login')

def add_profile(request):
    return render(request, 'addprofile.html')

def patient_form(request):
    return render(request, 'patientform.html')

def doctor_form(request):
    return render(request, 'doctorform.html')