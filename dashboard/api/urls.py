# dashboard/api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import RegisterLivreurView  # Ajouter cet import

# Configurer le routeur pour les ViewSets
router = DefaultRouter()
router.register('users', views.UserViewSet)
router.register('livraisons', views.LivraisonViewSet)
router.register('annonces', views.AnnonceViewSet)
router.register('messages', views.MessageViewSet, basename='message')    #By Oceane


# ViewSets spécifiques par type d'utilisateur
router.register('livreur/livraisons', views.LivreurLivraisonsViewSet, basename='livreur-livraisons')
router.register('client/annonces', views.ClientAnnoncesViewSet, basename='client-annonces')
router.register('commercant/contrats', views.CommercantContratsViewSet, basename='commercant-contrats')
router.register('prestataire/services', views.PrestataireServicesViewSet, basename='prestataire-services')

# Router pour les ViewSets d'administration
admin_router = DefaultRouter()
admin_router.register('users', views.AdminUserViewSet, basename='admin-users')
admin_router.register('livraisons', views.AdminLivraisonViewSet, basename='admin-livraisons')
admin_router.register('demandes-validation-livreur', views.AdminValidationLivreurViewSet, basename='admin-validation-livreur')
admin_router.register('pieces-justificatives', views.AdminPieceJustificativeViewSet, basename='admin-pieces')

app_name = 'api'

urlpatterns = [
    # Inclure les routes générées par le routeur principal
    path('', include(router.urls)),
    
    # Routes d'authentification
    path('auth/register/', views.register_user, name='register'),
    path('auth/register/livreur/', RegisterLivreurView.as_view(), name='register_livreur'),  # Nouvelle route pour l'inscription des livreurs
    path('auth/login/', views.login_user, name='login'),
    path('auth/logout/', views.logout_user, name='logout'),
    path('auth/profile/', views.user_profile, name='profile'),
    path('auth/register/livreur/', RegisterLivreurView.as_view(), name='register_livreur'),
    
    # Route de test de connexion
    path('test-connection/', views.test_connection, name='test-connection'),
    
    # Route pour les statistiques
    path('stats/monthly-revenue/', views.monthly_revenue, name='monthly-revenue'),
    
    # Routes d'administration
    path('admin/', include(admin_router.urls)),
    path('admin/dashboard-stats/', views.admin_dashboard_stats, name='admin-dashboard-stats'),
    path('admin/financial-report/monthly/<int:year>/', views.admin_monthly_financial_report, name='admin-monthly-financial-report'),
    path('admin/financial-report/yearly/', views.admin_yearly_financial_report, name='admin-yearly-financial-report'),
]