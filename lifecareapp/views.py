from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'index.html')

def inner(request):
    return render(request, 'inner-page.html')

def login(request):
    return render(request, 'login.html')

def signup(request):
    return render(request, 'signup.html')

def addprofile(request):
    return render(request, 'addprofile.html')

def patientform(request):
    return render(request, 'patientform.html')

def doctorform(request):
    return render(request, 'doctorform.html')