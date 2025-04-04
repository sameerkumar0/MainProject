from rest_framework import generics,status,permissions
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import EmployeeSerializer, LoginSerializer,ForgotPasswordSerializer,ResetPasswordSerializer,ManagerRegisterSerializer
from notifications.email_services import send_email_notification
import random
import string
from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tasks.models import Task 
from.models import CustomUser,UserRoles
from tasks.permissions import IsManager
from rest_framework.permissions import AllowAny
from django.urls import reverse
from tasks.serializers import TaskSerializer


User = get_user_model()
#employee Register
class EmployeeRegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.AllowAny]  # Anyone can register

    def perform_create(self, serializer):
        try:
            user = serializer.save()
            print(f"DEBUG: Employee created - {user.username}")

            # Send a welcome email (optional)
            email_subject = "Welcome to the Team!"
            email_body = (
                f"Hello {user.first_name},\n\n"
                f"Your employee account has been created successfully!\n"
                f"Username: {user.username}\n"
                f"Email: {user.email}\n\n"
                "Please log in to your account to get started."
            )
            # send_email_notification(user.email, email_subject, email_body)  # Uncomment if you have email sending set up

        except Exception as e:
            print(f"DEBUG: Error - {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def register_emp(request):
    return render(request, 'employee_register.html')


#manager Register
class ManagerRegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = ManagerRegisterSerializer
    permission_classes = [permissions.AllowAny]  # Anyone can register

    def perform_create(self, serializer):
        try:
            user = serializer.save()
            print(f"DEBUG: Manager created - {user.username}")

            # Send a welcome email (optional)
            email_subject = "Manager Account Created"
            email_body = (
                f"Hello {user.first_name},\n\n"
                f"Your manager account has been created successfully!\n"
                f"Username: {user.username}\n"
                f"Email: {user.email}\n\n"
                "You can now manage your team and assign tasks."
            )
            send_email_notification(user.email, email_subject, email_body)  # Uncomment if you have email sending set up

        except Exception as e:
            print(f"DEBUG: Error - {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
def register_manager(request):
    return render(request, 'manager_register.html') 



class EmployeeLoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]  # Public access

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        if user.role != UserRoles.EMPLOYEE:
            return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role  # Attach role to token

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "role": user.role,
            "redirect_url": request.build_absolute_uri(reverse("employee_dashboard"))
        }, status=status.HTTP_200_OK)

def emp_login_page(request):
   return render(request, 'employee_login.html')


class ManagerLoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]  # Public access

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        if user.role != UserRoles.MANAGER:
            return Response({"error": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role  # Attach role to token

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "role": user.role,
            "redirect_url": request.build_absolute_uri(reverse("list_employees"))
        }, status=status.HTTP_200_OK)
    

def manager_login_page(request):
    return render(request, "manager_login.html")



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
        


@login_required
def employee_dashboard(request):
    user = request.user  
    # Fetch assigned tasks for the employee
    tasks = Task.objects.filter(assigned_to=user)

    context = {
        "employee": user,
        "tasks": tasks,
    }
    return render(request, "employee_dashboard.html", context)


# manager Dashboard 

class ManagerDashboardView(generics.GenericAPIView):
    """
    API for managers to view their assigned employees, tasks, and tech stacks.
    """
    permission_classes = [permissions.IsAuthenticated, IsManager]

    def get(self, request, *args, **kwargs):
        manager = request.user
        employees = User.objects.filter(role="employee")  # Get all employees under manager
        tasks = Task.objects.filter(assigned_by=manager)  # Get all tasks assigned by manager

        employee_data = EmployeeSerializer(employees, many=True).data
        task_data = TaskSerializer(tasks, many=True).data

        return Response({
            "manager": {
                "username": manager.username,
                "email": manager.email,
            },
            "employees": employee_data,
            "tasks": task_data,
        })
    
def dashboard_Page(request):
    return render(request,'manager_dashboard.html')


from django.middleware.csrf import get_token
from django.http import JsonResponse

def get_csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})

def home(request):
    return render (request,'home.html')

class EmployeeListView(generics.ListAPIView):
    """
    View to get all registered employees.
    Only Managers can access this list.
    """
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager] 

    def get_queryset(self):
        return CustomUser.objects.filter(role="Employee")
    

def list_employee(request):
    return render(request,'employee_list.html')