
from django.urls import path
from .views import CertificateListAPIView, DashboardRegistrationsAPIView, EventDetailAPIView, EventFeedbackListAPIView, EventListCreateAPIView, EventRegisterAPIView, EventWithMediaDetailAPIView, EventWithMediaListAPIView, FeedBack,  UserListAPIView, UserProfileAPIView, UsersRetrieveUpdateDeleteView,EventListCreateAPIView2, EventRegistrationStatusAPIView,ScanRegistrationAPIView,EventRegistrationsAPIView, debug_create_event,export_event_registrations,AdminRegistrationsAPIView,CheckInAPIView,VenueListAPIView,cancel_registration, load_initial_data
from .views import (
    ContactMessageCreateView,
    ContactMessageListView,
    ContactMessageDetailView,
    mark_as_replied,
    contact_stats
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
     # --- Event Endpoints ---
    path('eventApi/', EventListCreateAPIView.as_view(), name='event-list'),
    path('eventApi2/', EventListCreateAPIView2.as_view(), name='event-list2'),

    path('eventApi/<int:id>/', EventDetailAPIView.as_view(), name="event-details"),
    path('eventApi/<int:id>/register/',EventRegisterAPIView.as_view(), name='event-register'),
    path("eventApi/<int:id>/registration/", EventRegistrationStatusAPIView.as_view(), name="event_registration_status"),

    path("feedback/", FeedBack.as_view(), name="feedback-create"),
    path("feedback/event/<int:event_id>/", EventFeedbackListAPIView.as_view()),

    
    path("eventApi/<int:id>/cancel/", cancel_registration, name="cancel_registration"),     
      # --- Auth Endpoints ---
    
    # --- user urls ---
    path('userApi/', UserListAPIView.as_view(), name='user-list'),

    path('userApi/<int:id>/', UsersRetrieveUpdateDeleteView.as_view(), name="user-details"),
    
    path('mediaApi/',EventWithMediaListAPIView.as_view(),name= 'events-with-media'),
    path('mediaApi/<int:media_id>/',EventWithMediaDetailAPIView.as_view(),name= 'medial-details'),
    
    path('dashboard/', DashboardRegistrationsAPIView.as_view(), name='dashboard'),
    path("my-registrations/", DashboardRegistrationsAPIView.as_view(), name="my-registrations"),
    path("my-certificates/", CertificateListAPIView.as_view(), name="my-certificates"),
    path("user/", UserProfileAPIView.as_view(), name="user-profile"),

   path("registration/scan/<uuid:public_id>/", ScanRegistrationAPIView.as_view(), name="scan-registration"),
   
   path("events/<int:event_id>/registrations/", EventRegistrationsAPIView.as_view()),
   path('venues/', VenueListAPIView.as_view(), name='venue-list'),

   path("events/<int:event_id>/export/",export_event_registrations,
   name="export_event_registrations"),

   path("admin/registrations/", AdminRegistrationsAPIView.as_view()),

   # In urls.py
   path("checkin/<uuid:public_id>/", CheckInAPIView.as_view(), name="checkin-ticket"),

   path('contact/', ContactMessageCreateView.as_view(), name='contact-create'),
    
    # Admin Contact Management
  path('admin/contacts/', ContactMessageListView.as_view(), name='admin-contacts-list'),
  path('admin/contacts/<int:pk>/', ContactMessageDetailView.as_view(), name='admin-contact-detail'),
  path('admin/contacts/<int:pk>/reply/', mark_as_replied, name='mark-as-replied'),
  path('admin/contacts/stats/', contact_stats, name='contact-stats'),

  path('api/debug-events/', debug_create_event),
  path('api/load-data/',load_initial_data, name='load-data'),
]
