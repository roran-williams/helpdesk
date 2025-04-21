from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'autocomplete': 'off','class': 'form-control', 'placeholder': 'Enter your email'}),
    )
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'autocomplete': 'off','class': 'form-control', 'placeholder': 'Enter your firstname'}),
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'autocomplete': 'off','class': 'form-control', 'placeholder': 'Enter your lastname'}),
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'autocomplete': 'off','class': 'form-control', 'placeholder': 'Enter your username'}),
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password','class': 'form-control', 'placeholder': 'Enter your password'}),
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password','class': 'form-control', 'placeholder': 'Confirm your password'}),
    )

    class Meta:
        model = User
        fields = ['first_name','last_name','username', 'email', 'password1', 'password2']
