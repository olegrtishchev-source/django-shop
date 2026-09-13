from django.db import migrations

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin12345'
ADMIN_EMAIL = 'admin@megano.local'


def create_default_admin(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Group = apps.get_model('auth', 'Group')
    if User.objects.filter(username=ADMIN_USERNAME).exists():
        return
    admin = User.objects.create_user(
        username=ADMIN_USERNAME, email=ADMIN_EMAIL, password=ADMIN_PASSWORD,
    )
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    group = Group.objects.filter(name='Администратор').first()
    if group:
        admin.groups.add(group)


def delete_default_admin(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    User.objects.filter(username=ADMIN_USERNAME, email=ADMIN_EMAIL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_roles'),
    ]

    operations = [
        migrations.RunPython(create_default_admin, delete_default_admin),
    ]
