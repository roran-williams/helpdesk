from django.urls import path
from . import views

urlpatterns = [
    path('', views.view_all, name='view_all'),
    path('view/<int:ticket_id>/', views.view, name='view'),
    path('new/', views.create, name='create'),
    path('submit_ticket/', views.submit_ticket, name='submit_ticket'),
    path('update/<int:ticket_id>/', views.update, name='update'),
    path('update_ticket/<int:ticket_id>/', views.update_ticket, name='update_ticket'),
    path('submit_comment/<int:ticket_id>/', views.submit_comment, name='submit_comment'),
    path('delete/<int:ticket_id>/', views.delete_ticket, name='delete_ticket'),
    path('delete_comment/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('project/', views.project, name='project'),
    path('register/', views.register, name='register'),
]

