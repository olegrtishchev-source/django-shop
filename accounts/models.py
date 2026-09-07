from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    """Дополнительные данные пользователя поверх стандартного auth.User."""

    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    full_name = models.CharField('ФИО', max_length=255, blank=True)
    phone = models.CharField('телефон', max_length=20, blank=True)
    avatar = models.ImageField('аватар', upload_to='avatars/', blank=True, null=True)

    class Meta:
        verbose_name = 'профиль'
        verbose_name_plural = 'профили'

    def __str__(self):
        return self.full_name or self.user.username
