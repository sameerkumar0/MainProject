"""
URL configuration for MainProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users.views import home

urlpatterns = [
    # Home page
    path('', home, name='home'),

    # Admin URLs
    path('admin/', admin.site.urls),

    # API URLs
    path('api/tasks/', include('tasks.urls')),
    path('api/users/', include('users.urls')),

    # Web URLs - Template views
    path('dashboard/', include('tasks.urls_web')),  # Dashboard and task views
    path('auth/', include('users.urls_web')),  # Authentication and user management views
    path('chat/', include('chat.urls')),  # Chat system
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)