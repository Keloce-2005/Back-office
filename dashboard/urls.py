# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'  # Namespace pour éviter les conflits de noms d'URL

urlpatterns = [
    # Page d'accueil du dashboard
    path('', views.home, name='home'),
    
    # Gestion des livreurs
    path('livreurs/', views.livreurs, name='livreurs'),
    path('livreurs/<int:livreur_id>/', views.livreur_detail, name='livreur_detail'),
    
    # Gestion des commerçants
    path('commercants/', views.commercants, name='commercants'),
    path('commercants/<int:commercant_id>/', views.commercant_detail, name='commercant_detail'),
    
    # Gestion des clients
    path('clients/', views.clients, name='clients'),
    path('clients/<int:client_id>/', views.client_detail, name='client_detail'),
    
    # Gestion des prestataires
    path('prestataires/', views.prestataires, name='prestataires'),
    path('prestataires/<int:prestataire_id>/', views.prestataire_detail, name='prestataire_detail'),
    
    # Gestion des annonces
    path('annonces/', views.annonces, name='annonces'),
    path('annonces/<int:annonce_id>/', views.annonce_detail, name='annonce_detail'),
    
    # Gestion des services
    path('services/', views.services, name='services'),
    path('services/<int:service_id>/', views.service_detail, name='service_detail'),
    
    # Gestion des entrepôts
    path('entrepots/', views.entrepots, name='entrepots'),
    path('entrepots/<int:entrepot_id>/', views.entrepot_detail, name='entrepot_detail'),
    
    # Gestion des livraisons
    path('livraisons/', views.livraisons, name='livraisons'),
    path('livraisons/<int:livraison_id>/', views.livraison_detail, name='livraison_detail'),
    
    # Gestion des notifications
    path('notifications/', views.notifications, name='notifications'),
    
    # Gestion des paiements
    path('paiements/', views.paiements, name='paiements'),
    path('paiements/<int:paiement_id>/', views.paiement_detail, name='paiement_detail'),
    
    # Gestion de la facturation
    path('facturation/', views.facturation, name='facturation'),
    
    # Gestion des abonnements
    path('abonnements/', views.abonnements, name='abonnements'),
    
    # Gestion des contrats
    path('contrats/', views.contrats, name='contrats'),
    
    # Statistiques et rapports
    path('statistiques/', views.statistiques, name='statistiques'),
    
    # Paramètres du système
    path('parametres/', views.parametres, name='parametres'),
    
    # Support et aide
    path('support/', views.support, name='support'),
    
    # Logs du système
    path('logs/', views.logs, name='logs'),
]