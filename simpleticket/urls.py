from django.urls import path
from . import views
from .views import get_ticket_data,analytics


urlpatterns = [
    path('staff/generate-ticket-status-report/', views.generate_ticket_status_report, name='generate_ticket_status_report'),
    path('generate-agent-performance-report/', views.generate_agent_performance_report, name='generate_agent_performance_report'),
    path('generate-ticket-assignment-report/', views.generate_ticket_assignment_report, name='generate_ticket_assignment_report'),
    path('generate-ticket-report/', views.generate_ticket_summary_report, name='generate_ticket_summary_report'),
    path('view_profile/<int:ticket_id>/', views.view_profile, name='view_profile'),
    path('', views.view_all, name='view_all'),
    path('my-tickets/', views.view_my_tickets, name='my_tickets'),
    path('view/<int:ticket_id>/', views.view, name='view'),
    path('new/', views.create, name='create'),
    path('submit_ticket/', views.submit_ticket, name='submit_ticket'),
    path('update/<int:ticket_id>/', views.update, name='update'),
    path('update_ticket/<int:ticket_id>/', views.update_ticket, name='update_ticket'),
    path('submit_comment/<int:ticket_id>/', views.submit_comment, name='submit_comment'),
    path('delete/<int:ticket_id>/', views.delete_ticket, name='delete_ticket'),
    path('delete_comment/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('project/', views.project, name='project'),
    path("ticket/<int:ticket_id>/pdf/", views.generate_ticket_pdf, name="generate_ticket_pdf"),
    path('analytics/', analytics, name="analytics"),
    path('analytics/data/', get_ticket_data, name="ticket_data"),
    path('analytics/download-csv/', views.download_csv_report, name="download_csv_report"),   
]