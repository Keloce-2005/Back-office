from django.contrib import admin
from django.utils.html import format_html

# Register your models here.
from django.contrib import admin
from .models import (
    User, DemandeValidationLivreur, Livreur, Commercant, Prestataire, Annonce, Livraison, 
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

# Ajouter cette classe pour les pièces justificatives comme inline
class PieceJustificativeInline(admin.TabularInline):
    model = PieceJustificative
    extra = 0
    readonly_fields = ('date_upload', 'date_validation')
    fields = ('type_piece', 'fichier', 'validee', 'date_upload', 'date_validation', 'commentaire_validation')

# Ajouter cette configuration pour la validation des livreurs
@admin.register(DemandeValidationLivreur)
class DemandeValidationLivreurAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_demande', 'status', 'date_traitement', 'traitee_par', 'documents_complets')
    list_filter = ('status', 'date_demande')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('date_demande',)
    inlines = [PieceJustificativeInline]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('user', 'date_demande', 'status')
        }),
        ('Traitement de la demande', {
            'fields': ('traitee_par', 'date_traitement', 'notes_admin', 'motif_refus')
        }),
    )
    
    actions = ['valider_demandes', 'refuser_demandes', 'mettre_en_examen']
    
    def documents_complets(self, obj):
        """Vérifie si tous les documents obligatoires sont fournis."""
        pieces_obligatoires = ['id_card', 'driving_license']
        pieces_validees = PieceJustificative.objects.filter(
            demande_validation=obj,
            type_piece__in=pieces_obligatoires,
            validee=True
        ).values_list('type_piece', flat=True)
        
        complet = set(pieces_obligatoires).issubset(set(pieces_validees))
        
        if complet:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    documents_complets.short_description = "Documents complets"
    
    def valider_demandes(self, request, queryset):
        for demande in queryset:
            demande.valider(request.user)
        
        self.message_user(request, f"{queryset.count()} demande(s) validée(s) avec succès.")
    valider_demandes.short_description = "Valider les demandes sélectionnées"
    
    def refuser_demandes(self, request, queryset):
        for demande in queryset:
            demande.refuser(request.user, "Refus administratif")
        
        self.message_user(request, f"{queryset.count()} demande(s) refusée(s).")
    refuser_demandes.short_description = "Refuser les demandes sélectionnées"
    
    def mettre_en_examen(self, request, queryset):
        for demande in queryset:
            demande.en_examen(request.user)
        
        self.message_user(request, f"{queryset.count()} demande(s) mise(s) en examen.")
    mettre_en_examen.short_description = "Mettre les demandes en examen"

# Compléter la configuration existante de PieceJustificativeAdmin
@admin.register(PieceJustificative)
class PieceJustificativeAdmin(admin.ModelAdmin):
    list_display = ('user', 'type_piece', 'date_upload', 'validee', 'date_validation', 'validee_par', 'demande_validation')
    list_filter = ('validee', 'type_piece', 'date_upload')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('date_upload', 'date_validation')
    
    fieldsets = (
        ('Document', {
            'fields': ('user', 'type_piece', 'fichier', 'date_upload', 'demande_validation')
        }),
        ('Validation', {
            'fields': ('validee', 'validee_par', 'date_validation', 'commentaire_validation')
        }),
    )
    
    actions = ['valider_pieces']
    
    def valider_pieces(self, request, queryset):
        for piece in queryset:
            piece.valider(request.user)
        
        self.message_user(request, f"{queryset.count()} pièce(s) validée(s) avec succès.")
    valider_pieces.short_description = "Valider les pièces sélectionnées"

