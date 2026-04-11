"""
Accounts views — Auth endpoints and user management.
"""

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.models import User, WorkspaceMembership
from accounts.serializers import (
    AddMemberSerializer,
    LoginSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    RegisterSerializer,
    UserSerializer,
    WorkspaceMembershipSerializer,
)
from accounts.services import AuthService, OTPService, WorkspaceService
from core.permissions import IsWorkspaceAdmin


class RegisterView(APIView):
    """
    POST /api/v1/auth/register/

    Register a new user account. Returns JWT tokens.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, tokens = AuthService.register_user(**serializer.validated_data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/v1/auth/login/

    Authenticate with email + password. Returns JWT tokens.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, tokens = AuthService.login_user(**serializer.validated_data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": tokens,
            }
        )


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/v1/auth/me/

    Retrieve or update the authenticated user's profile.
    """

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class OTPRequestView(APIView):
    """
    POST /api/v1/auth/otp/request/

    Request an OTP for customer portal login.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            code = OTPService.request_otp(**serializer.validated_data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # In production, send via email/SMS — never return code in response
        response_data = {"detail": "OTP sent successfully."}

        # In development, include the code for testing
        from django.conf import settings
        if settings.DEBUG:
            response_data["code"] = code

        return Response(response_data)


class OTPVerifyView(APIView):
    """
    POST /api/v1/auth/otp/verify/

    Verify an OTP and return session tokens.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, tokens = OTPService.verify_otp(**serializer.validated_data)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": tokens,
            }
        )


class WorkspaceMembersView(generics.ListAPIView):
    """
    GET /api/v1/auth/members/

    List all members of the current workspace.
    """

    serializer_class = WorkspaceMembershipSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def get_queryset(self):
        return (
            WorkspaceMembership.objects.filter(workspace=self.request.workspace)
            .select_related("user", "workspace")
            .order_by("-created_at")
        )


class AddMemberView(APIView):
    """
    POST /api/v1/auth/members/add/

    Add a user to the current workspace.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def post(self, request):
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        role = serializer.validated_data["role"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": f"No user found with email '{email}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        membership = WorkspaceService.add_member(request.workspace, user, role)
        return Response(
            WorkspaceMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )
