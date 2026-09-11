import io

from django.contrib.auth.models import User
from django.test import TestCase
from PIL import Image

from accounts.models import Profile


def _png_file(name='avatar.png'):
    """Маленькая валидная PNG-картинка в памяти — для теста загрузки аватара."""
    buf = io.BytesIO()
    Image.new('RGB', (2, 2), color='red').save(buf, format='PNG')
    buf.seek(0)
    from django.core.files.uploadedfile import SimpleUploadedFile
    return SimpleUploadedFile(name, buf.read(), content_type='image/png')


class SignUpViewTests(TestCase):
    def test_sign_up_creates_user_and_logs_in(self):
        response = self.client.post(
            '/api/sign-up',
            data='{"name": "Тест Тестов", "username": "newuser", "password": "pass12345"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertEqual(Profile.objects.get(user__username='newuser').full_name, 'Тест Тестов')
        # после регистрации пользователь должен быть залогинен
        profile_response = self.client.get('/api/profile')
        self.assertEqual(profile_response.status_code, 200)

    def test_sign_up_duplicate_username_fails(self):
        User.objects.create_user(username='existing', password='pass12345')
        response = self.client.post(
            '/api/sign-up',
            data='{"name": "Кто-то", "username": "existing", "password": "pass12345"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 500)


class SignInViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='login_user', password='pass12345')
        Profile.objects.create(user=self.user, full_name='Логин Юзер')

    def test_sign_in_success(self):
        response = self.client.post(
            '/api/sign-in',
            data='{"username": "login_user", "password": "pass12345"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/profile').status_code, 200)

    def test_sign_in_wrong_password(self):
        response = self.client.post(
            '/api/sign-in',
            data='{"username": "login_user", "password": "wrong"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 500)


class SignOutViewTests(TestCase):
    def test_sign_out_ends_session(self):
        user = User.objects.create_user(username='logout_user', password='pass12345')
        Profile.objects.create(user=user)
        self.client.force_login(user)
        self.assertEqual(self.client.get('/api/profile').status_code, 200)

        response = self.client.post('/api/sign-out')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/profile').status_code, 403)


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='profile_user', password='pass12345', email='old@example.com',
        )
        self.profile = Profile.objects.create(user=self.user, full_name='Старое Имя', phone='+70000000000')

    def test_profile_requires_auth(self):
        response = self.client.get('/api/profile')
        self.assertEqual(response.status_code, 403)

    def test_profile_get_returns_camel_case_fields(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/profile')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['fullName'], 'Старое Имя')
        self.assertEqual(data['phone'], '+70000000000')
        self.assertEqual(data['email'], 'old@example.com')
        self.assertIsNone(data['avatar'])

    def test_profile_post_updates_fields(self):
        self.client.force_login(self.user)
        response = self.client.post('/api/profile', data={
            'fullName': 'Новое Имя',
            'phone': '+79999999999',
            'email': 'new@example.com',
        })
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.profile.full_name, 'Новое Имя')
        self.assertEqual(self.profile.phone, '+79999999999')
        self.assertEqual(self.user.email, 'new@example.com')


class ProfilePasswordViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pwd_user', password='oldpass123')
        Profile.objects.create(user=self.user)
        self.client.force_login(self.user)

    def test_password_change_success_keeps_session(self):
        response = self.client.post('/api/profile/password', data={
            'currentPassword': 'oldpass123',
            'newPassword': 'newpass456',
        })
        self.assertEqual(response.status_code, 200)
        # сессия не должна слететь после смены пароля
        self.assertEqual(self.client.get('/api/profile').status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))

    def test_password_change_wrong_current_password(self):
        response = self.client.post('/api/profile/password', data={
            'currentPassword': 'notmypassword',
            'newPassword': 'newpass456',
        })
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('oldpass123'))


class ProfileAvatarViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='avatar_user', password='pass12345')
        Profile.objects.create(user=self.user)
        self.client.force_login(self.user)

    def test_avatar_upload_success(self):
        response = self.client.post('/api/profile/avatar', data={'avatar': _png_file()})
        self.assertEqual(response.status_code, 200)
        self.assertIn('src', response.json())
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(profile.avatar)

    def test_avatar_upload_without_file_fails(self):
        response = self.client.post('/api/profile/avatar', data={})
        self.assertEqual(response.status_code, 400)

    def test_profile_get_returns_avatar_as_object_after_upload(self):
        """Регрессия на замечание куратора: раньше GET /api/profile отдавал
        avatar голой строкой, а profile.html ждёт объект {src, alt}
        (`avatar.src`/`avatar.alt`) — из-за этого аватар не отображался,
        хотя загрузка на бэкенде проходила успешно."""
        self.client.post('/api/profile/avatar', data={'avatar': _png_file()})
        response = self.client.get('/api/profile')
        self.assertEqual(response.status_code, 200)
        avatar = response.json()['avatar']
        self.assertIsInstance(avatar, dict)
        self.assertIn('src', avatar)
        self.assertIn('alt', avatar)


class AccountViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='account_user', password='pass12345')
        Profile.objects.create(user=self.user, full_name='Тестовый Пользователь')

    def test_requires_authentication(self):
        response = self.client.get('/api/account/')
        self.assertEqual(response.status_code, 403)

    def test_returns_profile_data_with_no_orders(self):
        self.client.force_login(self.user)
        response = self.client.get('/api/account/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['fullName'], 'Тестовый Пользователь')
        self.assertIsNone(data['avatar'])
        self.assertEqual(data['orders'], [])

    def test_returns_only_the_most_recent_order(self):
        from orders.models import Order

        older_order = Order.objects.create(user=self.user, full_name='Тестовый Пользователь')
        newer_order = Order.objects.create(user=self.user, full_name='Тестовый Пользователь')

        self.client.force_login(self.user)
        response = self.client.get('/api/account/')
        self.assertEqual(response.status_code, 200)
        orders = response.json()['orders']
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]['id'], newer_order.id)
        self.assertNotEqual(orders[0]['id'], older_order.id)
