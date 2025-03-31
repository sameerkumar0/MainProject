from django.shortcuts import render
from rest_framework import generics, permissions
from .models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from .permissions import IsEmployee
from rest_framework import status, views
from rest_framework_simplejwt.tokens import RefreshToken
from .permissions import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth import authenticate
from django.http import HttpResponseForbidden
from rest_framework.permissions import IsAuthenticated

from rest_framework.decorators import api_view, permission_classes
# Create your views here.



from .serializers import EmployeeRegisterSerializer, ManagerRegisterSerializer

class EmployeeRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = EmployeeRegisterSerializer
    permission_classes = [permissions.AllowAny]

class ManagerRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = ManagerRegisterSerializer
    permission_classes = [permissions.AllowAny]

# Employee profile view 
class EmployeeProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmployee]

    def get(self, request):
        serializer = EmployeeRegisterSerializer(request.user)
        return Response(serializer.data)


class ManagerProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsManager]

    def get(self, request):
        serializer = ManagerRegisterSerializer(request.user)
        return Response(serializer.data)

def manager_login_page(request):
    return render(request, "manager_login.html")

def employee_login_page(request):
    return render(request, "employee_login.html")



from django.contrib.auth import authenticate, login
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import authenticate
from rest_framework import status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

class LoginView(views.APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)  # Generate JWT tokens

            # Check user role
            if user.groups.filter(name="Manager").exists():
                redirect_url = "/manager-dashboard"
            else:
                redirect_url = "/employee-dashboard"

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "username": user.username,
                "email": user.email,
                "redirect_url": redirect_url
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)




@login_required
def manager_dashboard(request):
    if not request.user.groups.filter(name="Manager").exists():
        return HttpResponseForbidden("You are not authorized")  

    return render(request, "manager_dashboard.html", {"user": request.user})


@api_view(["GET"])
@permission_classes([IsAuthenticated])  
def employee_dashboard(request):
    if request.user.groups.filter(name="Employee").exists():
        return render(request, "employee_dashboard.html", {"user": request.user}) 

    return HttpResponseForbidden("You are not authorized to access this page")