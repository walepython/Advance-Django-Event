from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from eventApi.views import serve_media
import re
from eventApi.views import MyTokenObtainPairView, RegisterView



urlpatterns = [
    path('admin/', admin.site.urls),

    # App routes
    path('api/', include('eventApi.urls')),   # all eventApi endpoints

    # Auth routes
    path('api/register/', RegisterView.as_view(), name='register'),
    # path('api-auth/', include('rest_framework.urls')), 

    path('api/token/', MyTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path('api/token/refresh/', TokenRefreshView.as_view(), name="token_refresh"),
]

if not settings.DEBUG:
    urlpatterns += [
        path('media/<path:path>', serve_media, name='serve_media')
    ]
else:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
