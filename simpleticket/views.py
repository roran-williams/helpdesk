from datetime import datetime
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from simpleticket.models import Priority, Status, Project, Ticket, TicketComment
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from .forms import RegistrationForm

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from simpleticket.utils import email_user

from django.core.exceptions import PermissionDenied

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your account has been created! You can now log in.")
            return redirect('login')  # Redirect to the login page after registration
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:  # Only allow staff users
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def create(request):
    priority_list = Priority.objects.all()
    status_list = Status.objects.all()
    project_list = Project.objects.all()
    user_list = User.objects.all()
    print(user_list)

    return render(request, 'create.html', {'tab_users': user_list,
                                              'priority_list': priority_list, 'status_list': status_list,
                                              'project_list': project_list})

@login_required
def view(request, ticket_id=1):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    # Check if the user is the ticket creator
    if ticket.created_by != request.user:
        raise PermissionDenied("You do not have permission to view this ticket.")

    status_list = Status.objects.all()

    # Paginate Ticket_Comments
    ticket_comments = ticket.ticketcomment_set.order_by('-id')
    paginator = Paginator(ticket_comments, 10)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        ticket_comments = paginator.page(page)
    except (EmptyPage, InvalidPage):
        ticket_comments = paginator.page(paginator.num_pages)

    return render(request, 'view.html', {'ticket': ticket, 'status_list': status_list, 'ticket_comments': ticket_comments})

@login_required
def view_all(request):
    # Filter tickets by the logged-in user
    tickets = Ticket.objects.filter(created_by=request.user)

    # Handle GET parameters for additional filtering
    assigned_filter = request.GET.get("assigned_to")
    priority_filter = request.GET.get("priority")
    status_filter = request.GET.get("status")
    project_filter = request.GET.get("project")
    closed_filter = request.GET.get("show_closed")
    sort_setting = request.GET.get("sort")
    order_setting = request.GET.get("order")

    if assigned_filter:
        tickets = tickets.filter(assigned_to=assigned_filter)
    if priority_filter:
        tickets = tickets.filter(priority=priority_filter)
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if project_filter:
        tickets = tickets.filter(project=project_filter)
    if not closed_filter or closed_filter.lower() != "true":
        tickets = tickets.exclude(status__hide_by_default=True)

    # Sort tickets
    sort_filter = sort_setting or 'id'
    order = '-' if order_setting == 'dsc' else ''
    tickets = tickets.order_by(order + sort_filter)

    # Pagination
    paginator = Paginator(tickets, 20)
    page = request.GET.get('page', 1)
    try:
        tickets = paginator.page(page)
    except (EmptyPage, InvalidPage):
        tickets = paginator.page(paginator.num_pages)

    return render(request, 'view_all.html', {'tickets': tickets})

@login_required
def submit_ticket(request):
    ticket = Ticket()
    ticket.project = Project.objects.get(pk=int(request.POST['project']))
    ticket.priority = Priority.objects.get(pk=int(request.POST['priority']))
    ticket.status = Status.objects.get(pk=int(request.POST['status']))
    ticket.created_by = request.user

    # Handle case of unassigned tickets
    assigned_option = request.POST['assigned']
    if assigned_option == 'unassigned':
        ticket.assigned_to = None
    else:
        ticket.assigned_to = User.objects.get(pk=int(assigned_option))

    ticket.creation_time = datetime.now()
    ticket.update_time = datetime.now()
    ticket.name = request.POST['name']
    ticket.desc = request.POST['desc']
    ticket.time_logged = 0
    ticket.save()

    # Email the assigned user if different than creating user
    if ticket.assigned_to is not None and (ticket.assigned_to != ticket.created_by):
        message_preamble = 'You have been assigned a ticket:\n' + \
                           request.get_host() + '/tickets/view/' + str(ticket.id) + '/\n\n'
        email_user(ticket.assigned_to, "Ticket Assigned: " + ticket.name, message_preamble + ticket.desc)

    messages.success(request, "The ticket has been created.")

    return HttpResponseRedirect("/tickets/view/" + str(ticket.id) + "/")

@login_required
def submit_comment(request, ticket_id):
    text = request.POST["comment-text"]
    time_logged = float(request.POST["comment-time-logged"])
    status = Status.objects.get(pk=int(request.POST["comment-status"]))
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    # Create ticket comment
    comment = TicketComment()

    # Update status if necessary
    if status != ticket.status:
        if text != "":
            text += "\n\n"
        else:
            comment.automated = True
        text += "<strong>Automated Comment:</strong> Status changed from " + ticket.status.name + " to " + status.name
        ticket.status = status
        ticket.save()

    # Set ticket comment properties
    comment.commenter = request.user
    comment.text = text
    comment.ticket = ticket
    comment.time_logged = time_logged
    comment.update_time = datetime.now()
    comment.save()

    # Email the assigned user if different than commenting user
    if ticket.assigned_to is not None and (ticket.assigned_to != comment.commenter):
        message_preamble = 'A ticket you are assigned to has received a comment:\n' + \
                           request.get_host() + '/tickets/view/' + str(ticket.id) + '/\n\n'
        email_user(ticket.assigned_to, "Ticket Comment: " + ticket.name, message_preamble + ticket.desc)

    messages.success(request, "The comment has been added.")

    return HttpResponseRedirect("/tickets/view/" + str(ticket.id) + "/")

@login_required
def update(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    priority_list = Priority.objects.all()
    status_list = Status.objects.all()
    project_list = Project.objects.all()
    users_list = User.objects.all()

    return render(request, 'update.html', {'ticket': ticket, 'tab_users': users_list,
                                                        'priority_list': priority_list, 'status_list': status_list,
                                                        'project_list': project_list})


@login_required
def update_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if ticket.created_by != request.user:
        raise PermissionDenied("You do not have permission to update this ticket.")

    # Rest of the function remains unchanged...

    project = Project.objects.get(pk=int(request.POST['project']))
    priority = Priority.objects.get(pk=int(request.POST['priority']))
    status = Status.objects.get(pk=int(request.POST['status']))

    # Handle case of unassigned tickets
    assigned_option = request.POST['assigned']
    if assigned_option == 'unassigned':
        assigned_to = None
    else:
        assigned_to = User.objects.get(pk=int(assigned_option))

    name = request.POST['name']
    desc = request.POST['desc']

    # Generate change auto-comment
    changes = []
    if project != ticket.project:
        changes.append("Changed project from " + ticket.project.name + " to " + project.name)
    if priority != ticket.priority:
        changes.append("Changed priority from " + ticket.priority.name + " to " + priority.name)
    if status != ticket.status:
        changes.append("Changed status from " + ticket.status.name + " to " + status.name)
    if assigned_to != ticket.assigned_to:
        changes.append("Changed assigned to from " + str(ticket.assigned_to) + " to " + str(assigned_to))
    if name != ticket.name:
        changes.append("Changed summary from " + ticket.name + " to " + name)
    if desc != ticket.desc:
        changes.append("Updated description")

    # Save changes to the ticket
    ticket.project = project
    ticket.priority = priority
    ticket.status = status
    ticket.assigned_to = assigned_to
    ticket.name = name
    ticket.desc = desc
    ticket.update_time = datetime.now()
    ticket.save()

    # Add the auto-generated comment if necessary
    if len(changes) > 0:
        auto = TicketComment()
        auto.ticket = ticket
        auto.commenter = request.user
        auto.time_logged = 0
        auto.update_time = datetime.now()
        auto.text = "<strong>Automated Comment:</strong> " + ("; ".join(changes))
        auto.automated = True
        auto.save()

    # Email the assigned user if updated
    if ticket.assigned_to is not None and (ticket.assigned_to != auto.commenter):
        message_preamble = 'A ticket you are assigned to you has been updated:\n' +\
                           request.get_host() + '/tickets/view/' + str(ticket.id) + '/\n\n'
        email_user(ticket.assigned_to, "Ticket Update: " + ticket.name, message_preamble + ticket.desc)

    messages.success(request, "The ticket has been updated.")

    return HttpResponseRedirect("/tickets/view/" + str(ticket.id) + "/")

@login_required
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if ticket.created_by != request.user:
        raise PermissionDenied("You do not have permission to delete this ticket.")

    TicketComment.objects.filter(ticket=ticket).delete()
    ticket.delete()

    messages.success(request, "The ticket has been deleted.")
    return HttpResponseRedirect("/tickets/")


@login_required
def delete_comment(request, comment_id):
    # Get the ticket
    comment = get_object_or_404(TicketComment, pk=comment_id)

    # Delete the ticket
    comment.delete()

    messages.success(request, "The comment has been deleted.")
    return HttpResponseRedirect("/tickets/view/" + str(comment.ticket.id) + "/")

@login_required
def project(request):
    project_list = Project.objects.all()

    return render(request, 'project.html', {'project_list': project_list})