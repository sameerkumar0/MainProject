from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User, Department, Technology
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer
from django.core.exceptions import ObjectDoesNotExist

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            data = request.data
            department_id = data.get("department")  # Get department ID from request
            technologies_ids = data.get("technologies", [])  # Get list of technology IDs
            experience = data.get("experience", 0)  # Get experience, default to 0

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            # Assign department if provided
            if department_id:
                try:
                    department = Department.objects.get(id=department_id)
                    user.department = department
                except Department.DoesNotExist:
                    return Response({"error": "Invalid department ID"}, status=status.HTTP_400_BAD_REQUEST)

            # Assign technologies if provided
            if technologies_ids:
                try:
                    technologies = Technology.objects.filter(id__in=technologies_ids)
                    user.technologies.set(technologies)  # Set multiple technologies
                except Technology.DoesNotExist:
                    return Response({"error": "Invalid technology IDs"}, status=status.HTTP_400_BAD_REQUEST)

            # Assign experience
            user.experience = int(experience)
            user.save()

            return Response(
                {"message": "User registered successfully", "user": UserSerializer(user).data},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                refresh = RefreshToken.for_user(user)
                return Response({
                    "message": "Login successful!",
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        except ObjectDoesNotExist:
            return Response({"error": "User does not exist"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": "Invalid token or already logged out"}, status=status.HTTP_400_BAD_REQUEST)

