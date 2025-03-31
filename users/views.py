from rest_framework import generics, permissions,status
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import UserSerializer, LoginSerializer,ForgotPasswordSerializer,ResetPasswordSerializer
from notifications.email_services import send_email_notification
import random
import string
from django.contrib.auth.hashers import make_password
import jwt
import datetime
from django.conf import settings
from django.shortcuts import render

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        try:
            user = serializer.save()
            email_subject = "Your Account Credentials"
            email_body = (
                f"Hello {user.first_name},\n\n"
                f"Your account has been created successfully!\n"
                f"Username: {user.username}\n"
                f"Email: {user.email}\n"
                f"Password: (password you entered during registration)\n\n"
                f"Please keep your credentials secure."
            )
            send_email_notification(user.email, email_subject, email_body)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(username=serializer.validated_data['username'], password=serializer.validated_data['password'])
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "role": user.role
            })
        return Response({"error": "Invalid credentials"}, status=400)

        return Response(serializer.validated_data) 
    



class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer  

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)

            # Generate a temporary password
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

            # Update user's password (hashed)
            user.password = make_password(temp_password)
            user.save()

            # Create reset password link
            reset_link = f"http://127.0.0.1:8000/api/users/reset-password-page/?email={email}"

            # Send email with the temporary password and reset link
            email_subject = "Password Reset Request"
            email_body = (
                f"Hello {user.first_name},\n\n"
                f"Your temporary password is: {temp_password}\n\n"
                f"Use this password to log in and reset your password here:\n"
                f"{reset_link}\n\n"
                f"Please reset your password immediately."
            )
            send_email_notification(user.email, email_subject, email_body)

            return Response({'message': 'Temporary password and reset link sent to your email.'}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'error': 'User with this email does not exist.'}, status=status.HTTP_404_NOT_FOUND)

def reset_password_page(request):
    email = request.GET.get('email')
    return render(request, 'reset-password.html', {'email': email})

class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer  

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        new_password = serializer.validated_data['password']
        confirm_password = serializer.validated_data['confirm_password']

        if new_password != confirm_password:
            return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)

            # Update user password
            user.password = make_password(new_password)
            user.save()

            return Response({'message': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tasks.models import Task  # Import Task model
from .models import CustomUser  # Import CustomUser model

# @login_required
def employee_dashboard(request):
    user = request.user  # Get the logged-in employee (CustomUser instance)
    
    # Ensure only employees can access the dashboard
    if user.role != "EMPLOYEE":
        return render(request, "error.html", {"message": "Access Denied!"})

    tasks = Task.objects.filter(assigned_to=user)  # Get assigned tasks

    context = {
        'employee': user,
        'tasks': tasks
    }
    return render(request, 'employee_dashboard.html', context)
