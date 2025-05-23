from django.db import models
from django.conf import settings
from django.db.models import Sum
from django.contrib.auth.models import User

class Profile(models.Model):
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics/', default='default_profile.png')
    
    # Basic Information
    organization = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(blank=True, null=True, max_length=100)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    
    # Professional Details
    position = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    tickets_created = models.IntegerField(default=0)
    tickets_handled = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)  # Adds the created_at field
    # # Activity & Status
    # account_status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Suspended', 'Suspended'), ('Deactivated', 'Deactivated')], default='Active')
    
    # Optional Personalization
    bio = models.TextField(blank=True, null=True)
    social_media_links = models.JSONField(default=dict, blank=True, null=True)  # Example: {"linkedin": "https://linkedin.com/in/user", "twitter": "https://twitter.com/user"}
    def get_role(self):
        """Dynamically determine role based on group membership."""
        if self.user.is_superuser:
            return "Administrator"
        elif self.user.groups.filter(name="Staff").exists():
            return "Staff"
        else:
            return "Client"
    def __str__(self):
        return f"{self.user.username} Profile"

class Project(models.Model):
    name = models.CharField(max_length=32)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def active_users(self):
        # Filter users who are assigned to tickets with status 'open' or 'in_progress'
        return User.objects.filter(
            tickets_assigned__project=self, 
            tickets_assigned__status__name__in=['open', 'in_progress']
        ).distinct()

    def user_time_map(self):
        users = self.active_users()
        timemap = {}
        for user in users:
            timemap[user] = Ticket.objects.filter(
                project=self, assigned_to=user
            ).aggregate(Sum('time_logged'))['time_logged__sum']
        return timemap


class Priority(models.Model):
    name = models.CharField(max_length=32)
    value = models.IntegerField()
    is_default = models.BooleanField(default=False)
    display_color = models.TextField(max_length=16, default="#000000")

    def __str__(self):
        return f"{self.name} ({self.value})"


class Status(models.Model):
    name = models.CharField(max_length=32)
    is_default = models.BooleanField(default=False)
    hide_by_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Ticket(models.Model):
    project = models.ForeignKey(Project, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=28)
    desc = models.TextField()
    priority = models.ForeignKey(Priority, on_delete=models.CASCADE)
    status = models.ForeignKey(Status, on_delete=models.CASCADE)  # Use ForeignKey to Status

    creation_time = models.DateTimeField()
    update_time = models.DateTimeField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, related_name='tickets_created', on_delete=models.CASCADE
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, related_name='tickets_assigned', on_delete=models.CASCADE
    )

    time_logged = models.FloatField(default=0)

    def __str__(self):
        return f"{self.name} (Project: {self.project}, Priority: {self.priority}, Assigned: {self.assigned_to})"

    class Meta:
        permissions = [
            ('can_view_status', 'Can view ticket status'),
            ('can_change_status', 'Can change ticket status'),
            ('can_assign_ticket', 'Can assign tickets'),
        ]


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    commenter = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE
    )
    text = models.TextField()

    update_time = models.DateTimeField()
    time_logged = models.FloatField(default=0)

    automated = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.time_logged < 0:
            raise ValueError("Time logged cannot be negative.")
        self.ticket.update_time = self.update_time
        self.ticket.time_logged += self.time_logged
        self.ticket.save()
        super(TicketComment, self).save(*args, **kwargs)


class TimeEntry(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    time_logged = models.FloatField()
    logged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    description = models.TextField()

    def __str__(self):
        return f"Time logged for {self.ticket.name} by {self.logged_by}"
