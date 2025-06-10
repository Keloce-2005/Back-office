from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Interface d’administration Django
    path('admin/', admin.site.urls),

    # Ton dashboard personnalisé (statistiques, utilisateurs, etc.)
    path('dashboard/', include('dashboard.urls')),

    # API REST pour React ou mobile (ex: /dashboard/api/annonces/)
    path('dashboard/api/', include('dashboard.api.urls')),

    # Redirection de la racine vers le dashboard
    path('', RedirectView.as_view(url='/dashboard/', permanent=True)),

     path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
]

# Pour servir les fichiers media (photos de profil, pièces PDF, etc.)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
