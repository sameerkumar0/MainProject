from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer
from users.models import CustomUser, UserRoles

# API Views
class ChatRoomListCreateView(generics.ListCreateAPIView):
    """API endpoint for listing and creating chat rooms"""
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRoles.MANAGER:
            return ChatRoom.objects.filter(manager=user).order_by('-updated_at')
        else:  # Employee
            return ChatRoom.objects.filter(employee=user).order_by('-updated_at')

    def perform_create(self, serializer):
        user = self.request.user
        data = self.request.data

        print(f"Chat room creation request from user {user.id} ({user.username}) with role {user.role}")
        print(f"Request data: {data}")
        print(f"Request data type: {type(data)}")

        if user.is_manager():
            # Manager creating a chat with an employee
            employee_id = data.get('employee')
            print(f"Manager creating chat with employee ID: {employee_id}, type: {type(employee_id)}")
            print(f"Full request data: {self.request.data}")

            if not employee_id:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'employee': 'Employee ID is required'})

            try:
                # Convert to int if it's a string or any other type
                try:
                    employee_id = int(employee_id)
                except (ValueError, TypeError):
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'employee': f'Invalid employee ID format: {employee_id}'})

                print(f"Looking for employee with ID: {employee_id}")
                employee = CustomUser.objects.get(id=employee_id, role=UserRoles.EMPLOYEE)
                print(f"Found employee: {employee.id} ({employee.username})")

                # Check if a chat room already exists
                existing_room = ChatRoom.objects.filter(manager=user, employee=employee).first()
                if existing_room:
                    print(f"Chat room already exists with ID: {existing_room.id}")
                    # Return the existing room instead of creating a new one
                    serializer.instance = existing_room
                    return

                # Generate a unique name for the chat room
                room_name = f"chat_{employee.username}_{user.username}_{int(timezone.now().timestamp())}"
                print(f"Creating new chat room with name: {room_name}")

                serializer.save(manager=user, employee=employee, name=room_name)
            except CustomUser.DoesNotExist:
                from rest_framework.exceptions import ValidationError
                print(f"Employee with ID {employee_id} not found or is not an employee")
                raise ValidationError({'employee': f'Employee with ID {employee_id} not found or is not an employee'})
            except Exception as e:
                print(f"Error creating chat room: {str(e)}")
                raise
        else:  # Employee
            # Employee creating a chat with their manager
            manager_id = data.get('manager')
            print(f"Employee creating chat with manager ID: {manager_id}, type: {type(manager_id)}")
            print(f"Full request data: {self.request.data}")

            try:
                # If no manager ID is provided, try to use the employee's assigned manager
                if not manager_id and hasattr(user, 'manager') and user.manager:
                    manager = user.manager
                    print(f"Using employee's assigned manager: {manager.id} ({manager.username})")
                elif manager_id:
                    # Convert to int if it's a string or any other type
                    try:
                        manager_id = int(manager_id)
                    except (ValueError, TypeError):
                        from rest_framework.exceptions import ValidationError
                        raise ValidationError({'manager': f'Invalid manager ID format: {manager_id}'})

                    print(f"Looking for manager with ID: {manager_id}")
                    manager = CustomUser.objects.get(id=manager_id, role=UserRoles.MANAGER)
                    print(f"Found manager: {manager.id} ({manager.username})")
                else:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'manager': 'Manager ID is required or employee must have an assigned manager'})

                # Check if a chat room already exists
                existing_room = ChatRoom.objects.filter(manager=manager, employee=user).first()
                if existing_room:
                    print(f"Chat room already exists with ID: {existing_room.id}")
                    # Return the existing room instead of creating a new one
                    serializer.instance = existing_room
                    return

                # Generate a unique name for the chat room
                room_name = f"chat_{user.username}_{manager.username}_{int(timezone.now().timestamp())}"
                print(f"Creating new chat room with name: {room_name}")

                serializer.save(employee=user, manager=manager, name=room_name)
            except CustomUser.DoesNotExist:
                from rest_framework.exceptions import ValidationError
                print(f"Manager with ID {manager_id} not found or is not a manager")
                raise ValidationError({'manager': f'Manager with ID {manager_id} not found or is not a manager'})
            except Exception as e:
                print(f"Error creating chat room: {str(e)}")
                raise

class ChatRoomDetailView(generics.RetrieveAPIView):
    """API endpoint for retrieving a specific chat room"""
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == UserRoles.MANAGER:
            return ChatRoom.objects.filter(manager=user)
        else:  # Employee
            return ChatRoom.objects.filter(employee=user)

class MessageListCreateView(generics.ListCreateAPIView):
    """API endpoint for listing and creating messages in a chat room"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        room = get_object_or_404(ChatRoom, id=room_id)

        # Check if user is part of this chat room
        user = self.request.user
        if user != room.employee and user != room.manager:
            return Message.objects.none()

        # Mark messages as read when fetched
        unread_messages = room.messages.filter(is_read=False).exclude(sender=user)
        for message in unread_messages:
            message.mark_as_read()

        return room.messages.all()

    def perform_create(self, serializer):
        room_id = self.kwargs.get('room_id')
        room = get_object_or_404(ChatRoom, id=room_id)

        # Check if user is part of this chat room
        user = self.request.user
        if user != room.employee and user != room.manager:
            return Response({"error": "You are not authorized to send messages in this chat room"},
                            status=status.HTTP_403_FORBIDDEN)

        # Update the room's updated_at timestamp
        room.save()

        serializer.save(room=room, sender=user)

class MarkMessagesAsReadView(APIView):
    """API endpoint for marking all messages in a room as read"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_id):
        room = get_object_or_404(ChatRoom, id=room_id)
        user = request.user

        # Check if user is part of this chat room
        if user != room.employee and user != room.manager:
            return Response({"error": "You are not authorized to access this chat room"},
                            status=status.HTTP_403_FORBIDDEN)

        # Mark all messages from the other user as read
        if user == room.employee:
            unread_messages = room.messages.filter(is_read=False, sender=room.manager)
        else:  # user is manager
            unread_messages = room.messages.filter(is_read=False, sender=room.employee)

        count = unread_messages.count()
        unread_messages.update(is_read=True)

        return Response({"marked_read": count}, status=status.HTTP_200_OK)

# Template Views
@login_required
def chat_list(request):
    """View for displaying the list of chat rooms"""
    user = request.user
    context = {
        'is_manager': user.role == UserRoles.MANAGER
    }
    return render(request, 'chat/chat_list.html', context)

@login_required
def chat_room(request, room_id):
    """View for displaying a specific chat room"""
    room = get_object_or_404(ChatRoom, id=room_id)
    user = request.user

    # Check if user is part of this chat room
    if user != room.employee and user != room.manager:
        return HttpResponseForbidden("You are not authorized to access this chat room")

    # Determine the other participant
    other_user = room.manager if user == room.employee else room.employee

    context = {
        'room': room,
        'other_user': other_user,
        'is_manager': user.role == UserRoles.MANAGER
    }

    return render(request, 'chat/chat_room.html', context)

@login_required
def create_chat(request):
    """View for creating a new chat room"""
    user = request.user

    if user.role == UserRoles.MANAGER:
        # Get all employees for the manager to choose from
        available_users = CustomUser.objects.filter(role=UserRoles.EMPLOYEE)
    else:  # Employee
        # Get all managers for the employee to choose from
        available_users = CustomUser.objects.filter(role=UserRoles.MANAGER)
        # If employee has a manager assigned, prioritize that one
        if user.manager:
            available_users = [user.manager] + list(available_users.exclude(id=user.manager.id))

    context = {
        'available_users': available_users,
        'is_manager': user.role == UserRoles.MANAGER
    }

    return render(request, 'chat/create_chat.html', context)
