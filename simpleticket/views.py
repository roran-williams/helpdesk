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

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from simpleticket.utils import email_user

from django.core.exceptions import PermissionDenied


from django.core.exceptions import PermissionDenied

def ticket_creator_permission_required(view_func):
    """
    This decorator ensures that only the user who created the ticket
    can perform certain actions on it (like updating or deleting).
    """
    def wrapper(request, *args, **kwargs):
        ticket_id = kwargs.get('ticket_id')
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        
        if ticket.created_by != request.user:
            raise PermissionDenied("You do not have permission to edit this ticket.")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


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

from django.core.exceptions import PermissionDenied

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied

@login_required
def submit_ticket(request):
    ticket = Ticket()
    ticket.project = Project.objects.get(pk=int(request.POST['project']))
    ticket.priority = Priority.objects.get(pk=int(request.POST['priority']))
    ticket.status = Status.objects.get(pk=int(request.POST['status']))
    ticket.created_by = request.user

    # Handle case of unassigned tickets
    assigned_option = request.POST.get('assigned', 'unassigned')  # Safely get 'assigned', default to 'unassigned'
    
    if assigned_option == 'unassigned':
        ticket.assigned_to = None
    else:
        # Check if the user has permission to assign tickets
        if not request.user.has_perm('simpleticket.assign_ticket'):
            raise PermissionDenied("You do not have permission to assign tickets.")
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

    # Check if the user has permission to change the status
    if not request.user.has_perm('simpleticket.change_status'):
        # If the status is being changed, deny access
        if status != ticket.status:
            raise PermissionDenied("You do not have permission to change the ticket status.")

    # Update status if necessary (only if permitted)
    if status != ticket.status:
        if text != "":
            text += "\n\n"
        else:
            comment.automated = True
        text += f"<strong>Automated Comment:</strong> Status changed from {ticket.status.name} to {status.name}"
        ticket.status = status
        ticket.save()

    # Create ticket comment
    comment = TicketComment(
        commenter=request.user, 
        text=text, 
        ticket=ticket, 
        time_logged=time_logged, 
        update_time=datetime.now()
    )
    comment.save()

    if ticket.assigned_to and (ticket.assigned_to != comment.commenter):
        message_preamble = f'A ticket you are assigned to has received a comment:\n{request.get_host()}/tickets/view/{ticket.id}/\n\n'
        email_user(ticket.assigned_to, f"Ticket Comment: {ticket.name}", message_preamble + ticket.desc)

    messages.success(request, "The comment has been added.")
    return HttpResponseRedirect(f"/tickets/view/{ticket.id}/")


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
@ticket_creator_permission_required
def update_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    # Check if the user has permission to change the status
    if not request.user.has_perm('simpleticket.change_status'):
        # If the status is being changed, deny access
        status = Status.objects.get(pk=int(request.POST['status']))
        if status != ticket.status:
            raise PermissionDenied("You do not have permission to change the ticket status.")

    project = Project.objects.get(pk=int(request.POST['project']))
    priority = Priority.objects.get(pk=int(request.POST['priority']))
    status = Status.objects.get(pk=int(request.POST['status']))

    assigned_option = request.POST['assigned']
    assigned_to = None if assigned_option == 'unassigned' else User.objects.get(pk=int(assigned_option))

    ticket.project = project
    ticket.priority = priority
    ticket.status = status  # Status update is allowed only if permitted
    ticket.assigned_to = assigned_to
    ticket.name = request.POST['name']
    ticket.desc = request.POST['desc']
    ticket.update_time = datetime.now()
    ticket.save()

    messages.success(request, "The ticket has been updated.")
    return HttpResponseRedirect(f"/tickets/view/{ticket.id}/")



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