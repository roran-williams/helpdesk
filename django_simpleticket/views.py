from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User, Group
from django.contrib.auth import logout
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
# from pyparsing import Group
from accounts import forms

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from simpleticket.models import Profile, Ticket
from simpleticket.forms import ProfileUpdateForm
from django.db.models import Count, Avg


def fanan_website(request):
    return render(request, 'fanan.html')  

@login_required
def profile(request, username=None):
    created_tickets = list(
        Ticket.objects.filter(created_by__username=username)
        .values('created_by__username')
        .annotate(created=Count('id'))
        .order_by('-created')
    )
    

    assigned_tickets = list(
        Ticket.objects.filter(assigned_to__username=username)
        .values('assigned_to__username')
        .annotate(assigned=Count('id'))
        .order_by('-assigned')
    )

    resolved_tickets = list(
        Ticket.objects.filter(assigned_to__username=username , status__name='Closed')
        .values('status__name')
        .annotate(closed=Count('id'))
        .order_by('-closed')
    )
    
    

    # Allow viewing other users' profiles
    if username:
        user_profile = get_object_or_404(Profile, user__username=username)
    else:
        user_profile = Profile.objects.get_or_create(user=request.user)[0]

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            return redirect('/profile/', username=user_profile.user.username)
    else:
        form = ProfileUpdateForm(instance=user_profile)

    return render(request, 'profile.html', {
        'form': form, 
        'profile': user_profile,
        'created_tickets':created_tickets[0]['created'] if created_tickets else 0, 
        'assigned_tickets':assigned_tickets[0]['assigned'] if assigned_tickets else 0,
        'resolved_tickets':resolved_tickets[0]['closed'] if resolved_tickets else 0,
        })


def custom_login(request):
    if request.method == "POST":
        
        username = request.POST.get("username")
        password = request.POST.get("password")
        
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("/")  # Redirect to dashboard after login
        else:
            messages.error(request, "Invalid Username or password. Please try again.")

    return render(request, "login.html")


def role_based_redirect(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('/admin/')
        else:
            return redirect('/tickets/')

def fanan(request):
    login_user = request.user.is_authenticated
    return render(request, "new/landing.html",{'login_user':login_user})

def knowledge_base(request):
    return render(request, "new/knowledge_base.html")

def home(request):
    if request.user.is_staff:
        return render(request, "home.html")
    return render(request, "u/home.html")


def register(request):
    if request.method == 'POST':
        form = forms.RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            Staff, created = Group.objects.get_or_create(name="Staff")

            if user.email.endswith("@fanan.com"):  # Example condition
                user.groups.add(Staff)
            # Check if the user belongs to the 'Staff' group
            if user.groups.filter(name="Staff").exists():
                organization = "Fanan ltd"
                address = 'mombasa rd'
            else:
                organization = None
                address = 'mombasa rd'

            
            Profile.objects.create(user=user,organization=organization,address=address)

        # Create a Profile and assign the role
        # Profile.objects.create(user=user)
        return redirect('login')
           
    else:
        form = forms.RegistrationForm()
    return render(request, 'register.html', {'form': form})

def logout_view(request):
    logout(request)  # Logs the user out
    return redirect('/')  # Redirect to the login page or any other desired page
