"""django_simpleticket URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
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
from django.urls import path, include
from django.contrib import admin
from .views import fanan_website, knowledge_base, fanan, home, register, logout_view
from django.contrib.auth import views as auth_views
from .views import custom_login
from .views import profile
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('fanan_website', fanan_website, name='fanan_website'),
    path('profile/', profile, name='profile'),
    path('profile/<str:username>/', profile, name='view_profile'),  # View other users' profiles
    # path('profile/', profile, name='profile'),
    # path('profile/<str:username>/', profile, name='profile'),
    
    path('admin/', admin.site.urls),
    path('', fanan, name='fanan'),
    path('home', home, name='home'),
    path('staff/', include('simpleticket.urls')),
    path('administrator/', include('administrator.urls')),
    path('accounts/', include('accounts.urls')),
    path('user/', include('normalusers.urls')),
    # path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),
    path('knowledge_base/', knowledge_base, name='knowledge_base'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path("login/", custom_login, name="login"),
]

# Serve media files correctly
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    