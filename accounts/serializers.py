from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import Profile
from accounts.validators import validate_phone_format


class ProfileSerializer(serializers.ModelSerializer):
    """Наружу отдаём camelCase-поля строго по контракту фронтенда
    (fullName/avatar/phone/email), а email на самом деле лежит на auth.User,
    не на Profile — читаем/пишем его через dotted source."""

    fullName = serializers.CharField(source='full_name', required=False, allow_blank=True)
    email = serializers.EmailField(source='user.email', required=False)
    phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True, validators=[validate_phone_format],
    )
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['fullName', 'email', 'phone', 'avatar']

    def validate_email(self, value):
        # ТЗ требует уникальности email на сайте
        query = User.objects.filter(email__iexact=value)
        if self.instance:
            query = query.exclude(pk=self.instance.user_id)
        if query.exists():
            raise serializers.ValidationError('Этот email уже используется другим пользователем')
        return value

    def validate_phone(self, value):
        # ТЗ требует уникальности телефона на сайте; пустое значение не
        # считаем занятым - поле необязательное
        if not value:
            return value
        query = Profile.objects.filter(phone=value)
        if self.instance:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError('Этот телефон уже используется другим пользователем')
        return value

    def get_avatar(self, obj):
        # Раньше отдавали голую строку — фронтенд (profile.html) рендерит
        # `<img :src="avatar.src">`, ждёт объект {src, alt}, как и в остальных
        # местах проекта (ProductImageSerializer и т.п.), и как уже отдаёт
        # ProfileAvatarView.post(). Несовпадение и было причиной того, что
        # аватар не отображался после загрузки.
        if not obj.avatar:
            return None
        return {'src': obj.avatar.url, 'alt': obj.full_name or ''}

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        if user_data and 'email' in user_data:
            instance.user.email = user_data['email']
            instance.user.save(update_fields=['email'])
        return super().update(instance, validated_data)
