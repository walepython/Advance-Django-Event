
from django.utils import timezone
from datetime import datetime
from django.shortcuts import get_object_or_404, redirect
from rest_framework import generics,permissions, status
from .models import Event,User,Registration,Attendance,Feedback,Certificate,MediaGallery,EventSeating,EventWaitlist,CalendarSync,EventShareLog,Venue,ContactMessage
from .serializers import CustomTokenObtainPairSerializer, EventSerializer,EventCreateUpdateSerializer, RegisterSerializer, RegistrationSerializer, UserListSerializer,UserPublicSerializer,AttendanceSerializer,FeedbackSerializer,CertificateSerializer,MediaGallerySerializer,EventSeatingSerializer,EventWaitlistSerializer,CalendarSyncSerializer,EventShareLogSerializer,RegistrationScanSerializer,AdminRegistrationSerializer,VenueListSerializer,ContactMessageSerializer, ContactMessageAdminSerializer

from django.http import HttpResponse, JsonResponse
import csv
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from rest_framework.permissions import IsAuthenticated, IsAdminUser,AllowAny

from .permissions import IsOrganizerOrAdmin
from django.contrib.auth import get_user_model
import json
import os
from rest_framework import status
import traceback
import qrcode
import qrcode.image.svg
from django.core.files.base import ContentFile
from io import BytesIO
import logging
from django.db import connection

# class IsOrganizerOrReadOnly(permissions.BasePermission):

#     def has_permission(self, request, view):
#         if request.method in permissions.SAFE_METHODS:
#             return True
#         return request.user.is_authenticated and request.user.role in ['organizer', 'admin']

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
class FeedBack(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        event_id = request.data.get("event")
        rating = request.data.get("rating")
        comments = request.data.get("comments")

        if not event_id or not rating:
            return Response(
                {"error": "Event and rating are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        event = get_object_or_404(Event, id=event_id)

        # ❌ Prevent duplicate feedback per student per event
        if Feedback.objects.filter(event=event, student=request.user).exists():
            return Response(
                {"error": "You have already submitted feedback for this event"},
                status=status.HTTP_400_BAD_REQUEST
            )

        feedback = Feedback.objects.create(
            event=event,
            student=request.user,
            rating=rating,
            comments=comments
        )

        serializer = FeedbackSerializer(feedback)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EventFeedbackListAPIView(generics.ListAPIView):
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        event_id = self.kwargs["event_id"]
        return Feedback.objects.filter(event_id=event_id)

class EventListCreateAPIView2(generics.ListCreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = EventSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    

   # Event views
class EventListCreateAPIView(generics.ListCreateAPIView):
    queryset = Event.objects.all().order_by('date')
    serializer_class = EventSerializer
    # permission_classes = [IsOrganizerOrReadOnly]
    permission_classes = [permissions.AllowAny]

    def list(self, request, *args, **kwargs):
        now = timezone.localtime()
        today = now.date()
        current_time = now.time()
        
        # Get only PUBLISHED events for public categorization
        # Pending events should not appear in public lists
        published_events = Event.objects.filter(status='published')
        
        ongoing = published_events.filter(
        date=today,
        start_time__lte=current_time,
        end_time__gte=current_time
        )

        upcoming = published_events.filter(
            date__gt=today
        )

        past = published_events.filter(
            date__lt=today
        )
            
        # Get pending events (for admin dashboard)
        pending_events = Event.objects.filter(status='pending').order_by('-created_at')
        
        # Build response with all categories including pending
        return Response({
            "ongoing": EventSerializer(ongoing, many=True, context={'request': request}).data,
            "upcoming": EventSerializer(upcoming, many=True, context={'request': request}).data,
            "past": EventSerializer(past, many=True, context={'request': request}).data,
            "pending": EventSerializer(pending_events, many=True, context={'request': request}).data,
        })

    def create(self, request, *args, **kwargs):
        """
        Override create to handle organizer field properly
        """
        try:
            # Get mutable copy of request data
            data = request.data.copy()
            
            # Get organizer from request data or use current user
            organizer_id = data.get('organizer')
            if not organizer_id:
                if request.user.is_authenticated:
                    organizer_id = request.user.id
                else:
                    return Response(
                        {'error': 'Authentication required'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            
            # Get the organizer User object (User is already imported at top of file)
            try:
                organizer = User.objects.get(id=organizer_id)
            except User.DoesNotExist:
                return Response(
                    {'error': 'Organizer not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get venue if provided (Venue is already imported at top of file)
            venue = None
            if data.get('venue'):
                try:
                    venue = Venue.objects.get(id=data.get('venue'))
                except Venue.DoesNotExist:
                    return Response(
                        {'error': 'Venue not found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Convert numeric fields from strings to proper types
            max_participants = None
            if data.get('max_participants'):
                try:
                    max_participants = int(data.get('max_participants'))
                except (ValueError, TypeError):
                    max_participants = None
            
            gate_fees = None
            if data.get('gate_fees'):
                try:
                    gate_fees = float(data.get('gate_fees'))
                except (ValueError, TypeError):
                    gate_fees = None
            
            gate_fees2 = None
            if data.get('gate_fees2'):
                try:
                    gate_fees2 = float(data.get('gate_fees2'))
                except (ValueError, TypeError):
                    gate_fees2 = None
            
            # Create the event directly using the model
            event = Event.objects.create(
                title=data.get('title'),
                description=data.get('description'),
                category=data.get('category', ''),
                date=data.get('date'),
                start_time=data.get('start_time'),
                end_time=data.get('end_time'),
                status=data.get('status', 'pending'),
                organizer=organizer,  # Use the User object, not the ID
                venue=venue,  # Use the Venue object or None
                max_participants=max_participants,  # Converted to int
                gate_fees=gate_fees,  # Converted to float
                gate_fees2=gate_fees2,  # Converted to float
            )
            
            # Handle image upload if present
            if 'image' in request.FILES:
                event.image = request.FILES['image']
                event.save()
            
            # Return the created event using EventSerializer
            response_serializer = EventSerializer(event, context={'request': request})
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            # Log the error
            print("===== ERROR CREATING EVENT =====")
            print(f"Error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            print("================================")
            
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    

class EventDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
      queryset = Event.objects.prefetch_related("media").all()
      serializer_class = EventSerializer
    #   permission_classes = [IsOrganizerOrReadOnly]
      permission_classes = [permissions.AllowAny]
      lookup_field = 'id'
      def get_serializer_context(self):
        return {'request': self.request}

      def update(self, request, *args, **kwargs):
        """
        Override update to handle event editing with proper type conversion
        """
        try:
            # Get the event instance
            instance = self.get_object()
            
            # Check if user has permission to edit
            if request.user != instance.organizer and request.user.role != 'admin':
                return Response(
                    {'error': 'You can only edit your own events'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get mutable copy of request data
            data = request.data.copy()
            
            # Update basic fields
            if data.get('title'):
                instance.title = data.get('title')
            
            if data.get('description'):
                instance.description = data.get('description')
            
            if data.get('category') is not None:
                instance.category = data.get('category', '')
            
            if data.get('date'):
                instance.date = data.get('date')
            
            if data.get('start_time'):
                instance.start_time = data.get('start_time')
            
            if data.get('end_time'):
                instance.end_time = data.get('end_time')

            if 'status' in data:
               instance.status = data.get('status')
            
            # Update venue if provided
            if 'venue' in data:
                if data.get('venue'):
                    try:
                        venue = Venue.objects.get(id=data.get('venue'))
                        instance.venue = venue
                    except Venue.DoesNotExist:
                        return Response(
                            {'error': 'Venue not found'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    instance.venue = None
            
            # Convert and update numeric fields
            if 'max_participants' in data:
                if data.get('max_participants'):
                    try:
                        instance.max_participants = int(data.get('max_participants'))
                    except (ValueError, TypeError):
                        instance.max_participants = None
                else:
                    instance.max_participants = None
            
            if 'gate_fees' in data:
                if data.get('gate_fees'):
                    try:
                        instance.gate_fees = float(data.get('gate_fees'))
                    except (ValueError, TypeError):
                        instance.gate_fees = None
                else:
                    instance.gate_fees = None
            
            if 'gate_fees2' in data:
                if data.get('gate_fees2'):
                    try:
                        instance.gate_fees2 = float(data.get('gate_fees2'))
                    except (ValueError, TypeError):
                        instance.gate_fees2 = None
                else:
                    instance.gate_fees2 = None
            
            # Handle image upload if present
            if 'image' in request.FILES:
                instance.image = request.FILES['image']
            
            # Save the updated event
            instance.save()
            
            # Return the updated event using EventSerializer
            serializer = EventSerializer(instance, context={'request': request})
            return Response(serializer.data)
            
        except Exception as e:
            # Log the error
            print("===== ERROR UPDATING EVENT =====")
            print(f"Error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            print("================================")
            
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

      def partial_update(self, request, *args, **kwargs):
        """
        Handle PATCH requests (same as update)
        """
        return self.update(request, *args, **kwargs)


class VenueListAPIView(generics.ListAPIView):
    queryset = Venue.objects.all()
    serializer_class = VenueListSerializer
    permission_classes = [IsAuthenticated]

def generate_seat_number(event):
    count = Registration.objects.filter(
        event=event,
        status="confirmed"
    ).count() + 1

    return f"A{count}"

# --- Registration API View ---

class EventRegisterAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        print("REQUEST DATA:", request.data)

        event = get_object_or_404(Event, id=id)
        ticket_type = request.data.get("ticket_type")

        if not ticket_type:
            return Response({"error": "ticket_type is required"}, status=400)

        # Prevent duplicate registrations
        if Registration.objects.filter(event=event, student=request.user).exists():
            return Response({"error": "You already registered for this event."}, status=400)

        # Pricing
        price = event.gate_fees2 if ticket_type == "vip" else event.gate_fees

        # Seats check
        if event.seats_available is not None and event.seats_available <= 0:
            return Response({"error": "This event is fully booked!"}, status=400)
  
        

        # Only assign seat if event has limited capacity
        # if event.max_participants or (event.venue and event.venue.capacity):
        seat_number = generate_seat_number(event)
        # Create registration
        registration = Registration.objects.create(
            event=event,
            student=request.user,
            ticket_type=ticket_type,
            price=price,
            status='confirmed',
            seat_number=seat_number
        )


       # Generate QR Code
        qr_data = str(registration.public_id)
        qr = qrcode.make(qr_data)

        buffer = BytesIO()
        qr.save(buffer, format="PNG")

        qr_filename = f"qr_{registration.registration_id}.png"
        registration.qr_code.save(qr_filename, ContentFile(buffer.getvalue()))
        registration.save()


        return Response({
            "success": "Seat booked successfully!",
            "registration_id":registration.registration_id,
            "seat_number": registration.seat_number, 
            "qr_code_url": request.build_absolute_uri(registration.qr_code.url)
        }, status=201)


class EventRegistrationStatusAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id):
        event = get_object_or_404(Event, id=id)

        # Check if user is already registered
        registration = Registration.objects.filter(event=event, student=request.user).first()

        if registration:
            return Response({
                "registered": True,
                "qr_code_url": request.build_absolute_uri(registration.qr_code.url),
                "ticket_type": registration.ticket_type,
                "registration_id": registration.registration_id
            })

        return Response({"registered": False})

    
class DashboardRegistrationsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        registrations = Registration.objects.filter(student=request.user)
        serializer = RegistrationSerializer(registrations, many=True,context={'request': request})
        return Response(serializer.data)

class RegistrationListAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminRegistrationSerializer

    def get_queryset(self):
        return Registration.objects.select_related("student", "event", "event__venue")



# User profile
class UserProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserPublicSerializer(request.user)
        return Response(serializer.data)

# Certificates
class CertificateListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        certificates = Certificate.objects.filter(student=request.user)
        serializer = CertificateSerializer(certificates, many=True,context={'request': request})
        return Response(serializer.data)

       # Users views
class UserListAPIView(generics.ListAPIView):
    
    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [permissions.AllowAny]

class UsersRetrieveUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes =  (permissions.AllowAny,) 
    queryset = User.objects.all()
    serializer_class = UserPublicSerializer

class EventWithMediaListAPIView(generics.ListCreateAPIView):
    queryset = MediaGallery.objects.all()
    serializer_class = MediaGallerySerializer
    permission_classes = (permissions.AllowAny,)

    

class EventWithMediaDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MediaGallery.objects.all()
    serializer_class = MediaGallerySerializer
    permission_classes = (permissions.AllowAny,)
    lookup_field = "media_id"  # use event_id instead of pk

  

# Registration View
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)

# Custom Login Response (JWT)
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['username'] = self.user.username
        data['email'] = self.user.email
        return data

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = (permissions.AllowAny,)

class ScanRegistrationAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]  # staff only

    def get(self, request, public_id):
        registration = get_object_or_404(Registration, public_id=public_id)

        if registration.is_used:
            return Response(
                {
                    "status": "DENIED",
                    "message": "❌ Ticket already used",
                },
                status=400,
            )

        serializer = RegistrationScanSerializer(registration)
        return Response(
            {
                "status": "VALID",
                "message": "✅ Ticket valid",
                "data": serializer.data,
            }
        )

    def post(self, request, public_id):
        """Mark ticket as used"""
        registration = get_object_or_404(Registration, public_id=public_id)

        if registration.is_used:
            return Response(
                {
                    "status": "DENIED",
                    "message": "❌ Ticket already used",
                },
                status=400,
            )

        registration.is_used = True
        registration.save(update_fields=["is_used"])

        return Response(
            {
                "status": "CHECKED_IN",
                "message": "🎉 Entry approved",
            }
        )

class EventRegistrationsAPIView(generics.ListAPIView):
    permission_classes = [IsOrganizerOrAdmin]
    serializer_class = AdminRegistrationSerializer

    def get_queryset(self):
        event_id = self.kwargs["event_id"]
        qs = Registration.objects.filter(event_id=event_id).select_related("student", "event", "event__venue").order_by("seat_number")
        if self.request.user.role == "organizer":
            qs = qs.filter(event__organizer=self.request.user)

        return qs


@api_view(["GET"])
@permission_classes([IsOrganizerOrAdmin])
def export_event_registrations(request, event_id):
    registrations = Registration.objects.filter(event_id=event_id,event__organizer=request.user)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="registrations.csv"'

    writer = csv.writer(response)
    writer.writerow(["Public_Id","Reg_ID","Name", "Seat", "Ticket", "Checked In"])
   
    name = f"{r.student.first_name or ''} {r.student.last_name or ''}".strip()
    name = name if name else r.student.username
    for r in registrations:
        writer.writerow([
            r.public_id,
            r.registration_id,
            name,
            r.seat_number,
            r.ticket_type,
            r.is_used
            
        ])

    return response

class AdminRegistrationsAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        registrations = Registration.objects.select_related(
            "student", "event", "event__venue"
        ).all()
        serializer = AdminRegistrationSerializer(
            registrations,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)


class CheckInAPIView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizerOrAdmin]

    def post(self, request, public_id):
        """Mark a ticket as used when QR code is scanned"""
        try:
            # Find the ticket by public_id
            ticket = get_object_or_404(Registration, public_id=public_id)
            
            # Check if already checked in
            if ticket.is_used:
                return Response({
                    'status': 'error',
                    'message': 'Ticket already checked in',
                    'ticket_info': {
                        'student_name': f"{ticket.student.first_name} {ticket.student.last_name}".strip() or ticket.student.username,
                        'event_title': ticket.event.title,
                        'seat_number': ticket.seat_number or 'N/A',
                        'ticket_type': ticket.ticket_type,
                        'checked_in_at': ticket.checked_in_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.checked_in_at else None,
                        'checked_in_by':  ticket.checked_in_by.username if ticket.checked_in_by else 'System'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check in the ticket
            ticket.is_used = True
            ticket.checked_in_at = timezone.now()
            ticket.checked_in_by = request.user
            ticket.save()
            
            return Response({
                'status': 'success',
                'message': 'Ticket checked in successfully',
                'ticket_info': {
                    'student_name':f"{ticket.student.first_name} {ticket.student.last_name}".strip() or ticket.student.username,
                    'event_title': ticket.event.title,
                    'seat_number': ticket.seat_number,
                    'ticket_type': ticket.ticket_type,
                    'checked_in_at': ticket.checked_in_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'checked_in_by': request.user.username
                }
            })
            
        except Registration.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Ticket not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def cancel_registration(request, id):
    registration = get_object_or_404(
        Registration,
        event_id=id,
        student=request.user
    )

    registration.delete()

    return Response(
        {"message": "Registration cancelled successfully"},
        status=status.HTTP_200_OK
    )


logger = logging.getLogger(__name__)


class ContactMessageCreateView(APIView):
    """
    Public endpoint for submitting contact messages
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Create a new contact message
        """
        try:
            serializer = ContactMessageSerializer(data=request.data)
            
            if serializer.is_valid():
                # Get client IP address
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(',')[0]
                else:
                    ip_address = request.META.get('REMOTE_ADDR')
                
                # Get user agent
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                # Save the message
                contact_message = serializer.save(
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Log the submission
                logger.info(f"New contact message from {contact_message.email}")
                
                # TODO: Send email notification to admin
                # send_contact_notification(contact_message)
                
                # TODO: If subscribe is True, add to newsletter
                # if contact_message.subscribe:
                #     add_to_newsletter(contact_message.email)
                
                return Response({
                    'success': True,
                    'message': 'Thank you for contacting us! We will get back to you soon.',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error creating contact message: {str(e)}")
            return Response({
                'success': False,
                'message': 'An error occurred while processing your request. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContactMessageListView(generics.ListAPIView):
    """
    Admin endpoint to view all contact messages
    """
    permission_classes = [IsAdminUser]
    serializer_class = ContactMessageAdminSerializer
    queryset = ContactMessage.objects.all()
    
    def get_queryset(self):
        """
        Optionally filter by status
        """
        queryset = ContactMessage.objects.all()
        status_filter = self.request.query_params.get('status', None)
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset


class ContactMessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin endpoint to view, update, or delete a specific contact message
    """
    permission_classes = [IsAdminUser]
    serializer_class = ContactMessageAdminSerializer
    queryset = ContactMessage.objects.all()
    
    def retrieve(self, request, *args, **kwargs):
        """
        Mark message as read when admin views it
        """
        instance = self.get_object()
        instance.mark_as_read()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def mark_as_replied(request, pk):
    """
    Mark a contact message as replied
    """
    try:
        message = ContactMessage.objects.get(pk=pk)
        message.mark_as_replied(user=request.user)
        
        return Response({
            'success': True,
            'message': 'Message marked as replied'
        })
    except ContactMessage.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Message not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def contact_stats(request):
    """
    Get statistics about contact messages
    """
    total = ContactMessage.objects.count()
    new = ContactMessage.objects.filter(status='new').count()
    read = ContactMessage.objects.filter(status='read').count()
    replied = ContactMessage.objects.filter(status='replied').count()
    resolved = ContactMessage.objects.filter(status='resolved').count()
    
    # Get counts by subject
    subject_counts = {}
    for choice in ContactMessage.SUBJECT_CHOICES:
        subject_counts[choice[0]] = ContactMessage.objects.filter(subject=choice[0]).count()
    
    return Response({
        'total': total,
        'by_status': {
            'new': new,
            'read': read,
            'replied': replied,
            'resolved': resolved
        },
        'by_subject': subject_counts
    })


@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def debug_create_event(request):
    if request.method == 'POST':
        # Create a sample event
        event = Event.objects.create(
            title=request.data.get('title', 'Sample Event'),
            description=request.data.get('description', 'Test Description'),
            date=request.data.get('date', '2024-12-31'),
            # Add other fields your model requires
        )
        return Response({'message': 'Event created', 'id': event.id})
    
    # GET request - show all events
    events = Event.objects.all()
    serializer = EventSerializer(events, many=True)
    return Response(serializer.data)

@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def load_initial_data(request):
    """
    Endpoint to load initial data from fixture
    POST: Load the data
    GET: Check if data exists
    """
    if request.method == 'POST':
        try:
            # Check if events already exist
            from eventApi.models import Event
            if Event.objects.count() > 0:
                return JsonResponse({
                    'status': 'warning',
                    'message': f'Database already has {Event.objects.count()} events. No data loaded.'
                })
            
            # Load the fixture data
            call_command('loaddata', 'data.json')
            
            # Verify loading
            event_count = Event.objects.count()
            return JsonResponse({
                'status': 'success',
                'message': f'Successfully loaded data',
                'events_loaded': event_count
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    # GET request - show status
    from eventApi.models import Event
    return JsonResponse({
        'status': 'ready',
        'event_count': Event.objects.count(),
        'endpoint': 'Send POST request to load data'
    })

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def debug_admin(request):
    User = get_user_model()
    
    if request.method == 'POST':
        # Create admin if it doesn't exist
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'  # Change this!
            )
            return Response({'message': 'Admin user created'})
        return Response({'message': 'Admin already exists'})
    
    # GET: Show database info
    return Response({
        'database': connection.vendor,
        'tables_exist': User.objects.exists(),
        'admin_exists': User.objects.filter(is_superuser=True).exists(),
        'user_count': User.objects.count()
    })


from django.core.management import call_command
from io import StringIO

@api_view(['GET'])
@permission_classes([AllowAny])
def check_migrations(request):
    try:
        # Check if migrations are applied
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        return Response({
            'pending_migrations': len(plan),
            'migrations_applied': len(plan) == 0,
            'database': connection.vendor
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def run_migrations(request):
    try:
        # Capture output
        out = StringIO()
        call_command('migrate', stdout=out)
        return Response({
            'message': 'Migrations completed',
            'output': out.getvalue()
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)
    
@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """API root with available endpoints"""
    return Response({
        'message': 'Event API',
        'endpoints': {
            'events': '/api/events/',
            'admin': '/admin/',
            'load_data': '/api/load-data/',
            'debug_admin': '/api/debug-admin/',
            'check_migrations': '/api/check-migrations/',
            'run_migrations': '/api/run-migrations/'
        }
    })