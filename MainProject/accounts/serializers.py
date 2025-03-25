from rest_framework import serializers
from .models import User, Department, Technology

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields ='__all__'

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )
    technologies = serializers.PrimaryKeyRelatedField(
        queryset=Technology.objects.all(), many=True, required=False
    )
    experience = serializers.IntegerField(required=False, min_value=0, default=0)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'role', 'department', 'technologies', 'experience']

    def create(self, validated_data):
        try:
            technologies = validated_data.pop('technologies', [])
            department = validated_data.pop('department', None)
            experience = validated_data.pop('experience', 0)

            # Create user
            user = User.objects.create_user(**validated_data)

            # Assign department if provided
            if department:
                user.department = department

            # Assign technologies if provided
            if technologies:
                user.technologies.set(technologies)

            # Assign experience
            user.experience = experience
            user.save()

            return user

        except Exception as e:
            raise serializers.ValidationError(f"Error creating user: {str(e)}")
            

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)