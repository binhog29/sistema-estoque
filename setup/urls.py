from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from estoque.views import index, gerar_relatorio_pdf # <--- Importe a nova função

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('relatorio-pdf/', gerar_relatorio_pdf, name='relatorio_pdf'), # <--- Nova rota
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
