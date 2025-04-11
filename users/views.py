from rest_framework import generics, status, permissions,response
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model, logout as auth_logout
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.db import models
from .serializers import EmployeeSerializer, LoginSerializer,ForgotPasswordSerializer,ResetPasswordSerializer,ManagerRegisterSerializer
from notifications.email_services import send_email_notification
from django.shortcuts import render
from tasks.models import Task
from.models import CustomUser,UserRoles
from tasks.permissions import IsManager,IsEmployee
from rest_framework.permissions import AllowAny
from tasks.serializers import TaskSerializer
from django.urls import reverse
from tasks.models import TaskAssignment
from django.utils import timezone
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated


User = get_user_model()
#employee Register
class EmployeeRegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            try:
                user = serializer.save()
                print(f"DEBUG: Employee created - {user.username}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(f"DEBUG: Error - {str(e)}")
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def register_emp(request):
    return render(request, 'employee_register.html')


#manager Register
class ManagerRegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = ManagerRegisterSerializer
    permission_classes = [permissions.AllowAny]  # Public access

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = serializer.save()
            print(f"DEBUG: Manager created - {user.username}")

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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


# manager Dashboard


class ManagerDashboardView(APIView):
    permission_classes = [IsAuthenticated,IsManager]

    def get(self, request):
        user = request.user

        # Ensure user is a manager
        if user.role != UserRoles.MANAGER:
            return Response({"error": "Access denied. Only managers can access this dashboard."}, status=403)

        # Manager info
        manager_data = {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "profile_photo": request.build_absolute_uri(user.profile_photo.url) if user.profile_photo else None,
            "phone_number": user.phone_number,
        }

        # Get all employees
        employees = CustomUser.objects.filter(role=UserRoles.EMPLOYEE)
        employees_data = []

        for emp in employees:
            emp_tasks = Task.objects.filter(assigned_to=emp, assigned_by=user)
            completed_tasks = emp_tasks.filter(status="completed").count()

            employees_data.append({
                "id": emp.id,
                "name": f"{emp.first_name} {emp.last_name}",
                "username": emp.username,
                "email": emp.email,
                "department": emp.department.name if emp.department else None,
                "tech_stack": [tech.strip() for tech in emp.tech_stack.split(",")] if emp.tech_stack else [],
                "profile_photo": request.build_absolute_uri(emp.profile_photo.url) if emp.profile_photo else None,
                "is_available": emp.is_available,
                "phone_number": emp.phone_number,
                "total_tasks": emp_tasks.count(),
                "completed_tasks": completed_tasks,
            })

        # Upcoming deadlines (7 days)
        today = timezone.now()
        upcoming_tasks = Task.objects.filter(
            assigned_by=user,
            due_date__gte=today,
            due_date__lte=today + timezone.timedelta(days=7)
        ).order_by('due_date')

        upcoming_deadlines = [
            {
                "title": task.title,
                "due_date": task.due_date.strftime("%Y-%m-%d %H:%M"),
                "assigned_to": f"{task.assigned_to.first_name} {task.assigned_to.last_name}",
                "status": task.status,
                "priority": task.priority
            } for task in upcoming_tasks
        ]

        # Top performers (by completed tasks)
        top_performers_query = CustomUser.objects.filter(
            role=UserRoles.EMPLOYEE,
            tasks__assigned_by=user,
            tasks__status="completed"
        ).annotate(completed=Count('tasks')).order_by('-completed')[:5]

        top_performers = [
            {
                "id": emp.id,
                "name": f"{emp.first_name} {emp.last_name}",
                "completed_tasks": emp.completed,
                "profile_photo": request.build_absolute_uri(emp.profile_photo.url) if emp.profile_photo else None,
            }
            for emp in top_performers_query
        ]

        # assignment history
        assignments = TaskAssignment.objects.filter(
            task__assigned_by=user
        ).select_related('employee', 'task').order_by('-assigned_at')[:10]

        assignment_history = [
            {
                "task": assign.task.title,
                "employee": f"{assign.employee.first_name} {assign.employee.last_name}",
                "assigned_at": assign.assigned_at.strftime("%Y-%m-%d %H:%M"),
                "status": assign.task.status
            }
            for assign in assignments
        ]

        return Response({
            "manager": manager_data,
            "employees": employees_data,
            "upcoming_deadlines": upcoming_deadlines,
            "top_performers": top_performers,
            "assignment_history": assignment_history
        })



def dashboard_Page(request):
    return render(request,'manager_dashboard.html')

#csrf handling
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
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk=None):
        # If pk is provided, get that specific employee's profile
        if pk:
            try:
                employee = CustomUser.objects.get(pk=pk, role=UserRoles.EMPLOYEE)
                serializer = EmployeeSerializer(employee)
                return Response(serializer.data)
            except CustomUser.DoesNotExist:
                return Response({"detail": "Employee not found."}, status=404)

        # Otherwise, get the current user's profile
        user = request.user

        # Check if the user is an employee (optional filter)
        if user.role != UserRoles.EMPLOYEE:
            return Response({"detail": "You are not authorized to view this profile."}, status=403)

        serializer = EmployeeSerializer(user)
        return Response(serializer.data)

def employee_profile(request):
    return render(request,'employee_profile.html')