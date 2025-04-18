from django.urls import path
from . import views

urlpatterns = [
    # API endpoints
    path('api/rooms/', views.ChatRoomListCreateView.as_view(), name='chat-room-list'),
    path('api/rooms/<int:pk>/', views.ChatRoomDetailView.as_view(), name='chat-room-detail'),
    path('api/rooms/<int:room_id>/messages/', views.MessageListCreateView.as_view(), name='message-list'),
    path('api/rooms/<int:room_id>/mark-read/', views.MarkMessagesAsReadView.as_view(), name='mark-messages-read'),
    
    # Template views
    path('', views.chat_list, name='chat-list'),
    path('rooms/<int:room_id>/', views.chat_room, name='chat-room'),
    path('create/', views.create_chat, name='create-chat'),
]
