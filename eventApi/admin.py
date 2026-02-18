from django.contrib import admin
from .models import (
    Attendance, CalendarSync, Certificate, EventSeating, EventShareLog,
    EventWaitlist, MediaGallery, Registration, User,
    Event, Feedback, Venue,ContactMessage
)

admin.site.register(User)
admin.site.register(Venue)
admin.site.register(Event)
admin.site.register(Attendance)
admin.site.register(Feedback)
admin.site.register(Certificate)
admin.site.register(MediaGallery)
admin.site.register(EventSeating)
admin.site.register(EventWaitlist)
admin.site.register(CalendarSync)
admin.site.register(EventShareLog)

#  Custom Registration admin (ONLY ONCE)
@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
            "public_id",
            "registration_id",
            "student",
            "event",
            "ticket_type",
            "seat_number",
            "qr_code",
            "status",
            "is_used",
    )
    list_filter = ("event", "ticket_type", "is_used","seat_number")
    search_fields = ("student__username", "student__email")
    ordering = ("-created_at",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'full_name',
        'email',
        'subject',
        'status',
        'created_at',
        'replied_at'
    ]
    list_filter = ['status', 'subject', 'subscribe', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'message']
    readonly_fields = [
        'created_at',
        'updated_at',
        'ip_address',
        'user_agent',
        'replied_at'
    ]
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Message Details', {
            'fields': ('subject', 'message', 'subscribe')
        }),
        ('Status & Admin', {
            'fields': ('status', 'admin_notes', 'replied_by', 'replied_at')
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_replied', 'mark_as_resolved']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.filter(status='new').update(status='read')
        self.message_user(request, f'{updated} messages marked as read')
    mark_as_read.short_description = 'Mark selected as read'
    
    def mark_as_replied(self, request, queryset):
        from django.utils import timezone
        updated = queryset.exclude(status='replied').update(
            status='replied',
            replied_at=timezone.now(),
            replied_by=request.user
        )
        self.message_user(request, f'{updated} messages marked as replied')
    mark_as_replied.short_description = 'Mark selected as replied'
    
    def mark_as_resolved(self, request, queryset):
        updated = queryset.update(status='resolved')
        self.message_user(request, f'{updated} messages marked as resolved')
    mark_as_resolved.short_description = 'Mark selected as resolved'

