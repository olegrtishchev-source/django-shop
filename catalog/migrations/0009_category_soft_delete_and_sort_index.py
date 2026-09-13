from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0008_shopsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='is_deleted',
            field=models.BooleanField(default=False, verbose_name='удалена'),
        ),
        migrations.AddField(
            model_name='product',
            name='sort_index',
            field=models.PositiveIntegerField(
                default=0,
                help_text=(
                    'Чем меньше значение, тем выше товар в топе на главной странице; '
                    'при равном индексе — сортировка по количеству покупок'
                ),
                verbose_name='индекс сортировки',
            ),
        ),
    ]
