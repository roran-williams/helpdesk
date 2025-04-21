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
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import HttpResponse
import os
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

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


def profile(request):
    user = request.user
    return render(request, 'u/profile.html',{'user':user})

@login_required
def create(request):
    priority_list = Priority.objects.all()
    status_list = Status.objects.all()
    project_list = Project.objects.all()
    user_list = User.objects.all()
    support_staff = []
    for member in user_list:
        if member.has_perm('simpleticket.change_status') and not member.is_superuser:
            support_staff.append(member)

    return render(request, 'new/create.html', {'tab_users': support_staff,
                                              'priority_list': priority_list, 'status_list': status_list,
                                              'project_list': project_list})

@login_required
@ticket_creator_permission_required
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

    return render(request, 'new/view.html', {'user':request.user, 'ticket': ticket, 'status_list': status_list, 'ticket_comments': ticket_comments})

@login_required
def view_all(request):
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

    

    return render(request, 'new/view_all.html', { 'tickets': tickets, 'filter': filter,
                                                          'filter_message': filter_message, 'base_url': base_url,
                                                          'next_link': next_link, 'prev_link': prev_link,
                                                          'sort': sort_setting, 'order': order_setting,
                                                          'show_closed': show_closed})
from django.core.exceptions import PermissionDenied

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied

@login_required
def submit_ticket(request):
    
    ticket = Ticket()
    ticket.project = Project.objects.get(pk=int(request.POST['project']))
    ticket.priority = Priority.objects.get(pk=int(request.POST['priority']))
    ticket.created_by = request.user
    ticket.status = Status.objects.get(pk=int(request.POST['status']))
    

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
    return HttpResponseRedirect("/user/view/" + str(ticket.id) + "/")


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

    # # Update status if necessary (only if permitted)
    # if status != ticket.status:
    #     if text != "":
    #         text += "\n\n"
    #     else:
    #         comment.automated = True
    #     text += f"<strong>Automated Comment:</strong> Status changed from {ticket.status.name} to {status.name}"
    #     ticket.status = status
    #     ticket.save()

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
    return HttpResponseRedirect(f"/user/view/{ticket.id}/")


# def submit_comment(request, ticket_id):
#     text = request.POST["comment-text"]
#     time_logged = float(request.POST["comment-time-logged"])
#     status = Status.objects.get(pk=int(request.POST["comment-status"]))
#     ticket = get_object_or_404(Ticket, pk=ticket_id)

#     # Check if the user has permission to change the status
#     if not request.user.has_perm('simpleticket.change_status'):
#         # If the status is being changed, deny access
#         if status != ticket.status:
#             raise PermissionDenied("You do not have permission to change the ticket status.")


#     # Update status if necessary (only if permitted)
#     if status != ticket.status:
#         if text != "":
#             text += "\n\n"
#         else:
#             comment.automated = True
#         text += f"<strong>Automated Comment:</strong> Status changed from {ticket.status.name} to {status.name}"
#         ticket.status = status
#         ticket.save()

#     # Create ticket comment
#     comment = TicketComment(
#         commenter=request.user, 
#         text=text, 
#         ticket=ticket, 
#         time_logged=time_logged, 
#         update_time=datetime.now()
#     )
    
#     comment.save()

#     if ticket.assigned_to and (ticket.assigned_to != comment.commenter):
#         try:
#             email_user(to_email=ticket.assigned_to.email,subject="A ticket you are assigned to has received a comment",message=f"ticket '{ticket.name}' has received a comment, check it!!.")
#         except Exception:
#             messages.error(request, "email not sent, but coment is still saved.")

#     messages.success(request, "The comment has been added.")
#     return HttpResponseRedirect(f"/staff/view/{ticket.id}/")



@login_required
def update(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    allowed_to_change_ticket = request.user.has_perm('simpleticket.change_ticket') 
    allowed_to_change_ticket_status = request.user.has_perm('simpleticket.change_status')
    allowed_to_change_ticket_project = request.user.has_perm('simpleticket.change_project')
    allowed_to_change_ticket_priority = request.user.has_perm('simpleticket.change_priority')
    allowed_to_assign_ticket = request.user.has_perm('simpleticket.assign_ticket')
    you_created_ticket = ticket.created_by == request.user
    set_priority = you_created_ticket and (ticket.assigned_to == None)
    
    priority_list = Priority.objects.all()
    status_list = Status.objects.all()
    project_list = Project.objects.all()
    users_list = User.objects.all()
    support_staff = []
    for member in users_list:
        if member.has_perm('simpleticket.change_status') and not member.is_superuser:
            support_staff.append(member)


    return render(request, 'new/update.html', {
        'ticket': ticket, 
        'tab_users': support_staff,
        'allowed_to_change_ticket':allowed_to_change_ticket,
        'allowed_to_assign_ticket':allowed_to_assign_ticket, 
        'allowed_to_change_ticket_project':allowed_to_change_ticket_project,
        'allowed_to_change_ticket_status':allowed_to_change_ticket_status,
        'allowed_to_change_ticket_priority':allowed_to_change_ticket_priority,
        'priority_list': priority_list, 
        'status_list': status_list,
        'project_list': project_list,
        'set_priority':set_priority,
        'you_created_ticket':you_created_ticket,
        })



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
    return HttpResponseRedirect(f"/user/view/{ticket.id}/")



@login_required
@ticket_creator_permission_required
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    if ticket.created_by != request.user:
        raise PermissionDenied("You do not have permission to delete this ticket.")
    TicketComment.objects.filter(ticket=ticket).delete()
    ticket.delete()
    messages.success(request, "The ticket has been deleted.")
    return HttpResponseRedirect("/user/")

 
@login_required
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
    return HttpResponseRedirect("/user/view/" + str(comment.ticket.id) + "/")

@login_required
def project(request):
    project_list = Project.objects.all()
    return render(request, 'u/project.html', {'project_list': project_list})

@ticket_creator_permission_required
def generate_ticket_pdf(request, ticket_id):
    # Retrieve the ticket from the database
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return HttpResponse("Ticket not found", status=404)

    # Define the response as a PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="ticket_{ticket_id}.pdf"'

    # Create PDF document
    pdf = SimpleDocTemplate(response, pagesize=letter)
    elements = []

    # Add company logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'fanan_logo.jpg')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=100, height=50)
        elements.append(logo)

    # Add ticket title
    title_style = ParagraphStyle(name="TitleStyle", fontSize=18, alignment=1, spaceAfter=10, textColor=colors.black)
    elements.append(Paragraph(f"<b>Ticket #{ticket.id}</b>", title_style))
    elements.append(Spacer(1, 10))

    # Define priority color style
    priority_style = ParagraphStyle(name="PriorityStyle", textColor=ticket.priority.display_color)

    # Ticket details table
    data = [
        ["Subject:", ticket.name],
        ["Project:", ticket.project],
        ["Status:", ticket.status],
        ["Priority:", Paragraph(ticket.priority.name, priority_style)],
        ["Time Allocated:", f"{ticket.time_logged} HRS"],
        ["Created By:", ticket.created_by.username],
        ["Assigned To:", ticket.assigned_to.username if ticket.assigned_to else "Unassigned"],
        ["Created On:", ticket.creation_time.strftime("%Y-%m-%d %H:%M:%S")],
        ["Last Updated:", ticket.update_time.strftime("%Y-%m-%d %H:%M:%S")],
    ]

    table = Table(data, colWidths=[150, 350])
    table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
    )

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Description
    desc_style = ParagraphStyle(name="DescriptionStyle", fontSize=12, spaceBefore=10, spaceAfter=5, textColor=colors.black)
    elements.append(Paragraph("<b>Description</b>", desc_style))
    elements.append(Paragraph(ticket.desc, desc_style))

    # Build the PDF
    pdf.build(elements)
    return response
