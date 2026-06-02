from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import ListAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import (UserRegistrationSerializer, UserProfileSerializer, UserUpdateSerializer)
from .permissions import IsAdmin

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            profile = UserProfileSerializer(user)
            return Response(profile.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return Response(status=status.HTTP_205_RESET_CONTENT)


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user,
                                          data=request.data,
                                          partial=True)
        if serializer.is_valid():
            serializer.save()
            # Use serializer.instance to get the refreshed object, not stale request.user
            profile = UserProfileSerializer(serializer.instance)
            return Response(profile.data)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)


class UserListView(ListAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = UserProfileSerializer

    def get_queryset(self):
        return User.objects.all().order_by('id')


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)

    def patch(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = UserProfileSerializer(user,
                                           data=request.data,
                                           partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        user = self.get_object(pk)
        if not user:
            return Response({"detail": "Not found."},
                            status=status.HTTP_404_NOT_FOUND)
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
