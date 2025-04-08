from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import CustomUser, UserRoles

from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser
class EmployeeSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "username", "email", "password", "phone_number", "tech_stack"]

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])  # Hash password
        validated_data["role"] = UserRoles.EMPLOYEE  # Set role explicitly
        user = CustomUser.objects.create(**validated_data)
        return user



# manager
class ManagerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "username", "email", "password", "phone_number"]

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])  # Hash password
        validated_data["role"] = UserRoles.MANAGER  # Set role explicitly
        user = CustomUser.objects.create(**validated_data)
        return user






class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            raise serializers.ValidationError("Username and password are required.")

        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        data["user"] = user  # Attach the authenticated user to the validated data
        return data




class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

