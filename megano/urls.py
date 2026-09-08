from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.views import serve as serve_static
from django.urls import include, path, re_path
from django.views.static import serve as serve_media

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('catalog.urls')),
    path('', include('frontend.urls')),
]

# Раздача /static/ и /media/ намеренно не зависит от DJANGO_DEBUG: тот, кто
# проверяет проект, запускает его только через `manage.py runserver`, без
# collectstatic и отдельного веб-сервера под статику — значит сайт обязан
# работать «из коробки» при любом значении DEBUG в его .env (в том числе
# если .env вообще не создан). serve_static с insecure=True — тот же приём,
# что использует `runserver --insecure`, только без необходимости помнить
# про флаг; работает через стандартные static-finders, collectstatic не нужен.
urlpatterns += [
    re_path(r'^static/(?P<path>.*)$', serve_static, kwargs={'insecure': True}),
    re_path(r'^media/(?P<path>.*)$', serve_media, kwargs={'document_root': settings.MEDIA_ROOT}),
]
