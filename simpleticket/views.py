from datetime import datetime
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from simpleticket.models import Profile, Priority, Status, Project, Ticket, TicketComment
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from simpleticket.utils import email_user
from django.core.exceptions import PermissionDenied
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from django.http import HttpResponse
import os
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

from django.http import HttpResponse
from datetime import datetime
from django.db.models import Q
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.pdfgen import canvas
from .models import Ticket, User
import csv
from django.http import HttpResponse



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
    
    user_list = User.objects.all()
    support_staff = []
    for member in user_list:
        if member.has_perm('simpleticket.change_status') and not member.is_superuser:
            support_staff.append(member)

    return render(request, 'staff/create.html', {'tab_users': support_staff,
                                              'priority_list': priority_list, 'status_list': status_list,
                                              'project_list': project_list})

@login_required
@admin_required
def view(request, ticket_id=1):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    status_list = Status.objects.all()
    profile = Profile.objects.filter(user=ticket.created_by)
    
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

    return render(request, 'staff/view.html', {'profile':profile,'ticket': ticket, 'status_list': status_list, 'ticket_comments': ticket_comments})


def view_profile(request,ticket_id=1):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    profile = Profile.objects.filter(user=ticket.created_by)
    assigned_profile = Profile.objects.filter(user=ticket.assigned_to)
    
    for i in assigned_profile:
        afirst_name = i.user.first_name
        alast_name = i.user.last_name
        aemail = i.user.email
        ausername = i.user.username
        aaddress = i.address
        acontact = i.contact_number
        aorganization = i.organization
        adate = i.created_at
        aimage = i.get_profile_picture()
        arole = i.role

    for i in profile:
        first_name = i.user.first_name
        last_name = i.user.last_name
        email = i.user.email
        username = i.user.username
        address = i.address
        contact = i.contact_number
        organization = i.organization
        date = i.created_at
        image = i.get_profile_picture()
        role = i.role
  
    return render(request, "staff/profile.html", {
        'profile':profile,
        "address":address,
        'organization':organization,
        'email':email,
        'username':username,
        'first_name':first_name,
        'last_name':last_name,
        'contact':contact,
        'date':date,
        'image':image,
        'role':role,
        "aaddress":aaddress,
        'aorganization':aorganization,
        'aemail':aemail,
        'ausername':ausername,
        'afirst_name':afirst_name,
        'alast_name':alast_name,
        'acontact':acontact,
        'adate':adate,
        'aimage':aimage,
        'arole':arole
         })


@login_required
@admin_required
def view_all(request):
    my_tickets = Ticket.objects.filter(created_by=request.user)
    allowed_to_change_ticket_status = request.user.has_perm('simpleticket.change_status')
    
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

    return render(request, 'staff/view_all.html', {
        'tickets': tickets,
        'my_tickets':my_tickets,
          'filter': filter,
          'allowed_to_change_ticket_status':allowed_to_change_ticket_status,
            'filter_message': filter_message, 'base_url': base_url,
            'next_link': next_link, 'prev_link': prev_link,
            'sort': sort_setting, 'order': order_setting,
            'show_closed': show_closed,
            })
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

    

    return render(request, 'staff/view_all.html', { 'tickets': tickets, 'filter': filter,
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
    return HttpResponseRedirect("/staff/view/" + str(ticket.id) + "/")

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
    return HttpResponseRedirect(f"/staff/view/{ticket.id}/")

@login_required
@admin_required
def update(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    allowed_to_change_ticket = request.user.has_perm('simpleticket.change_ticket') 
    allowed_to_change_ticket_status = request.user.has_perm('simpleticket.change_status')
    allowed_to_change_ticket_project = request.user.has_perm('simpleticket.change_project')
    allowed_to_change_ticket_priority = request.user.has_perm('simpleticket.change_priority')
    allowed_to_assign_ticket = request.user.has_perm('simpleticket.assign_ticket')
    
    priority_list = Priority.objects.all()
    status_list = Status.objects.all()
    project_list = Project.objects.all()
    users_list = User.objects.filter(is_staff=True)
    support_staff = []
    for u in users_list:
        if u.has_perm('simpleticket.change_status') and not u.is_superuser:
            support_staff.append(u)
            

    return render(request, 'staff/update.html', {
        'ticket': ticket,
        'allowed_to_change_ticket':allowed_to_change_ticket,
        'allowed_to_assign_ticket':allowed_to_assign_ticket, 
        'allowed_to_change_ticket_project':allowed_to_change_ticket_project,
        'allowed_to_change_ticket_status':allowed_to_change_ticket_status,
        'allowed_to_change_ticket_priority':allowed_to_change_ticket_priority,
        'tab_users': support_staff,
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

     # Check if the user has permission to assign tickets
    if not request.user.has_perm('simpleticket.assign_ticket'):
        # If the assinee is being changed, deny access
        assigned_option = request.POST['assigned']
        assigned = None if assigned_option == 'unassigned' else User.objects.get(pk=int(request.POST['assigned']))
        if assigned != ticket.assigned_to:
            raise PermissionDenied("You do not have permission to assign tickets")
            
    
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
    return HttpResponseRedirect(f"/staff/view/{ticket.id}/")

@login_required
@admin_required
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    created_ticket = ticket.created_by == request.user
    if not (request.user.has_perm('simpleticket.delete_ticket') or request.user.is_superuser or created_ticket):
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
    return HttpResponseRedirect("/staff/")

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
    return HttpResponseRedirect("/staff/view/" + str(comment.ticket.id) + "/")

@login_required
@admin_required
def project(request):
    project_list = Project.objects.all()

    return render(request, 'project.html', {'project_list': project_list})
@admin_required
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



@admin_required
def get_ticket_data(request):
    """ API to return ticket analytics as JSON """

    # 📊 Ticket Status Distribution
    ticket_status = Ticket.objects.values('status__name').annotate(count=Count('id'))
    
    # 📅 Tickets Over Time (Last 30 Days)
    last_30_days = now() - timedelta(days=30)
    tickets_per_day = (
        Ticket.objects.filter(creation_time__gte=last_30_days)
        .annotate(day=TruncDate('creation_time'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    # 🎯 Agent Performance
    agent_performance = (
        Ticket.objects.filter(status__name="Closed")
        .values('assigned_to__username')
        .annotate(resolved_tickets=Count('id'))
        .order_by('-resolved_tickets')
    )

    # ⏳ Average Resolution Time
    avg_resolution = Ticket.objects.aggregate(Avg('time_logged'))['time_logged__avg'] or 0

    data = {
        "ticket_status": list(ticket_status),
        "tickets_over_time": list(tickets_per_day),
        "agent_performance": list(agent_performance),
        "avg_resolution": round(avg_resolution, 2),
    }
    
    return JsonResponse(data)

#reports

@admin_required
def analytics(request):
    return render(request, 'staff/analytics.html')


@admin_required
def download_csv_report(request):
    """ Generate a CSV report for analytics """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="helpdesk_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(["Status", "Ticket Count"])
    
    for status in Ticket.objects.values('status__name').annotate(count=Count('id')):
        writer.writerow([status['status__name'], status['count']])

    return response


def generate_ticket_summary_report(request):
    # Fetch filters from request
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    status = request.GET.get("status")
    priority = request.GET.get("priority")
    
    # Filter tickets based on user input
    tickets = Ticket.objects.all()
    if start_date and end_date:
        tickets = tickets.filter(creation_time__range=[start_date, end_date])
    if status:
        tickets = tickets.filter(status__name=status)
    if priority:
        tickets = tickets.filter(priority__name=priority)
    
    # Create HTTP response with PDF content
    response = HttpResponse(content_type='application/pdf')
    filename = f"Ticket_Report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Create PDF canvas
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    
    # Add logo (Assuming logo is stored in static files)
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'fanan_logo.jpg')
    # logo_path = "static/images/fanan_logo.png"  # Adjust path as needed
    p.drawImage(logo_path, 40, height - 80, width=100, height=50)
    
    # Add Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(150, height - 60, "Ticket Summary Report")
    p.setFont("Helvetica", 10)
    p.drawString(150, height - 75, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Table Data
    data = [["Ticket ID", "Subject", "Status", "Priority", "Agent","Client"]]
    for ticket in tickets:
        data.append([ticket.id, ticket.name, ticket.status, ticket.priority, ticket.assigned_to.username if ticket.assigned_to else "Unassigned", ticket.created_by.username])
    
    # Create Table
    table = Table(data, colWidths=[70, 200, 80, 80, 100,80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    # Draw Table
    table.wrapOn(p, width, height)
    table.drawOn(p, 0, height - 200)
    
    # Save PDF
    p.showPage()
    p.save()
    return response


def generate_ticket_assignment_report(request):
    # Fetch filters from request
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    
    # Filter tickets based on date range
    tickets = Ticket.objects.all()
    if start_date and end_date:
        tickets = tickets.filter(creation_time__range=[start_date, end_date])
    
    # Create a dictionary to store ticket counts for each agent
    agent_report = {}
    for ticket in tickets:
        agent = ticket.assigned_to.username if ticket.assigned_to else "Unassigned"
        if agent not in agent_report:
            agent_report[agent] = {"open": 0, "closed": 0, "pending": 0}
        
        # Count ticket statuses
        if ticket.status == "open":
            agent_report[agent]["open"] += 1
        elif ticket.status == "closed":
            agent_report[agent]["closed"] += 1
        elif ticket.status == "pending":
            agent_report[agent]["pending"] += 1

    # Create HTTP response with PDF content
    response = HttpResponse(content_type='application/pdf')
    filename = f"Ticket_Assignment_Report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Create PDF canvas
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    
    # Add logo (Assuming logo is stored in static files)
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'fanan_logo.jpg')
    # logo_path = "static/images/fanan_logo.jpg"  # Adjust path as needed
    p.drawImage(logo_path, 40, height - 80, width=100, height=50)
    
    # Add Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(150, height - 60, "Ticket Assignment Report")
    p.setFont("Helvetica", 10)
    p.drawString(150, height - 75, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Table Data
    data = [["Agent", "Open Tickets", "Closed Tickets", "Pending Tickets"]]
    for agent, status_counts in agent_report.items():
        data.append([agent, status_counts["open"], status_counts["closed"], status_counts["pending"]])
    
    # Create Table
    table = Table(data, colWidths=[150, 100, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    # Draw Table
    table.wrapOn(p, width, height)
    table.drawOn(p, 40, height - 200)
    
    # Save PDF
    p.showPage()
    p.save()
    return response



def generate_agent_performance_report(request):
    # Get filter values
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # Get all tickets within the date range
    tickets = Ticket.objects.all()
    if start_date and end_date:
        tickets = tickets.filter(creation_time__range=[start_date, end_date])        
    # Group tickets per agent
    agent_stats = {}
    
    for ticket in tickets:
        agent_id = ticket.assigned_to_id if ticket.assigned_to else 'Unassigned'
        if agent_id not in agent_stats:
            agent_stats[agent_id] = {
                "assigned": 0,
                "resolved": 0,
                "total_resolution_time": 0
            }
        
        # Count all assigned tickets
        agent_stats[agent_id]["assigned"] += 1  

        # Count only resolved or closed tickets
        if ticket.status.name in ["Closed", "Resolved"]:  
            agent_stats[agent_id]["resolved"] += 1
            resolution_time = (ticket.update_time - ticket.creation_time).total_seconds()
            agent_stats[agent_id]["total_resolution_time"] += resolution_time

    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    filename = f"Agent_Performance_Report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Add logo
    logo_path = "static/images/fanan_logo.jpg"
    p.drawImage(logo_path, 40, height - 80, width=100, height=50)

    # Title & Timestamp
    p.setFont("Helvetica-Bold", 16)
    p.drawString(150, height - 60, "Agent Performance Report")
    p.setFont("Helvetica", 10)
    p.drawString(150, height - 75, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Table Data
    data = [["Agent", "Tickets Assigned", "Tickets Resolved", "Avg Resolution Time (hrs)"]]

    for agent_id, stats in agent_stats.items():
        agent = User.objects.filter(id=agent_id).first() if agent_id != "Unassigned" else "Unassigned"
        avg_resolution_time = (
            stats["total_resolution_time"] / stats["resolved"] / 3600 if stats["resolved"] > 0 else 0
        )  # Convert to hours
        if agent != "Unassigned":
            data.append([agent.username, stats["assigned"], stats["resolved"], round(avg_resolution_time, 2)])
        else:
            continue
    # Create table
    table = Table(data, colWidths=[150, 150, 150, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    # Draw table
    table.wrapOn(p, width, height)
    table.drawOn(p, 40, height - 200)

    # Save PDF
    p.showPage()
    p.save()
    return response



def generate_ticket_status_report(request):
    # Get the filter values from the request
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    
    # Filter tickets based on date range
    tickets = Ticket.objects.all()
    if start_date and end_date:
        tickets = tickets.filter(creation_time__range=[start_date, end_date])
    
    # Count tickets by status
    status_report = {"open": 0, "closed": 0, "pending": 0}
    for ticket in tickets:
        if ticket.status == "Submitted":
            status_report["open"] += 1
        elif ticket.status.name == "Closed":
            status_report["closed"] += 1
        elif ticket.status == "In Progress":
            status_report["pending"] += 1
    
    # Create HTTP response with PDF content
    response = HttpResponse(content_type='application/pdf')
    filename = f"Ticket_Status_Report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Create the PDF canvas
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    
    # Add the logo (adjust the path to your logo image)
    logo_path = "static/images/fanan_logo.jpg"
    p.drawImage(logo_path, 40, height - 80, width=100, height=50)
    
    # Title and timestamp
    p.setFont("Helvetica-Bold", 16)
    p.drawString(150, height - 60, "Ticket Status Overview Report")
    p.setFont("Helvetica", 10)
    p.drawString(150, height - 75, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Table Data
    data = [["Status", "Ticket Count"]]
    for status, count in status_report.items():
        data.append([status.capitalize(), count])
    
    # Create the Table
    table = Table(data, colWidths=[150, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    # Draw the table on the PDF
    table.wrapOn(p, width, height)
    table.drawOn(p, 40, height - 200)
    
    # Save PDF
    p.showPage()
    p.save()
    return response

