from django.shortcuts import render
from django.contrib.auth import logout
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages


def role_based_redirect(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('/admin/')
        else:
            return redirect('/tickets/')


def home(request):
    return render(request, "home.html")

from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def logout_view(request):
    logout(request)  # Logs the user out
    return redirect('login')  # Redirect to the login page or any other desired page
