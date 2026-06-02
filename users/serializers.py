from rest_framework import serializers
from .models import CustomUser
from departments.serializers import DepartmentSerializer


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name',
                  'role', 'department', 'phone']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'role', 'department', 'phone']


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for users updating their own profile (excludes role/department)."""

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'phone']
