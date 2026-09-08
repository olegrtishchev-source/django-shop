from rest_framework import serializers

from accounts.models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    """Наружу отдаём camelCase-поля строго по контракту фронтенда
    (fullName/avatar/phone/email), а email на самом деле лежит на auth.User,
    не на Profile — читаем/пишем его через dotted source."""

    fullName = serializers.CharField(source='full_name', required=False, allow_blank=True)
    email = serializers.EmailField(source='user.email', required=False)
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['fullName', 'email', 'phone', 'avatar']

    def get_avatar(self, obj):
        return obj.avatar.url if obj.avatar else None

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        if user_data and 'email' in user_data:
            instance.user.email = user_data['email']
            instance.user.save(update_fields=['email'])
        return super().update(instance, validated_data)
