"""
Accounts views — Auth endpoints and user management.
"""

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

import logging
from accounts.models import User, WorkspaceMembership

logger = logging.getLogger("terratrail")
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

    @swagger_auto_schema(
        request_body=RegisterSerializer,
        responses={201: UserSerializer},
        operation_description="Register a new user account. Returns JWT tokens.",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, tokens = AuthService.register_user(**serializer.validated_data)
            logger.info(f"New user registered: {user.email}")
        except ValueError as e:
            logger.warning(
                f"Registration failed for {serializer.initial_data.get('email')}: {e}"
            )
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Account created. Please verify your email using the OTP sent to you.",
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/v1/auth/login/

    Authenticate with email + password. Returns JWT tokens.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={200: UserSerializer},
        operation_description="Authenticate with email + password. Returns JWT tokens.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, tokens = AuthService.login_user(**serializer.validated_data)
            logger.info(f"User logged in: {user.email}")
        except ValueError as e:
            logger.warning(
                f"Login attempt failed for {serializer.initial_data.get('email')}: {e}"
            )
            return Response({"message": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

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

    @swagger_auto_schema(
        request_body=OTPRequestSerializer,
        responses={200: openapi.Response("OTP sent successfully.")},
        operation_description="Request an OTP for customer portal login.",
    )
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            code = OTPService.request_otp(**serializer.validated_data)
        except ValueError as e:
            return Response(
                {"message": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # In production, send via email/SMS — never return code in response
        response_data = {"message": "OTP sent successfully."}

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

    @swagger_auto_schema(
        request_body=OTPVerifySerializer,
        responses={200: UserSerializer},
        operation_description="Verify an OTP and return session tokens.",
    )
    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user, tokens = OTPService.verify_otp(**serializer.validated_data)
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

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

    @swagger_auto_schema(
        request_body=AddMemberSerializer,
        responses={201: WorkspaceMembershipSerializer},
        operation_description="Add a user to the current workspace.",
    )
    def post(self, request):
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        role = serializer.validated_data["role"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"message": f"No user found with email '{email}'."},
                status=status.HTTP_404_NOT_FOUND,
            )

        membership = WorkspaceService.add_member(request.workspace, user, role)
        return Response(
            WorkspaceMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )
