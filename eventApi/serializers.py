
from datetime import datetime
from rest_framework import serializers
from .models import Event,User,Registration,Attendance,Feedback,Certificate,MediaGallery,EventSeating,EventWaitlist,CalendarSync,EventShareLog, Venue,ContactMessage

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token["username"] = user.username
        token['email'] = user.email
        token["role"] = user.role
        return token


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','username','first_name','last_name','email','role','mobile','matric_no','department']

class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']

class VenueListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ['id','name', 'address', 'capacity']


# class MediaGalleryCreateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = MediaGallery
#         # Define only the fields that the user needs to provide during upload.
#         fields = ['file', 'file_type', 'caption']

class MediaGallerySerializer(serializers.ModelSerializer):
    file = serializers.FileField(use_url=True)
    class Meta:
        model = MediaGallery
        fields = ["media_id","event", "file_type", "file", "caption", "uploaded_on"]


class EventSerializer(serializers.ModelSerializer):
    organizer = UserPublicSerializer( read_only=True)  
    venue = VenueListSerializer(read_only=True)
    seats_available = serializers.IntegerField(read_only=True) 
    is_registered = serializers.SerializerMethodField()
    media = MediaGallerySerializer(many=True, read_only=True)  # related_name="media"


    class Meta:
        model = Event
        fields =  [
            'id', 
            'title', 
            'description', 
            'date', 
            'start_time', 
            'end_time', 
            'image',
            'venue',
            'organizer',
            'seats_available',
            'gate_fees',
            'gate_fees2',
            'is_registered',
            'media'        ,
            
            ]
        
    # def get_organizer(self, obj):
    #    if obj.organizer:  
    #       return str(obj.organizer) 
    #    return None
    
    def get_is_registered(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return Registration.objects.filter(event=obj, student=user).exists()
        return False

    def get_start_datetime(self, obj):
        if obj.date and obj.start_time:
            return datetime.combine(obj.date, obj.start_time).isoformat()
        return None
    
    def get_end_datetime(self, obj):
        if obj.date and obj.end_time:
            return datetime.combine(obj.date, obj.end_time).isoformat()
        return None


class EventCreateUpdateSerializer(serializers.ModelSerializer):
    venue = serializers.PrimaryKeyRelatedField(queryset=Venue.objects.all())
    organizer = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role__in=['organizer', 'admin']))

    class Meta:
        model = Event
       
        fields = [  
            'title', 
            'description', 
            'date', 
            'start_time', 
            'end_time', 
            'image',
            'venue',
            'organizer',
            'gate_fees',
            'gate_fees2',
            ]

class RegistrationSerializer(serializers.ModelSerializer):
    event = EventSerializer(read_only=True)
    student_name = serializers.SerializerMethodField()
    student_email = serializers.CharField(source="student.email", read_only=True)

    class Meta:
        model = Registration
        fields = [
            'registration_id',
            'public_id', 
            'event',
            'student',  
            'student_name',  
            'student_email', 
            'status',
            'ticket_type',
            'price',
            'seat_number',  
            'qr_code',  
            'is_used',  
            'registered_on'
        ]
    def get_student_name(self, obj):
        # Get full name or fallback to username
        if obj.student.first_name and obj.student.last_name:
            return f"{obj.student.first_name} {obj.student.last_name}"
        return obj.student.username

class AttendanceSerializer(serializers.ModelSerializer):
    event = EventSerializer()
    class Meta:
        model = Attendance
        fields = "__all__"



class FeedbackSerializer(serializers.ModelSerializer):
    student_email = serializers.ReadOnlyField(source="student.email")
    # event_title = serializers.ReadOnlyField(source="event.title")
    event = EventSerializer(read_only=True)


    class Meta:
        model = Feedback
        fields = [
            "feedback_id",
            "event",
            
            "student",
            "student_email",
            "rating",
            "comments",
            "submitted_on",
        ]
        read_only_fields = ["student", "submitted_on"]


class CertificateSerializer(serializers.ModelSerializer):
    event = EventSerializer()
    class Meta:
        model = Certificate
        fields = "__all__"

class MediaGallerySerializer(serializers.ModelSerializer):
    file = serializers.FileField(use_url=True)
    class Meta:
        model = MediaGallery
        fields = ["media_id", "file_type", "file", "caption", "uploaded_on"]


class EventSeatingSerializer(serializers.ModelSerializer):
    event = EventSerializer()
    class Meta:
        model = EventSeating
        fields = "__all__"


class EventWaitlistSerializer(serializers.ModelSerializer):
    event = EventSerializer()
    class Meta:
        model = EventWaitlist
        fields = "__all__"


class CalendarSyncSerializer(serializers.ModelSerializer):
    event = EventSerializer()
    class Meta:
        model = CalendarSync
        fields = "__all__"


class EventShareLogSerializer(serializers.ModelSerializer):
    event = EventSerializer()
    class Meta:
        model = EventShareLog
        fields = "__all__"


from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password

# Registration Serializer
class RegisterSerializer(serializers.ModelSerializer):
    matric_no = serializers.CharField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())])
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'username',
            'password',
            'password2',
            'email',
            'first_name',
            'last_name',
            'role',
            'mobile',
            'department',
            'matric_no',
        )

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords must match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')  # remove extra field
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=validated_data.get('role', 'participant'),
            mobile=validated_data.get('mobile', ''),
            department=validated_data.get('department', ''),
            matric_no=validated_data.get('matric_no', ''),
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class RegistrationScanSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    username = serializers.CharField(source="student.username", read_only=True)
    event_title = serializers.CharField(source="event.title")
    venue = serializers.CharField(source="event.venue.name", default=None)

    class Meta:
        model = Registration
        fields = [
            "public_id",
            "registration_id",
            "username",
            "student_name",
            "event_title",
            "venue",
            "ticket_type",
            "seat_number",
            "qr_code",
            "status",
            "is_used",
        ]

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"


class AdminRegistrationSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_email = serializers.CharField(source="student.email", read_only=True)
    event_title = serializers.CharField(source="event.title")
    venue = serializers.CharField(source="event.venue.name", default=None)

    class Meta:
        model = Registration
        fields = [
            "registration_id",
            "public_id",
            "student_name",
            "event_title",
            "student_email",
            "venue",
            "ticket_type",
            "seat_number",
            "status",
            "is_used",
            "created_at",
        ]

    def get_student_name(self, obj):
        first = obj.student.first_name or ""
        last = obj.student.last_name or ""
        full_name = f"{first} {last}".strip()
        return full_name if full_name else obj.student.username


class ContactMessageSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = ContactMessage
        fields = [
            'id',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'phone',
            'subject',
            'message',
            'subscribe',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def validate_message(self, value):
        """Ensure message is at least 10 characters"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters long")
        return value

    def validate_email(self, value):
        """Basic email validation"""
        if not value or '@' not in value:
            raise serializers.ValidationError("Please enter a valid email address")
        return value.lower()


class ContactMessageAdminSerializer(serializers.ModelSerializer):
    """Admin serializer with all fields including admin notes"""
    full_name = serializers.ReadOnlyField()
    replied_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ContactMessage
        fields = '__all__'

    def get_replied_by_name(self, obj):
        if obj.replied_by:
            return obj.replied_by.username
        return None