from django import forms
from django.contrib.auth.models import User
from .models import Ticket, TicketComment, Priority, Status, Project
from .models import Profile

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'profile_picture', 'organization', 'address', 'contact_number','position', 'department', 'bio', 'social_media_links',
        ]

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['name', 'desc', 'project', 'priority', 'status', 'assigned_to']
        widgets = {
            'desc': forms.Textarea(attrs={'rows': 3}),
        }

    assigned_to = forms.ChoiceField(choices=[('unassigned', 'Unassigned')] + [(user.id, user.username) for user in User.objects.all()],
                                    required=False)

    def clean_assigned_to(self):
        assigned_to = self.cleaned_data.get('assigned_to')
        if assigned_to == 'unassigned':
            return None
        return User.objects.get(id=assigned_to)


class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ['text', 'status']

    text = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), label="Comment")
    status = forms.ModelChoiceField(queryset=Status.objects.all(), required=False, label="Update Status")

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        text = cleaned_data.get('text')

        # Ensure a status change is only allowed if the user has permission
        if status and not self.instance.ticket.status != status and not self.user.has_perm('simpleticket.change_status'):
            raise forms.ValidationError("You do not have permission to change the ticket status.")
        return cleaned_data
