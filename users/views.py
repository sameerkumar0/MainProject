from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model, logout as auth_logout
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .serializers import EmployeeSerializer, LoginSerializer, ForgotPasswordSerializer, ResetPasswordSerializer, ManagerRegisterSerializer, ManagerDashboardSerializer, EmployeeTasksSerializer
from notifications.email_services import send_email_notification
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tasks.models import Task
from.models import CustomUser,UserRoles
from tasks.permissions import IsManager,IsEmployee
from rest_framework.permissions import AllowAny
import random





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

        # Create JWT tokens
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role  # Attach role to token

        # Also log in the user for session authentication
        from django.contrib.auth import login
        login(request, user)

        # Use the hardcoded URL instead of reverse to ensure consistency
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "role": user.role,
            "redirect_url": "/dashboard/employee_dashboard/"
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

        # Create JWT tokens
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role  # Attach role to token

        # Also log in the user for session authentication
        from django.contrib.auth import login
        login(request, user)

        # Use the hardcoded URL instead of reverse to ensure consistency
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "role": user.role,
            "redirect_url": "/auth/manager/employees/"
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
        # Check if the email exists and is valid
        user = User.objects.filter(email=email).first()

        if user:
            # Check if the user is active
            if not user.is_active:
                # For security reasons, don't explicitly state the account is inactive
                return Response({'message': 'If your email is registered and active, you will receive password reset instructions.'}, status=status.HTTP_200_OK)

            # Generate a 6-digit OTP
            otp = ''.join(random.choices(string.digits, k=6))

            # Store OTP in the user model
            user.otp = otp
            user.otp_valid_until = timezone.now() + timezone.timedelta(minutes=15)  # OTP valid for 15 minutes
            user.save()

            # Create reset password link with email parameter
            reset_link = f"http://127.0.0.1:8001/auth/reset-password/?email={email}"

            # Send email with OTP and reset link
            email_subject = "Password Reset Request"
            email_body = (
                f"Hello {user.first_name},\n\n"
                f"We received a request to reset your password. Your verification code is:\n\n"
                f"OTP: {otp}\n\n"
                f"Please use this code on the password reset page to verify your identity:\n"
                f"{reset_link}\n\n"
                f"This code will expire in 15 minutes.\n\n"
                f"If you did not request a password reset, please ignore this email."
            )
            send_email_notification(user.email, email_subject, email_body)

            # Log the password reset attempt for security auditing
            print(f"Password reset requested for {email} at {timezone.now()}")

            return Response({'message': 'Password reset instructions sent to your email.'}, status=status.HTTP_200_OK)
        else:
            # For security reasons, don't reveal whether the email exists or not
            # But we can log this for internal monitoring
            print(f"Password reset attempted for non-existent email: {email} at {timezone.now()}")
            return Response({'message': 'If your email is registered, you will receive password reset instructions.'}, status=status.HTTP_200_OK)

def reset_password_page(request):
    email = request.GET.get('email')
    return render(request, 'reset-password.html', {'email': email})

def forgot_password_page(request):
    return render(request, 'forgot-password.html')

class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['password']
        confirm_password = serializer.validated_data['confirm_password']

        if new_password != confirm_password:
            return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        # Find the user by email
        user = User.objects.filter(email=email).first()

        if not user:
            # For security, don't reveal that the user doesn't exist
            return Response({'error': 'Invalid email or verification code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the user is active
        if not user.is_active:
            return Response({'error': 'This account is not active.'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify OTP
        if not user.otp or user.otp != otp:
            # Log the failed attempt for security monitoring
            print(f"Failed OTP verification for {email} at {timezone.now()}. Provided: {otp}, Expected: {user.otp}")
            return Response({'error': 'Invalid verification code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if OTP is expired
        if not user.otp_valid_until or timezone.now() > user.otp_valid_until:
            return Response({'error': 'Verification code has expired. Please request a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        # Update user password
        user.password = make_password(new_password)

        # Clear OTP fields after successful reset
        user.otp = None
        user.otp_valid_until = None
        user.save()

        # Log the successful password reset
        print(f"Password reset successful for {email} at {timezone.now()}")

        # Return success message with user role for proper redirection
        return Response({
            'message': 'Password has been reset successfully.',
            'role': user.role
        }, status=status.HTTP_200_OK)



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


@login_required
def employee_dashboard(request):
    # Get the current employee (user)
    employee = request.user

    # Check if the user is an employee
    if employee.role != UserRoles.EMPLOYEE:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You are not authorized to view this page.")

    # Get tasks assigned to the employee via TaskAssignment
    tasks = Task.objects.filter(assignments__employee=employee)

    # Calculate task statistics
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='completed').count()
    in_progress_tasks = tasks.filter(status='in_progress').count()
    pending_tasks = tasks.filter(status__in=['pending', 'assigned']).count()

    # Prepare context for the template
    context = {
        'employee': employee,
        'task_stats': {
            'total': total_tasks,
            'completed': completed_tasks,
            'in_progress': in_progress_tasks,
            'pending': pending_tasks
        }
    }

    return render(request, 'employee_dashboard.html', context)


class ManagerDashboardAPIView(generics.RetrieveAPIView):
    """
    API endpoint for retrieving manager dashboard data.
    Provides manager profile information, team statistics, and employee list with their tech stacks.
    """
    serializer_class = ManagerDashboardSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]

    def get_object(self):
        # Return the current user (manager) as the object to be serialized
        return self.request.user

@login_required
def manager_employee_dashboard(request):
    """View for the manager employee dashboard page with employee tasks."""
    # Check if the user is a manager
    if request.user.role != UserRoles.MANAGER:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You are not authorized to view this page.")

    return render(request, 'manager_employee_dashboard.html')


def employee_tasks_view(request):
    """View for displaying all employees with their assigned tasks."""
    return render(request, 'employee_tasks_view.html')


class EmployeeTasksAPIView(generics.ListAPIView):
    """API endpoint for retrieving all employees with their assigned tasks."""
    serializer_class = EmployeeTasksSerializer

    def get_queryset(self):
        # Return all employees with role=Employee
        return CustomUser.objects.filter(role=UserRoles.EMPLOYEE)