import json

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Profile
from accounts.serializers import ProfileSerializer


def _read_json_body(request):
    """sign-in/sign-up фронтенд шлёт через JSON.stringify(...) как тело
    postData — axios в этом случае не всегда проставляет
    Content-Type: application/json, и DRF-парсер по content-type может не
    сработать. Поэтому тело разбираем сами, а на request.data полагаемся
    только как на резервный вариант."""
    try:
        return json.loads(request.body)
    except (ValueError, TypeError):
        return request.data


class SignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = _read_json_body(request)
        username = payload.get('username')
        password = payload.get('password')
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        login(request, user)
        return Response(status=status.HTTP_200_OK)


class SignUpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = _read_json_body(request)
        name = (payload.get('name') or '').strip()
        username = (payload.get('username') or '').strip()
        password = payload.get('password') or ''
        if not username or not password or User.objects.filter(username=username).exists():
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        user = User.objects.create_user(username=username, password=password)
        Profile.objects.create(user=user, full_name=name)
        login(request, user)
        return Response(status=status.HTTP_200_OK)


class SignOutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_200_OK)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return Response(ProfileSerializer(profile).data)

    def post(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ProfilePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('currentPassword')
        new_password = request.data.get('newPassword')
        if not current_password or not new_password or not request.user.check_password(current_password):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new_password)
        request.user.save()
        # иначе смена пароля разлогинит текущую сессию
        update_session_auth_hash(request, request.user)
        return Response(status=status.HTTP_200_OK)


class ProfileAvatarView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        avatar = request.FILES.get('avatar')
        if not avatar:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        profile.avatar = avatar
        profile.save(update_fields=['avatar'])
        return Response({'src': profile.avatar.url, 'alt': profile.full_name})
