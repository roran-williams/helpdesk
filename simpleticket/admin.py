from simpleticket.models import Profile, Project, Priority, Status, Ticket, TicketComment
from django.contrib import admin

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'contact_number', 'created_at')
    search_fields = ('user__username', 'organization', 'contact_number')
    list_filter = ( 'created_at','organization')

class TicketCommentInLine(admin.TabularInline):
    model = TicketComment
    fk_name = "ticket"
    extra = 1


class ProjectAdmin(admin.ModelAdmin):
    model = Project


class PriorityAdmin(admin.ModelAdmin):
    model = Priority


class StatusAdmin(admin.ModelAdmin):
    model = Status


class TicketAdmin(admin.ModelAdmin):
    model = Ticket
    inlines = [TicketCommentInLine]


admin.site.register(Project, ProjectAdmin)
admin.site.register(Priority, PriorityAdmin)
admin.site.register(Status, StatusAdmin)
admin.site.register(Ticket, TicketAdmin)
