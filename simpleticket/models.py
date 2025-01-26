from django.db import models
from django.conf import settings
from django.db.models import Sum
from django.contrib.auth.models import AbstractUser


class Project(models.Model):
    name = models.CharField(max_length=32)
    is_default = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    def active_users(self):
        user_set = set()
        for ticket in self.ticket_set.all():
            user_set.add(ticket.assigned_to)
        return user_set

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

    def __unicode__(self):
        return self.name + " (" + str(self.value) + ")"

    def __str__(self):
        return self.__unicode__()


class Status(models.Model):
    name = models.CharField(max_length=32)
    is_default = models.BooleanField(default=False)
    hide_by_default = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name


class Ticket(models.Model):
    project = models.ForeignKey(Project, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=128)
    desc = models.TextField()
    priority = models.ForeignKey(Priority, on_delete=models.CASCADE)
    status = models.ForeignKey(Status, on_delete=models.CASCADE)

    creation_time = models.DateTimeField()
    update_time = models.DateTimeField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, related_name='tickets_created', on_delete=models.CASCADE
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, related_name='tickets_assigned', on_delete=models.CASCADE
    )

    time_logged = models.FloatField(default=0)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name


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
        self.ticket.update_time = self.update_time
        self.ticket.time_logged += self.time_logged
        self.ticket.save()
        super(TicketComment, self).save(*args, **kwargs)
