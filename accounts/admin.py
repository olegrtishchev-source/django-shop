from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from accounts.models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone')
    search_fields = ('full_name', 'phone', 'user__username')


class UserAdmin(DjangoUserAdmin):
    """Мягкое удаление пользователей - ТЗ требует его наравне с товарами,
    заказами и категориями. Своего поля is_deleted у auth.User нет, и
    добавлять миграцию в чужое приложение (django.contrib.auth) не стоит -
    поэтому используем уже существующий is_active: удаление из списка
    деактивирует пользователя (не может войти), а не стирает его из базы,
    заодно не рвёт его заказы и отзывы."""

    actions = ['restore']

    def delete_model(self, request, obj):
        obj.is_active = False
        obj.save(update_fields=['is_active'])

    def delete_queryset(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description='Восстановить (сделать активным)')
    def restore(self, request, queryset):
        queryset.update(is_active=True)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
