from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import (
    User, Livreur, Commercant, Prestataire, Annonce, Livraison, 
    Paiement, Facture, Service, Entrepot, BoxStockage, Abonnement,
    Notification, Evaluation, PieceJustificative, Contrat, LogConnexion,
    CalendrierDisponibilite
)

# Configuration de base
admin.site.site_header = "Administration EcoDeli"
admin.site.site_title = "Portail d'administration EcoDeli"
admin.site.index_title = "Bienvenue sur le portail d'administration d'EcoDeli"

# Utilisateurs et Profils
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'user_type', 'date_joined', 'is_active')
    list_filter = ('user_type', 'is_active')
    search_fields = ('username', 'email', 'phone')
    fieldsets = (
        ('Informations personnelles', {'fields': ('username', 'email', 'password', 'first_name', 'last_name', 'user_type')}),
        ('Coordonnées', {'fields': ('phone', 'address', 'date_naissance', 'pays')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates importantes', {'fields': ('last_login', 'date_joined')}),
    )

@admin.register(Livreur)
class LivreurAdmin(admin.ModelAdmin):
    list_display = ('user', 'verified', 'rating', 'disponible')
    list_filter = ('verified', 'disponible')
    search_fields = ('user__username', 'user__email')

@admin.register(Commercant)
class CommercantAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'siret', 'contract_signed')
    list_filter = ('contract_signed',)
    search_fields = ('user__username', 'company_name', 'siret')

@admin.register(Prestataire)
class PrestataireAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialites', 'tarif_horaire', 'disponible', 'verified', 'rating')
    list_filter = ('disponible', 'verified')
    search_fields = ('user__username', 'specialites')

# Opérations principales
@admin.register(Annonce)
class AnnonceAdmin(admin.ModelAdmin):
    list_display = ('titre', 'created_by', 'depart', 'arrivee', 'date_depart', 'prix', 'status')
    list_filter = ('status', 'type_annonce')
    search_fields = ('titre', 'description', 'created_by__username')
    date_hierarchy = 'created_at'

@admin.register(Livraison)
class LivraisonAdmin(admin.ModelAdmin):
    list_display = ('reference', 'livreur', 'client', 'date_prise_en_charge', 'date_livraison_prevue', 'status')
    list_filter = ('status',)
    search_fields = ('reference', 'livreur__username', 'client__username', 'description_colis')
    date_hierarchy = 'date_prise_en_charge'

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_service', 'prestataire', 'prix', 'disponible')
    list_filter = ('type_service', 'disponible')
    search_fields = ('nom', 'description', 'prestataire__username')

# Finances
@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('reference', 'montant', 'payeur', 'beneficiaire', 'date_paiement', 'status')
    list_filter = ('status', 'mode_paiement')
    search_fields = ('reference', 'payeur__username', 'beneficiaire__username')
    date_hierarchy = 'date_paiement'

@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ('reference', 'montant_total', 'date_emission', 'status_paiement')
    list_filter = ('status_paiement',)
    search_fields = ('reference',)
    date_hierarchy = 'date_emission'

# Infrastructure
@admin.register(Entrepot)
class EntrepotAdmin(admin.ModelAdmin):
    list_display = ('nom', 'ville', 'code_postal', 'capacite_totale', 'est_bureau')
    list_filter = ('est_bureau',)
    search_fields = ('nom', 'adresse', 'ville')

@admin.register(BoxStockage)
class BoxStockageAdmin(admin.ModelAdmin):
    list_display = ('reference', 'entrepot', 'capacite', 'tarif_jour', 'disponible')
    list_filter = ('disponible', 'entrepot')
    search_fields = ('reference',)

# Gestion utilisateurs
@admin.register(Abonnement)
class AbonnementAdmin(admin.ModelAdmin):
    list_display = ('user', 'type_abonnement', 'date_debut', 'date_fin', 'actif', 'prix_mensuel')
    list_filter = ('type_abonnement', 'actif')
    search_fields = ('user__username',)
    date_hierarchy = 'date_debut'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'user', 'lue', 'date_creation')
    list_filter = ('lue',)
    search_fields = ('titre', 'message', 'user__username')
    date_hierarchy = 'date_creation'

@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('evaluateur', 'evalue', 'note', 'date_evaluation')
    list_filter = ('note',)
    search_fields = ('evaluateur__username', 'evalue__username', 'commentaire')
    date_hierarchy = 'date_evaluation'

# Documents
@admin.register(PieceJustificative)
class PieceJustificativeAdmin(admin.ModelAdmin):
    list_display = ('user', 'type_piece', 'date_upload', 'validee')
    list_filter = ('type_piece', 'validee')
    search_fields = ('user__username',)
    date_hierarchy = 'date_upload'

@admin.register(Contrat)
class ContratAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'date_debut', 'date_fin', 'status')
    list_filter = ('status',)
    search_fields = ('reference', 'user__username', 'description')
    date_hierarchy = 'date_debut'

# Disponibilités et Logs
@admin.register(CalendrierDisponibilite)
class CalendrierDisponibiliteAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_debut', 'date_fin', 'disponible')
    list_filter = ('disponible',)
    search_fields = ('user__username', 'notes')
    date_hierarchy = 'date_debut'

@admin.register(LogConnexion)
class LogConnexionAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_connexion', 'adresse_ip', 'navigateur')
    search_fields = ('user__username', 'adresse_ip')
    date_hierarchy = 'date_connexion'