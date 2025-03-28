from django.shortcuts import render
from django.contrib.auth import logout
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from accounts import forms

def role_based_redirect(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('/admin/')
        else:
            return redirect('/tickets/')

def fanan(request):
    login_user = request.user.is_authenticated
    return render(request, "new/landing.html",{'login_user':login_user})


def home(request):
    if request.user.is_staff:
        return render(request, "home.html")
    return render(request, "u/home.html")


def register(request):
    if request.method == 'POST':
        form = forms.RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
           
    else:
        form = forms.RegistrationForm()
    return render(request, 'register.html', {'form': form})

def logout_view(request):
    logout(request)  # Logs the user out
    return redirect('/')  # Redirect to the login page or any other desired page
