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
from simpleticket.utils import email_user
from django.core.exceptions import PermissionDenied
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:  # Only allow staff users
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@admin_required
def create(request):
    priority_list = Priority.objects.all()
    status_list = Status.objects.all()
    project_list = Project.objects.all()
    
    user_list = []
    u = User.objects.all()
    for member in u:
        if member.is_staff:
            user_list.append(member)

    return render(request, 'create.html', {'tab_users': user_list,
                                              'priority_list': priority_list, 'status_list': status_list,
                                              'project_list': project_list})

@login_required
@admin_required
def view(request, ticket_id=1):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
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
@admin_required
def view_all(request):
    my_tickets = Ticket.objects.filter(created_by=request.user)

    # Handle GET parameters
    assigned_filter = request.GET.get("assigned_to")
    created_filter = request.GET.get("created_by")
    priority_filter = request.GET.get("priority")
    status_filter = request.GET.get("status")
    project_filter = request.GET.get("project")
    closed_filter = request.GET.get("show_closed")
    sort_setting = request.GET.get("sort")
    order_setting = request.GET.get("order")

    # Set the default sort and order params
    if not sort_setting:
        sort_setting = "id"
    if not order_setting:
        order_setting = "dsc"

    # Do filtering for GET parameters
    args = {}
    if assigned_filter and assigned_filter != 'unassigned':
        args['assigned_to'] = assigned_filter
    if assigned_filter and assigned_filter == 'unassigned':
        args['assigned_to__exact'] = None
    if created_filter:
        args['created_by'] = created_filter
    if priority_filter:
        args['priority'] = priority_filter
    if status_filter:
        args['status'] = status_filter
    if project_filter:
        args['project'] = project_filter
    tickets = Ticket.objects.filter(**args)

    # Filter out closed tickets
    if not closed_filter or closed_filter.lower() != "true":
        tickets = tickets.exclude(status__hide_by_default=True)

    # Sort the tickets
    sort_filter = sort_setting
    if sort_filter == 'assigned':
        sort_filter = 'assigned_to'
    if sort_filter == 'updated':
        sort_filter = 'update_time'
    if order_setting == 'dsc':
        sort_filter = '-' + sort_filter
    tickets = tickets.order_by(sort_filter)

    # Create filter string
    try:
        filterArray = []
        if assigned_filter and assigned_filter != 'unassigned':
            assigned = User.objects.get(pk=assigned_filter)
            filterArray.append("Assigned to: " + assigned.username)
        if assigned_filter and assigned_filter == 'unassigned':
            filterArray.append("Assigned to: Unassigned")
        if created_filter:
            created = User.objects.get(pk=created_filter)
            filterArray.append("Assigned to: " + created.username)
        if priority_filter:
            priority = Priority.objects.get(pk=priority_filter)
            filterArray.append("Priority: " + priority.name)
        if status_filter:
            status = Status.objects.get(pk=status_filter)
            filterArray.append("Status: " + status.name)
        if project_filter:
            project = Project.objects.get(pk=project_filter)
            filterArray.append("Project: " + project.name)
        if filterArray:
            filter = ', '.join(filterArray)
        else:
            filter = "All"
        filter_message = None
    except Exception as e:
        filter = "Filter Error"
        filter_message = e

    # Handle the case of no visible tickets
    if tickets.count() < 1:
        filter_message = "No tickets meet the current filtering critera."

    # Generate the base URL for showing closed tickets & sorting
    get_dict = request.GET.copy()
    if get_dict.get('show_closed'):
        del get_dict['show_closed']
    if get_dict.get('sort'):
        del get_dict['sort']
    if get_dict.get('order'):
        del get_dict['order']
    base_url = request.path_info + "?" + urlencode(get_dict)

    if closed_filter == 'true':
        show_closed = 'true'
    else:
        show_closed = 'false'

    # Paginate
    paginator = Paginator(tickets, 20)
    try: # Make sure page request is an int. If not, deliver first page.
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        tickets = paginator.page(page)
    except (EmptyPage, InvalidPage):
        tickets = paginator.page(paginator.num_pages)

    # Generate next page link
    pairs = []
    for key in request.GET.keys():
        if key != 'page':
            pairs.append(key + "=" + request.GET.get(key))
    if tickets.has_next():
        pairs.append('page=' + str(tickets.next_page_number()))
    else:
        pairs.append('page=0')
    get_params = '&'.join(pairs)
    next_link = request.path + '?' + get_params

    # Generate previous page link
    pairs = []
    for key in request.GET.keys():
        if key != 'page':
            pairs.append(key + "=" + request.GET.get(key))
    if tickets.has_previous():
        pairs.append('page=' + str(tickets.previous_page_number()))
    else:
        pairs.append('page=0')
    get_params = '&'.join(pairs)
    prev_link = request.path + '?' + get_params

    return render(request, 'view_all.html', {'tickets': tickets,'my_tickets':my_tickets, 'filter': filter,
                                                          'filter_message': filter_message, 'base_url': base_url,
                                                          'next_link': next_link, 'prev_link': prev_link,
                                                          'sort': sort_setting, 'order': order_setting,
                                                          'show_closed': show_closed})


@login_required
def view_my_tickets(request):
    user_tickets = Ticket.objects.filter(created_by=request.user)
    # print(tickets)
    # Handle GET parameters 
    assigned_filter = request.GET.get("assigned_to")
    created_filter = request.GET.get("created_by")
    priority_filter = request.GET.get("priority")
    status_filter = request.GET.get("status")
    project_filter = request.GET.get("project")
    closed_filter = request.GET.get("show_closed")
    sort_setting = request.GET.get("sort")
    order_setting = request.GET.get("order")

    # Set the default sort and order params
    if not sort_setting:
        sort_setting = "id"
    if not order_setting:
        order_setting = "dsc"

    # Do filtering for GET parameters
    args = {}
    if assigned_filter and assigned_filter != 'unassigned':
        args['assigned_to'] = assigned_filter
    if assigned_filter and assigned_filter == 'unassigned':
        args['assigned_to__exact'] = None
    if created_filter:
        args['created_by'] = created_filter
    if priority_filter:
        args['priority'] = priority_filter
    if status_filter:
        args['status'] = status_filter
    if project_filter:
        args['project'] = project_filter
    tickets = user_tickets.filter(**args)
    

    # Filter out closed tickets
    if not closed_filter or closed_filter.lower() != "true":
        tickets = tickets.exclude(status__hide_by_default=True)

    # Sort the tickets
    sort_filter = sort_setting
    if sort_filter == 'assigned':
        sort_filter = 'assigned_to'
    if sort_filter == 'updated':
        sort_filter = 'update_time'
    if order_setting == 'dsc':
        sort_filter = '-' + sort_filter
    tickets = tickets.order_by(sort_filter)

    # Create filter string
    try:
        filterArray = []
        if assigned_filter and assigned_filter != 'unassigned':
            assigned = User.objects.get(pk=assigned_filter)
            filterArray.append("Assigned to: " + assigned.username)
        if assigned_filter and assigned_filter == 'unassigned':
            filterArray.append("Assigned to: Unassigned")
        if created_filter:
            created = User.objects.get(pk=created_filter)
            filterArray.append("Assigned to: " + created.username)
        if priority_filter:
            priority = Priority.objects.get(pk=priority_filter)
            filterArray.append("Priority: " + priority.name)
        if status_filter:
            status = Status.objects.get(pk=status_filter)
            filterArray.append("Status: " + status.name)
        if project_filter:
            project = Project.objects.get(pk=project_filter)
            filterArray.append("Project: " + project.name)
        if filterArray:
            filter = ', '.join(filterArray)
        else:
            filter = "All"
        filter_message = None
    except Exception as e:
        filter = "Filter Error"
        filter_message = e

    # Handle the case of no visible tickets
    if tickets.count() < 1:
        filter_message = "No tickets meet the current filtering critera."

    # Generate the base URL for showing closed tickets & sorting
    get_dict = request.GET.copy()
    if get_dict.get('show_closed'):
        del get_dict['show_closed']
    if get_dict.get('sort'):
        del get_dict['sort']
    if get_dict.get('order'):
        del get_dict['order']
    base_url = request.path_info + "?" + urlencode(get_dict)

    if closed_filter == 'true':
        show_closed = 'true'
    else:
        show_closed = 'false'

    # Paginate
    paginator = Paginator(tickets, 20)
    try: # Make sure page request is an int. If not, deliver first page.
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        tickets = paginator.page(page)
    except (EmptyPage, InvalidPage):
        tickets = paginator.page(paginator.num_pages)

    # Generate next page link
    pairs = []
    for key in request.GET.keys():
        if key != 'page':
            pairs.append(key + "=" + request.GET.get(key))
    if tickets.has_next():
        pairs.append('page=' + str(tickets.next_page_number()))
    else:
        pairs.append('page=0')
    get_params = '&'.join(pairs)
    next_link = request.path + '?' + get_params

    # Generate previous page link
    pairs = []
    for key in request.GET.keys():
        if key != 'page':
            pairs.append(key + "=" + request.GET.get(key))
    if tickets.has_previous():
        pairs.append('page=' + str(tickets.previous_page_number()))
    else:
        pairs.append('page=0')
    get_params = '&'.join(pairs)
    prev_link = request.path + '?' + get_params

    

    return render(request, 'my-tickets.html', { 'tickets': tickets, 'filter': filter,
                                                          'filter_message': filter_message, 'base_url': base_url,
                                                          'next_link': next_link, 'prev_link': prev_link,
                                                          'sort': sort_setting, 'order': order_setting,
                                                          'show_closed': show_closed})

@login_required
@admin_required
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
        if not request.user.has_perm('simpleitcket.assign_ticket'):
            raise PermissionDenied("You do not have permission to assign tickets.")
        ticket.assigned_to = User.objects.get(pk=int(assigned_option))

    ticket.creation_time = datetime.now()
    ticket.update_time = datetime.now()
    ticket.name = request.POST['name']
    ticket.desc = request.POST['desc']
    ticket.time_logged = 0
    ticket.save()
    try:
        email_user(to_email=request.user.email,subject="Helpdesk Ticket Created",message=f"Your ticket '{ticket.name}' has been received.")
        messages.success(request, "You will receive a confirmation email from help desk.")
        if ticket.assigned_to != None:
            email_user(to_email=ticket.assigned_to.email,subject="You Have Been Assigned A ticket",message=f"ticket '{ticket.name}' has been assigned to you.")
    except Exception:
        messages.error(request, "could not send email at the moment check your internet connection.")

    messages.success(request, "The ticket has been created.")
    return HttpResponseRedirect("/tickets/view/" + str(ticket.id) + "/")




@login_required
@admin_required
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
        try:
            email_user(to_email=ticket.assigned_to.email,subject="A ticket you are assigned to has received a comment",message=f"ticket '{ticket.name}' has received a comment, check it!!.")
        except Exception:
            messages.error(request, "email not sent, but coment is still saved.")

    messages.success(request, "The comment has been added.")
    return HttpResponseRedirect(f"/tickets/view/{ticket.id}/")


@login_required
@admin_required
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
@admin_required
def update_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    previously_assigned = ticket.assigned_to

    # Check if the user has permission to change the status
    if not request.user.has_perm('simpleticket.change_status'):
        # If the status is being changed, deny access
        status = Status.objects.get(pk=int(request.POST['status']))
        if status != ticket.status:
            raise PermissionDenied("You do not have permission to change the ticket status.")

    project = Project.objects.get(pk=int(request.POST['project']))
    priority = Priority.objects.get(pk=int(request.POST['priority']))
    status = Status.objects.get(pk=int(request.POST['status']))

    if not request.user.has_perm('assign_ticket'):
        raise PermissionDenied("You do not have permission to assign tickets.")

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

    if ticket.assigned_to != previously_assigned:
        try:
            email_user(to_email=previously_assigned.email,subject="You are no longer assigened to this ticket",message=f"ticket '{ticket.name}' has been updated,you have been unassigned by '{request.user}' check it!!.")
        except Exception:
            messages.success(request, "asignee changed")

    try:
        if ticket.created_by != request.user:
            email_user(to_email=ticket.created_by.email,subject="Your ticket has been updated",message=f"ticket '{ticket.name}' has been updated, check it!!.")
        if ticket.assigned_to != request.user:
            email_user(to_email=ticket.assigned_to.email,subject="A ticket assigned to you has been updated",message=f"ticket '{ticket.name}' has been updated, check it!!.")
    except Exception:
            messages.error(request, "email not send email to the ticket owner or assinee.")    

    messages.success(request, "The ticket has been updated.")
    return HttpResponseRedirect(f"/tickets/view/{ticket.id}/")



@login_required
@admin_required
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)

    if not request.user.has_perm('simpleticket.delete_ticket'):
        raise PermissionDenied("You do not have permission to delete this ticket.")

    TicketComment.objects.filter(ticket=ticket).delete()
    ticket.delete()

    messages.success(request, "The ticket has been deleted.")
    
    try:
        if request.user != ticket.created_by:
            email_user(to_email=ticket.created_by.email,subject="your ticket has been deleted",message=f"ticket '{ticket.name}' has been deleted!.")
        if request.user != ticket.assigned_to:
            email_user(to_email=ticket.assigned_to.email,subject="A ticket you are assigned to has been deleted",message=f"ticket '{ticket.name}' has been deleted!.")
        email_user(to_email=request.user.email,subject="You have deleted a ticket",message=f"ticket '{ticket.name}' has been deleted!.")
    except Exception:
        messages.error(request, "email not sent.")
    return HttpResponseRedirect("/tickets/")

@login_required
@admin_required
def delete_comment(request, comment_id):
    # Get the ticket
    comment = get_object_or_404(TicketComment, pk=comment_id)
    # Delete the ticket
    comment.delete()
    messages.success(request, "The comment has been deleted.")

    try:
        email_user(to_email=comment.commenter.email,subject="coment has been delete",message=f"comment '{comment.ticket.name}' has been deleted!.")
    except Exception:
        messages.error(request, "email not sent but comment deleted.")
    return HttpResponseRedirect("/tickets/view/" + str(comment.ticket.id) + "/")

@login_required
@admin_required
def project(request):
    project_list = Project.objects.all()

    return render(request, 'project.html', {'project_list': project_list})