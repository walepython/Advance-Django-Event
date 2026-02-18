from django.conf import settings
from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser




class User(AbstractUser): 
    ROLE_CHOICES = [ 
        ('participant', 'Participant'), 
        ('organizer', 'Organizer'),
        ('admin', 'Admin'), 
          ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='participant') 
    mobile = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    matric_no = models.CharField(max_length=50, blank=True, null=True, unique=True) 

    def __str__(self):
        return f"{self.email} ({self.role})"

   
    
class RegistrationStatus(models.TextChoices):
     CONFIRMED = 'confirmed', 'Confirmed' 
     CANCELLED = 'cancelled', 'Cancelled' 
     WAITLIST = 'waitlist', 'Waitlist' 

class Venue(models.Model): 
    name = models.CharField(max_length=100, unique=True)
    address = models.TextField() 
    capacity = models.PositiveIntegerField(null=True, blank=True) 
    
    def __str__(self): return self.name 

class Event(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    title = models.CharField(max_length=150, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=50, db_index=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    max_participants = models.PositiveIntegerField(default=0)

    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organized_events',
        limit_choices_to={'role': 'organizer'}
    )

    image = models.ImageField(upload_to="event_images/", blank=True, null=True)
    gate_fees = models.IntegerField(null=True, blank=True, default=None)
    gate_fees2 = models.IntegerField(null=True, blank=True, default=None)

    def __str__(self):
        return f"{self.title} ({self.date})"

    @property
    def seats_booked(self):
        # status is a CharField, so use the actual string value
        return Registration.objects.filter(event=self, status="confirmed").count()

    @property
    def seats_available(self):
        if self.max_participants:
            return max(self.max_participants - self.seats_booked, 0)
        if self.venue and self.venue.capacity:
            return max(self.venue.capacity - self.seats_booked, 0)
        return None

class Registration(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('waitlist', 'Waitlist'),
    ]
    TICKET_CHOICES = [
        ('regular', 'Regular'),
        ('vip', 'VIP'),
    ]

    registration_id = models.AutoField(primary_key=True) 
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_registrations")
    registered_on = models.DateTimeField(auto_now_add=True)  
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    ticket_type = models.CharField(max_length=10, choices=TICKET_CHOICES, default='regular')
    price = models.IntegerField(null=True, blank=True)
    seat_number = models.CharField(max_length=10, null=True, blank=True)
    qr_code = models.ImageField(upload_to="qr_codes/", blank=True, null=True)
    is_used = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)  # Add this
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checkins"
    )

    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
       
    class Meta:
        unique_together = ('event', 'student','ticket_type')  

    def __str__(self):
        return f"{self.student.email} -> {self.event.title} ({self.status})"  

    def check_in(self, user):
        """Mark ticket as checked in"""
        if self.is_used:
            return False, "Already checked in"
        
        self.is_used = True
        self.checked_in_at = timezone.now()
        self.checked_in_by = user
        self.save()
        return True, "Checked in successfully"

class Attendance(models.Model): 
    attendance_id = models.AutoField(primary_key=True) 
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances') 
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_attendances')
    attended = models.BooleanField(default=False) 
    marked_on = models.DateTimeField(auto_now_add=True) 

    class Meta: unique_together = ('event', 'student')

    def __str__(self): 
        status = "Present" if self.attended else "Absent" 
        return f"{self.student.email} - {self.event.title}: {status}" 
class Feedback(models.Model):
     feedback_id = models.AutoField(primary_key=True) 
     event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="feedbacks")
     student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_feedbacks") 
     rating = models.PositiveSmallIntegerField() 
     comments = models.TextField(blank=True, null=True) 
     submitted_on = models.DateTimeField(auto_now_add=True) 

     def __str__(self):
         return f"Feedback by {self.student.email} for {self.event.title} - {self.rating}/5"
     
class Certificate(models.Model):
     certificate_id = models.AutoField(primary_key=True)
     event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="certificates")
     student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates") 
     certificate_url = models.CharField(max_length=255) 
     issued_on = models.DateTimeField(auto_now_add=True) 

     def __str__(self):
         return f"Certificate for {self.student.email} - {self.event.title}" 
     
class MediaGallery(models.Model):
     FILE_CHOICES = [
          ("image", "Image"), 
          ("video", "Video"), 
          ] 
     media_id = models.AutoField(primary_key=True)
     event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="media") 
     file_type = models.CharField(max_length=10, choices=FILE_CHOICES) 
     file = models.FileField(upload_to='gallery/', null=True, blank=True)
     uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
     caption = models.CharField(max_length=150, blank=True, null=True)
     uploaded_on = models.DateTimeField(auto_now_add=True) 

     def __str__(self):
         return f"{self.file_type} for {self.event.title}"
         
class EventSeating(models.Model):
     event = models.OneToOneField(Event, on_delete=models.CASCADE, primary_key=True)
     venue_name = models.CharField(max_length=200, blank=True, null=True)
     total_seats = models.PositiveIntegerField(default=0) 
     seats_booked = models.PositiveIntegerField(default=0)
     waitlist_enabled = models.BooleanField(default=False) 
     
     @property 
     def seats_available(self):
         return max(self.total_seats - self.seats_booked, 0) 
     
     def __str__(self): return f"Seating for {self.event.title} ({self.seats_available} available)" 
     
class EventWaitlist(models.Model): 
    STATUS_CHOICES = [
         ("waiting", "Waiting"),
         ("confirmed", "Confirmed"),
         ("cancelled", "Cancelled"),
           ] 
    waitlist_id = models.AutoField(primary_key=True) 
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) 
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="waitlist_entries") 
    waitlist_time = models.DateTimeField(auto_now_add=True) 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="waiting") 
    class Meta: 
        unique_together = ("student", "event") 
        ordering = ["waitlist_time"] 

    def __str__(self):
        return f"{self.student.email} - {self.event.title} ({self.status})"
             
class CalendarSync(models.Model): 
    sync_id = models.AutoField(primary_key=True) 
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) 
    event = models.ForeignKey(Event, on_delete=models.CASCADE) 
    calendar_type = models.CharField(max_length=50) 
    sync_timestamp = models.DateTimeField(auto_now_add=True)
    calendar_url = models.CharField(max_length=255, blank=True, null=True) 
    
    def __str__(self):
         return f"{self.user.email} synced {self.event.title} ({self.calendar_type})" 
    
class EventShareLog(models.Model): 
    share_id = models.AutoField(primary_key=True) 
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True) 
    event = models.ForeignKey(Event, on_delete=models.CASCADE) 
    platform = models.CharField(max_length=50, blank=True, null=True) 
    share_timestamp = models.DateTimeField(auto_now_add=True)
    share_message = models.TextField(blank=True, null=True) 
    
    def __str__(self): return f"{self.user.email if self.user else 'Anonymous'} shared {self.event.title}"


class ContactMessage(models.Model):
    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('support', 'Technical Support'),
        ('event', 'Event Organization'),
        ('partnership', 'Partnership'),
        ('feedback', 'Feedback'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('resolved', 'Resolved'),
    ]

    # Contact Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Message Details
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, default='general')
    message = models.TextField()
    
    # Additional Info
    subscribe = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    
    # Metadata
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Admin Notes
    admin_notes = models.TextField(blank=True, null=True)
    replied_at = models.DateTimeField(blank=True, null=True)
    replied_by = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='contact_replies'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.subject}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def mark_as_read(self):
        if self.status == 'new':
            self.status = 'read'
            self.save(update_fields=['status'])

    def mark_as_replied(self, user=None):
        self.status = 'replied'
        self.replied_at = timezone.now()
        if user:
            self.replied_by = user
        self.save(update_fields=['status', 'replied_at', 'replied_by'])
