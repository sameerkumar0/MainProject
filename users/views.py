from rest_framework import generics, status, permissions,response
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model, logout as auth_logout
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from django.db import models
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
from tasks.permissions import IsManager,IsEmployee
from rest_framework.permissions import AllowAny
from tasks.serializers import TaskTitleSerializer, TaskSerializer
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


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
            send_email_notification(user.email, email_subject, email_body)

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
            "redirect_url": request.build_absolute_uri(reverse("manager_dasboard"))
        }, status=status.HTTP_200_OK)


def manager_login_page(request):
    return render(request, "manager_login.html")


class LogoutView(APIView):
    """
    Logout view that blacklists the refresh token and clears session data.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # Get the refresh token from the request data
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                # Blacklist the refresh token
                token = RefreshToken(refresh_token)
                token.blacklist()

            # Logout the user from the session
            auth_logout(request)

            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def logout_view(request):
    """
    Render the logout confirmation page.
    """
    return render(request, 'logout.html')



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



class EmployeeDashboardView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployee]
    def get_queryset(self):
        return Task.objects.select_related('assigned_by').filter(
            assigned_to=self.request.user
        ).annotate(
            assignment_date=models.F('created_at'),
            submission_date=models.F('due_date')
        ).order_by('due_date')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        total_tasks = queryset.count()
        completed_tasks = queryset.filter(status='completed').count()
        in_progress_tasks = queryset.filter(status='in_progress').count()
        pending_tasks = queryset.filter(status='pending').count()

        return Response({
            'tasks': serializer.data,
            'task_stats': {
                'total': total_tasks,
                'completed': completed_tasks,
                'in_progress': in_progress_tasks,
                'pending': pending_tasks
            }
        })


@login_required
def employee_dashboard(request):
    return render(request,'employee_dashboard.html')

# manager Dashboard
class ManagerDashboardView(generics.GenericAPIView):
    """
    API for managers to view their employees and assignable tasks.
    """
    permission_classes = [permissions.IsAuthenticated, IsManager]

    def get(self, request, *args, **kwargs):
        manager = request.user
        employees = User.objects.filter(role="Employee")
        employees_with_tasks = []

        for employee in employees:
            employee_tasks = Task.objects.filter(assigned_to=employee, assigned_by=manager)
            employee_data = EmployeeSerializer(employee).data
            # Only get task titles instead of full task data
            task_titles = [task.title for task in employee_tasks]

            # Add tasks to employee data
            employee_data["assigned_tasks"] = task_titles
            employee_data["task_count"] = employee_tasks.count()
            if not employee_data.get("tech_stack"):
                employee_data["tech_stack"] = "No tech stack specified"

            employees_with_tasks.append(employee_data)

        # Unassigned tasks by this manager
        available_tasks = Task.objects.filter(assigned_to__isnull=True, assigned_by=manager)
        available_tasks_data = TaskTitleSerializer(available_tasks, many=True).data

        # Manager profile info
        manager_data = {
            "first_name": manager.first_name,
            "last_name": manager.last_name,
            "profile_photo": manager.profile_photo.url if manager.profile_photo else None
        }

        return response.Response({
            "manager": manager_data,
            "employees": employees_with_tasks,
            "available_tasks": available_tasks_data
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


class EmployeeProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated,IsManager]

    def get(self, request):
        user = request.user

        # Check if the user is an employee (optional filter)
        if user.role != 'EMPLOYEE':
            return Response({"detail": "You are not authorized to view this profile."}, status=403)

        serializer = EmployeeSerializer(user)
        return Response(serializer.data) 

def employee_profile(request):
    return render(request,'employee_profile.html')