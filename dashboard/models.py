from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
import os

def generate_unique_reference(prefix, length=6):
    """Génère une référence unique avec préfixe."""
    return f"{prefix}-{uuid.uuid4().hex[:length].upper()}"


#By Oceane
class Message(models.Model):
    sender = models.ForeignKey(
        'User', related_name='sent_messages', on_delete=models.CASCADE
    )
    receiver = models.ForeignKey(
        'User', related_name='received_messages', on_delete=models.CASCADE
    )
    annonce = models.ForeignKey(
        'Annonce', related_name='messages', on_delete=models.CASCADE
    )
    content = models.TextField(verbose_name="Contenu du message")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Envoyé le")

    def __str__(self):
        return f"De {self.sender.username} à {self.receiver.username} ({self.timestamp.strftime('%d/%m/%Y %H:%M')})"


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin', 'Administrateur'),
        ('livreur', 'Livreur'),
        ('client', 'Client'),
        ('commercant', 'Commerçant'),
        ('prestataire', 'Prestataire'),
    )
    
    @property
    def revenu_total(self):
        total = self.paiements_recus.filter(status='reussi').aggregate(
            total=Sum('montant')
        )['total']
        return total or 0

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='dashboard_user_set',
        related_query_name='user',
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='dashboard_user_permission_set',
        related_query_name='user',
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='client')
    phone = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        validators=[RegexValidator(r'^\+?[0-9]{9,15}$', message="Format de téléphone invalide")]
    )
    address = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_naissance = models.DateField(blank=True, null=True)
    pays = models.CharField(max_length=100, blank=True, null=True)
    langue_preference = models.CharField(max_length=10, default='fr')
    portefeuille_solde = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    date_derniere_connexion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('utilisateur')
        verbose_name_plural = _('utilisateurs')
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
        ]

    def __str__(self):
        return self.username
    
    def save(self, *args, **kwargs):
        """Surcharge pour gérer les événements post-création"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Création automatique des profils selon le type d'utilisateur
        if is_new:
            if self.user_type == 'livreur':
                # Créer d'abord le livreur sans référence à la demande
                livreur = Livreur.objects.create(user=self)
                # Ensuite créer la demande de validation
                demande = DemandeValidationLivreur.objects.create(user=self)
                # Puis mettre à jour le livreur avec la référence à la demande
                livreur.derniere_demande_validation = demande
                livreur.save(update_fields=['derniere_demande_validation'])
            elif self.user_type == 'commercant':
                Commercant.objects.create(user=self)
            elif self.user_type == 'prestataire':
                Prestataire.objects.create(user=self)
            
            # Création de l'abonnement gratuit par défaut
            today = timezone.now().date()
            one_year_later = today.replace(year=today.year + 1)
            Abonnement.objects.create(
                user=self,
                type_abonnement='free',
                date_debut=today,
                date_fin=one_year_later,
                actif=True
            )
    
    def get_rating(self):
        """Retourne la note moyenne de l'utilisateur."""
        evaluations = self.evaluations_recues.all()
        if not evaluations:
            return 0
        return sum(e.note for e in evaluations) / evaluations.count()
    
    def est_disponible(self):
        """Vérifie si l'utilisateur est disponible."""
        if hasattr(self, 'livreur_profile'):
            return self.livreur_profile.disponible
        if hasattr(self, 'prestataire_profile'):
            return self.prestataire_profile.disponible
        return False
    from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def set_user_type_for_superuser(sender, instance, created, **kwargs):
    if created and instance.is_superuser and instance.user_type != 'admin':
        instance.user_type = 'admin'
        instance.save(update_fields=['user_type'])

# Modifié: Changement de l'ordre de définition des modèles pour résoudre le problème de référence circulaire
class Livreur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='livreur_profile')
    verified = models.BooleanField(default=False)
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)
    id_card = models.FileField(upload_to='documents/id_cards/', blank=True, null=True)
    driving_license = models.FileField(upload_to='documents/driving_licenses/', blank=True, null=True)
    disponible = models.BooleanField(default=True)
    zones_livraison = models.TextField(blank=True, null=True, help_text="Zones de livraison préférées")
    nombre_livraisons = models.IntegerField(default=0)
    date_inscription = models.DateTimeField(auto_now_add=True)
    derniere_demande_validation = models.ForeignKey(
        'DemandeValidationLivreur',  # En utilisant des guillemets, on peut référencer un modèle défini plus tard
        on_delete=models.SET_NULL, 
        related_name='livreur',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('livreur')
        verbose_name_plural = _('livreurs')
    
    def __str__(self):
        return f"Livreur: {self.user.username}"
    
    def update_rating(self):
        """Met à jour la note moyenne du livreur."""
        evaluations = self.user.evaluations_recues.all()
        if evaluations:
            self.rating = sum(e.note for e in evaluations) / evaluations.count()
            self.save(update_fields=['rating'])
    
    def documents_valides(self):
        """Vérifie si les documents obligatoires sont fournis."""
        return bool(self.id_card and self.driving_license)

class DemandeValidationLivreur(models.Model):
    STATUS_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_examen', 'En cours d\'examen'),
        ('validee', 'Validée'),
        ('refusee', 'Refusée')
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demandes_validation_livreur')
    date_demande = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='en_attente')
    traitee_par = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name='validations_livreurs_traitees',
        null=True, 
        blank=True
    )
    motif_refus = models.TextField(blank=True, null=True)
    notes_admin = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = _('demande de validation livreur')
        verbose_name_plural = _('demandes de validation livreur')
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['date_demande']),
        ]
    
    def __str__(self):
        return f"Demande de {self.user.username} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        """Override save method to update related models when status changes"""
        # Si le statut passe à validée, mettre à jour la date de traitement si elle n'est pas déjà définie
        if self.status == 'validee' and not self.date_traitement:
            self.date_traitement = timezone.now()
            
        # Si le statut passe à refusée, aussi mettre à jour la date de traitement
        elif self.status == 'refusee' and not self.date_traitement:
            self.date_traitement = timezone.now()
            
        super().save(*args, **kwargs)
        
        # Si la demande est validée, mettre à jour le statut du livreur
        if self.status == 'validee':
            try:
                # Mise à jour du profil livreur si il existe
                livreur = Livreur.objects.get(user=self.user)
                livreur.verified = True
                livreur.save(update_fields=['verified'])
                
                # Notification à l'utilisateur (si la fonction existe)
                if 'Notification' in globals():
                    Notification.creer_notification(
                        user=self.user,
                        titre="Demande de livreur acceptée",
                        message="Votre demande pour devenir livreur a été acceptée. Vous pouvez maintenant proposer vos services.",
                        type_notification='success',
                        lien=None
                    )
            except Livreur.DoesNotExist:
                # Si le livreur n'existe pas pour une raison quelconque, on peut le créer
                Livreur.objects.create(
                    user=self.user,
                    verified=True,
                    derniere_demande_validation=self
                )
    
    def valider(self, admin, notes=None):
        """Valide la demande de livreur."""
        self.status = 'validee'
        self.traitee_par = admin
        self.date_traitement = timezone.now()
        if notes:
            self.notes_admin = notes
        self.save()
        
        # Mise à jour du profil livreur
        try:
            livreur = Livreur.objects.get(user=self.user)
            livreur.verified = True
            livreur.save(update_fields=['verified'])
        except Livreur.DoesNotExist:
            # Si le livreur n'existe pas, le créer
            Livreur.objects.create(
                user=self.user,
                verified=True,
                derniere_demande_validation=self
            )
        
        # Notification à l'utilisateur
        Notification.creer_notification(
            user=self.user,
            titre="Demande de livreur acceptée",
            message="Votre demande pour devenir livreur a été acceptée. Vous pouvez maintenant proposer vos services.",
            type_notification='success',
            lien=None
        )
        
        return True
    
    def refuser(self, admin, motif, notes=None):
        """Refuse la demande de livreur."""
        self.status = 'refusee'
        self.traitee_par = admin
        self.date_traitement = timezone.now()
        self.motif_refus = motif
        if notes:
            self.notes_admin = notes
        self.save()
        
        # Notification à l'utilisateur
        Notification.creer_notification(
            user=self.user,
            titre="Demande de livreur refusée",
            message=f"Votre demande pour devenir livreur a été refusée. Motif: {motif}",
            type_notification='warning',
            lien=None
        )
        
        return True
    
    def en_examen(self, admin, notes=None):
        """Marque la demande comme étant en cours d'examen."""
        self.status = 'en_examen'
        self.traitee_par = admin
        if notes:
            self.notes_admin = notes
        self.save()
        
        # Notification à l'utilisateur
        Notification.creer_notification(
            user=self.user,
            titre="Demande de livreur en cours d'examen",
            message="Votre demande est en cours d'examen par notre équipe.",
            type_notification='info',
            lien=None
        )
        
        return True

class Commercant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='commercant_profile')
    company_name = models.CharField(max_length=255)
    siret = models.CharField(
        max_length=14,
        validators=[RegexValidator(r'^\d{14}$', message="Le SIRET doit comporter 14 chiffres")]
    )
    company_address = models.TextField()
    contract_signed = models.BooleanField(default=False)
    contract_file = models.FileField(upload_to='contracts/', blank=True, null=True)
    contract_start_date = models.DateField(blank=True, null=True)
    contract_end_date = models.DateField(blank=True, null=True)
    contract_type = models.CharField(max_length=50, blank=True, null=True)
    taux_commission = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=10.00,
        help_text="Taux de commission en pourcentage"
    )
    
    class Meta:
        verbose_name = _('commerçant')
        verbose_name_plural = _('commerçants')
        indexes = [
            models.Index(fields=['siret']),
        ]
    
    def __str__(self):
        return self.company_name
    
    def contrat_actif(self):
        """Vérifie si le contrat est actif."""
        today = timezone.now().date()
        return (self.contract_signed and 
                self.contract_start_date and 
                (not self.contract_end_date or self.contract_end_date >= today))

class Prestataire(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='prestataire_profile')
    specialites = models.CharField(max_length=255)
    tarif_horaire = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    disponible = models.BooleanField(default=True)
    verified = models.BooleanField(default=False)
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    certifications = models.TextField(blank=True, null=True)
    nombre_services = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = _('prestataire')
        verbose_name_plural = _('prestataires')
    
    def __str__(self):
        return f"Prestataire: {self.user.username}"
    
    def update_rating(self):
        """Met à jour la note moyenne du prestataire."""
        evaluations = self.user.evaluations_recues.all()
        if evaluations:
            self.rating = sum(e.note for e in evaluations) / evaluations.count()
            self.save(update_fields=['rating'])

class CalendrierDisponibilite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disponibilites')
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    disponible = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    recurrence = models.CharField(
        max_length=20, 
        choices=(
            ('none', 'Aucune'),
            ('daily', 'Quotidienne'),
            ('weekly', 'Hebdomadaire'),
            ('monthly', 'Mensuelle')
        ),
        default='none'
    )
    
    class Meta:
        verbose_name = _('disponibilité')
        verbose_name_plural = _('disponibilités')
        indexes = [
            models.Index(fields=['date_debut', 'date_fin']),
            models.Index(fields=['user', 'disponible']),
        ]
    
    def __str__(self):
        return f"Disponibilité: {self.user.username} ({self.date_debut} - {self.date_fin})"
    
    def clean(self):
        """Valide les dates de disponibilité."""
        from django.core.exceptions import ValidationError
        if self.date_debut >= self.date_fin:
            raise ValidationError("La date de début doit être antérieure à la date de fin.")
        
        # Vérifier les chevauchements
        chevauchements = CalendrierDisponibilite.objects.filter(
            user=self.user,
            date_debut__lt=self.date_fin,
            date_fin__gt=self.date_debut
        )
        if self.pk:
            chevauchements = chevauchements.exclude(pk=self.pk)
        if chevauchements.exists():
            raise ValidationError("Cette plage horaire chevauche une disponibilité existante.")

class Annonce(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    )
    
    TYPE_CHOICES = (
        ('colis', 'Colis'),
        ('service', 'Service à la personne'),
    )
    
    titre = models.CharField(max_length=255)
    description = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='annonces')
    depart = models.CharField(max_length=255)
    arrivee = models.CharField(max_length=255)
    date_depart = models.DateTimeField()
    date_arrivee = models.DateTimeField()
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    type_annonce = models.CharField(max_length=20, choices=TYPE_CHOICES, default='colis')
    poids = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    dimensions = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    est_urgente = models.BooleanField(default=False)
    vues = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = _('annonce')
        verbose_name_plural = _('annonces')
        indexes = [
            models.Index(fields=['status', 'type_annonce']),
            models.Index(fields=['created_at']),
            models.Index(fields=['date_depart']),
        ]
    
    def __str__(self):
        return self.titre
    
    def clean(self):
        """Valide les dates de l'annonce."""
        from django.core.exceptions import ValidationError
        if self.date_depart >= self.date_arrivee:
            raise ValidationError("La date de départ doit être antérieure à la date d'arrivée.")
        
        if self.date_depart < timezone.now():
            raise ValidationError("La date de départ ne peut pas être dans le passé.")
    
    def get_statut_affichage(self):
        """Retourne le statut formaté pour l'affichage."""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def est_modifiable(self):
        """Détermine si l'annonce peut être modifiée."""
        return self.status in ['active']
    
    def est_disponible(self):
        """Vérifie si l'annonce est disponible."""
        return self.status == 'active' and self.date_depart > timezone.now()

class Service(models.Model):
    TYPE_CHOICES = (
        ('transport', 'Transport de personnes'),
        ('courses', 'Courses'),
        ('achat_etranger', 'Achat à l\'étranger'),
        ('garde_animaux', 'Garde d\'animaux'),
        ('travaux', 'Petits travaux'),
        ('autre', 'Autre'),
    )
    
    nom = models.CharField(max_length=255)
    description = models.TextField()
    type_service = models.CharField(max_length=20, choices=TYPE_CHOICES)
    prestataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services_offerts')
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    disponible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    duree_estimee = models.IntegerField(
        default=60,
        help_text="Durée estimée en minutes",
        validators=[MinValueValidator(15)]
    )
    zone_intervention = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        verbose_name = _('service')
        verbose_name_plural = _('services')
        indexes = [
            models.Index(fields=['type_service', 'disponible']),
        ]
    
    def __str__(self):
        return self.nom
    
    def save(self, *args, **kwargs):
        """Mise à jour du nombre de services pour le prestataire."""
        super().save(*args, **kwargs)
        
        if self.prestataire.user_type == 'prestataire':
            prestataire = self.prestataire.prestataire_profile
            prestataire.nombre_services = Service.objects.filter(
                prestataire=self.prestataire,
                disponible=True
            ).count()
            prestataire.save(update_fields=['nombre_services'])

class Entrepot(models.Model):
    nom = models.CharField(max_length=255)
    adresse = models.TextField()
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    capacite_totale = models.IntegerField()
    est_bureau = models.BooleanField(default=False)
    responsable = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name='entrepots_geres',
        null=True, 
        blank=True
    )
    
    class Meta:
        verbose_name = _('entrepôt')
        verbose_name_plural = _('entrepôts')
    
    def __str__(self):
        return self.nom
    
    def capacite_disponible(self):
        """Calcule la capacité encore disponible."""
        capacite_utilisee = sum(
            box.capacite for box in self.boxes.filter(disponible=False)
        )
        return self.capacite_totale - capacite_utilisee
    
    def taux_occupation(self):
        """Calcule le taux d'occupation en pourcentage."""
        if self.capacite_totale == 0:
            return 0
        return 100 - (self.capacite_disponible() / self.capacite_totale * 100)

class BoxStockage(models.Model):
    entrepot = models.ForeignKey(Entrepot, on_delete=models.CASCADE, related_name='boxes')
    reference = models.CharField(max_length=10)
    capacite = models.DecimalField(max_digits=6, decimal_places=2)  # en m³
    tarif_jour = models.DecimalField(max_digits=6, decimal_places=2)
    disponible = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _('box de stockage')
        verbose_name_plural = _('boxes de stockage')
        unique_together = ('entrepot', 'reference')
    
    def __str__(self):
        return f"Box {self.reference} - {self.entrepot.nom}"

class Livraison(models.Model):
    STATUS_CHOICES = (
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    )
    
    reference = models.CharField(max_length=10, unique=True)
    annonce = models.ForeignKey(Annonce, on_delete=models.CASCADE, related_name='livraisons')
    livreur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='livraisons_effectuees')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='livraisons_recues')
    description_colis = models.TextField()
    poids = models.DecimalField(max_digits=6, decimal_places=2)
    dimensions = models.CharField(max_length=100, blank=True)
    date_prise_en_charge = models.DateTimeField()
    date_livraison_prevue = models.DateTimeField()
    date_livraison_reelle = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    code_validation = models.CharField(max_length=6)
    trajet_complet = models.TextField(blank=True, null=True, help_text="Étapes intermédiaires du trajet")
    box_stockage = models.ForeignKey(BoxStockage, on_delete=models.SET_NULL, related_name='livraisons', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('livraison')
        verbose_name_plural = _('livraisons')
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
            models.Index(fields=['date_livraison_prevue']),
        ]
    
    def __str__(self):
        return f"Livraison {self.reference}"
    
    def save(self, *args, **kwargs):
        """Génère une référence unique si nécessaire."""
        if not self.reference:
            self.reference = generate_unique_reference("LIV")
        
        if not self.code_validation:
            import random
            self.code_validation = ''.join(random.choices('0123456789', k=6))
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Met à jour les compteurs et le statut de l'annonce
        if is_new:
            if self.livreur.user_type == 'livreur':
                livreur_profile = self.livreur.livreur_profile
                livreur_profile.nombre_livraisons += 1
                livreur_profile.save(update_fields=['nombre_livraisons'])
            
            self.annonce.status = 'en_cours'
            self.annonce.save(update_fields=['status'])
    
    def est_en_retard(self):
        """Vérifie si la livraison est en retard."""
        return (self.status in ['en_attente', 'en_cours'] and 
                self.date_livraison_prevue < timezone.now())
    
    def marquer_comme_livree(self):
        """Marque la livraison comme livrée."""
        if self.status != 'livree':
            self.status = 'livree'
            self.date_livraison_reelle = timezone.now()
            self.save(update_fields=['status', 'date_livraison_reelle'])
            
            # Met à jour le statut de l'annonce
            self.annonce.status = 'terminee'
            self.annonce.save(update_fields=['status'])
            
            # Libère le box de stockage si utilisé
            if self.box_stockage:
                self.box_stockage.disponible = True
                self.box_stockage.save(update_fields=['disponible'])

class Paiement(models.Model):
    STATUS_CHOICES = (
        ('en_attente', 'En attente'),
        ('reussi', 'Réussi'),
        ('echoue', 'Échoué'),
        ('rembourse', 'Remboursé'),
    )
    
    MODE_CHOICES = (
        ('carte', 'Carte bancaire'),
        ('virement', 'Virement bancaire'),
        ('portefeuille', 'Portefeuille EcoDeli'),
    )
    
    reference = models.CharField(max_length=20, unique=True)
    livraison = models.ForeignKey(Livraison, on_delete=models.CASCADE, related_name='paiements', null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='paiements', null=True, blank=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    payeur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paiements_effectues')
    beneficiaire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='paiements_recus')
    stripe_payment_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    mode_paiement = models.CharField(max_length=20, choices=MODE_CHOICES, default='carte')
    date_paiement = models.DateTimeField(auto_now_add=True)
    date_derniere_mise_a_jour = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('paiement')
        verbose_name_plural = _('paiements')
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Paiement {self.reference} - {self.montant}€"
    
    def save(self, *args, **kwargs):
        """Génère une référence unique si nécessaire."""
        if not self.reference:
            self.reference = generate_unique_reference("PAY")
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new or self._status_changed():
            # Générer une facture si le paiement est réussi
            if self.status == 'reussi':
                Facture.objects.create(
                    reference=generate_unique_reference("FAC"),
                    paiement=self,
                    montant_total=self.montant,
                    status_paiement='reussi'
                )
                
                # Mettre à jour le portefeuille du bénéficiaire
                self.beneficiaire.portefeuille_solde += self.montant
                self.beneficiaire.save(update_fields=['portefeuille_solde'])
    
    def _status_changed(self):
        """Vérifie si le statut a changé."""
        if not self.pk:
            return False
        old_status = Paiement.objects.get(pk=self.pk).status
        return old_status != self.status

class Facture(models.Model):
    reference = models.CharField(max_length=20, unique=True)
    paiement = models.OneToOneField(Paiement, on_delete=models.CASCADE, related_name='facture')
    pdf_file = models.FileField(upload_to='factures/', blank=True, null=True)
    date_emission = models.DateTimeField(auto_now_add=True)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    status_paiement = models.CharField(max_length=20, choices=Paiement.STATUS_CHOICES, default='en_attente')
    
    class Meta:
        verbose_name = _('facture')
        verbose_name_plural = _('factures')
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['date_emission']),
        ]
    
    def __str__(self):
        return f"Facture {self.reference}"
    
    def generer_pdf(self):
        """Génère le fichier PDF de la facture."""
        # Cette méthode serait implémentée avec une bibliothèque comme reportlab
        # Pour l'instant, c'est un placeholder
        from django.core.files.base import ContentFile
        
        # Code pour générer le PDF
        # pdf_content = create_pdf(self)
        # self.pdf_file.save(f"facture_{self.reference}.pdf", ContentFile(pdf_content))
        # self.save(update_fields=['pdf_file'])
        pass

class Abonnement(models.Model):
    TYPE_CHOICES = (
        ('free', 'Free'),
        ('starter', 'Starter'),
        ('premium', 'Premium'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='abonnements')
    type_abonnement = models.CharField(max_length=10, choices=TYPE_CHOICES, default='free')
    date_debut = models.DateField()
    date_fin = models.DateField()
    actif = models.BooleanField(default=True)
    prix_mensuel = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    auto_renouvellement = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('abonnement')
        verbose_name_plural = _('abonnements')
    
    def __str__(self):
        return f"{self.user.username} - {self.get_type_abonnement_display()}"
    
    def est_actif(self):
        """Vérifie si l'abonnement est actif."""
        today = timezone.now().date()
        return self.actif and self.date_debut <= today <= self.date_fin
    
    def jours_restants(self):
        """Calcule le nombre de jours restants."""
        today = timezone.now().date()
        if today > self.date_fin:
            return 0
        return (self.date_fin - today).days

class Notification(models.Model):
    TYPE_CHOICES = (
        ('info', 'Information'),
        ('success', 'Succès'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    titre = models.CharField(max_length=255)
    message = models.TextField()
    lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    type_notification = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info')
    lien = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        indexes = [
            models.Index(fields=['user', 'lue']),
            models.Index(fields=['date_creation']),
        ]
    
    def __str__(self):
        return self.titre
    
    @classmethod
    def creer_notification(cls, user, titre, message, type_notification='info', lien=None):
        """Crée une nouvelle notification."""
        return cls.objects.create(
            user=user,
            titre=titre,
            message=message,
            type_notification=type_notification,
            lien=lien
        )

class Evaluation(models.Model):
    evaluateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluations_donnees')
    evalue = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluations_recues')
    livraison = models.ForeignKey(Livraison, on_delete=models.CASCADE, related_name='evaluations', null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='evaluations', null=True, blank=True)
    note = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    commentaire = models.TextField(blank=True, null=True)
    date_evaluation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('évaluation')
        verbose_name_plural = _('évaluations')
        indexes = [
            models.Index(fields=['evaluateur', 'evalue']),
            models.Index(fields=['note']),
            models.Index(fields=['date_evaluation']),
        ]
    
    def __str__(self):
        return f"Évaluation de {self.evalue.username} par {self.evaluateur.username}"
    
    def save(self, *args, **kwargs):
        """Mise à jour de la note moyenne de l'évalué."""
        super().save(*args, **kwargs)
        
        # Mettre à jour la note du livreur ou prestataire évalué
        if self.evalue.user_type == 'livreur' and hasattr(self.evalue, 'livreur_profile'):
            self.evalue.livreur_profile.update_rating()
        elif self.evalue.user_type == 'prestataire' and hasattr(self.evalue, 'prestataire_profile'):
            self.evalue.prestataire_profile.update_rating()
        
        # Envoyer une notification à l'évalué
        Notification.objects.create(
            user=self.evalue,
            titre=f"Nouvelle évaluation reçue",
            message=f"{self.evaluateur.username} vous a donné une note de {self.note}/5.",
            type_notification='info'
        )

class PieceJustificative(models.Model):
    TYPE_CHOICES = (
        ('id_card', 'Carte d\'identité'),
        ('driving_license', 'Permis de conduire'),
        ('proof_address', 'Justificatif de domicile'),
        ('professional_card', 'Carte professionnelle'),
        ('insurance', 'Attestation d\'assurance'),
        ('other', 'Autre'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pieces_justificatives')
    type_piece = models.CharField(max_length=20, choices=TYPE_CHOICES)
    fichier = models.FileField(upload_to='documents/justificatifs/')
    date_upload = models.DateTimeField(auto_now_add=True)
    validee = models.BooleanField(default=False)
    commentaire_validation = models.TextField(blank=True, null=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    validee_par = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name='validations_pieces',
        null=True, 
        blank=True
    )
    demande_validation = models.ForeignKey(
        DemandeValidationLivreur, 
        on_delete=models.CASCADE, 
        related_name='pieces_justificatives',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('pièce justificative')
        verbose_name_plural = _('pièces justificatives')
    
    def __str__(self):
        return f"{self.get_type_piece_display()} de {self.user.username}"
    
    def valider(self, validateur, commentaire=None):
        """Valide la pièce justificative."""
        self.validee = True
        self.commentaire_validation = commentaire
        self.date_validation = timezone.now()
        self.validee_par = validateur
        self.save()
        
        # Envoyer une notification à l'utilisateur
        Notification.creer_notification(
            user=self.user,
            titre=f"Pièce justificative validée",
            message=f"Votre {self.get_type_piece_display()} a été validée.",
            type_notification='success'
        )
        
        # Si l'utilisateur est un livreur et que la pièce est liée à une demande, 
        # vérifier si toutes les pièces obligatoires sont validées
        if self.demande_validation and self.user.user_type == 'livreur':
            pieces_obligatoires = ['id_card', 'driving_license']
            pieces_validees = PieceJustificative.objects.filter(
                demande_validation=self.demande_validation,
                type_piece__in=pieces_obligatoires,
                validee=True
            ).values_list('type_piece', flat=True)
            
            if set(pieces_obligatoires).issubset(set(pieces_validees)) and self.demande_validation.status == 'en_attente':
                # Mettre la demande en examen automatiquement
                self.demande_validation.en_examen(validateur, "Documents obligatoires validés")
                
                # Notification aux administrateurs
                admins = User.objects.filter(user_type='admin')
                for admin in admins:
                    Notification.creer_notification(
                        user=admin,
                        titre="Nouvelle demande livreur à examiner",
                        message=f"Les pièces justificatives de {self.user.username} ont été validées. Sa demande est prête à être examinée.",
                        type_notification='info',
                        lien="/admin/validation-livreurs/"
                    )

class Contrat(models.Model):
    STATUS_CHOICES = (
        ('actif', 'Actif'),
        ('expire', 'Expiré'),
        ('resilie', 'Résilié'),
        ('en_attente', 'En attente de signature'),
    )
    
    reference = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contrats')
    document = models.FileField(upload_to='contrats/')
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    description = models.TextField(blank=True, null=True)
    date_signature = models.DateField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        related_name='contrats_crees',
        null=True, 
        blank=True
    )
    
    class Meta:
        verbose_name = _('contrat')
        verbose_name_plural = _('contrats')
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
            models.Index(fields=['date_debut']),
        ]
    
    def __str__(self):
        return f"Contrat {self.reference} - {self.user.username}"
    
    def save(self, *args, **kwargs):
        """Génère une référence unique si nécessaire."""
        if not self.reference:
            self.reference = generate_unique_reference("CTR")
        
        # Vérification du statut du contrat
        today = timezone.now().date()
        if self.status == 'actif' and self.date_fin and today > self.date_fin:
            self.status = 'expire'
        
        super().save(*args, **kwargs)
    
    def signer(self):
        """Signe le contrat."""
        self.status = 'actif'
        self.date_signature = timezone.now().date()
        self.save(update_fields=['status', 'date_signature'])
        
        # Si le contrat est pour un commerçant, mettre à jour son profil
        if self.user.user_type == 'commercant' and hasattr(self.user, 'commercant_profile'):
            self.user.commercant_profile.contract_signed = True
            self.user.commercant_profile.contract_start_date = self.date_debut
            self.user.commercant_profile.contract_end_date = self.date_fin
            self.user.commercant_profile.contract_type = "Standard"
            self.user.commercant_profile.save(update_fields=[
                'contract_signed', 'contract_start_date', 'contract_end_date', 'contract_type'
            ])
        
        # Envoyer une notification à l'utilisateur
        Notification.creer_notification(
            user=self.user,
            titre=f"Contrat signé",
            message=f"Votre contrat {self.reference} a été activé.",
            type_notification='success'
        )
    
    def resilier(self, raison=None):
        """Résilie le contrat."""
        self.status = 'resilie'
        if raison:
            self.description += f"\n\nRésilié le {timezone.now().date()} pour la raison suivante: {raison}"
        self.save(update_fields=['status', 'description'])
        
        # Si le contrat est pour un commerçant, mettre à jour son profil
        if self.user.user_type == 'commercant' and hasattr(self.user, 'commercant_profile'):
            self.user.commercant_profile.contract_signed = False
            self.user.commercant_profile.save(update_fields=['contract_signed'])
        
        # Envoyer une notification à l'utilisateur
        Notification.creer_notification(
            user=self.user,
            titre=f"Contrat résilié",
            message=f"Votre contrat {self.reference} a été résilié.",
            type_notification='warning'
        )

class LogConnexion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs_connexion')
    date_connexion = models.DateTimeField(auto_now_add=True)
    adresse_ip = models.GenericIPAddressField()
    navigateur = models.CharField(max_length=255)
    systeme_exploitation = models.CharField(max_length=255)
    reussi = models.BooleanField(default=True)
    details = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = _('log de connexion')
        verbose_name_plural = _('logs de connexion')
        indexes = [
            models.Index(fields=['user', 'date_connexion']),
            models.Index(fields=['adresse_ip']),
            models.Index(fields=['reussi']),
        ]
    
    def __str__(self):
        status = "réussie" if self.reussi else "échouée"
        return f"Connexion {status} de {self.user.username} le {self.date_connexion}"
    
    @classmethod
    def enregistrer_connexion(cls, user, request, reussi=True, details=None):
        """Enregistre une tentative de connexion."""
        # Obtenir l'adresse IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        # Obtenir les informations sur le navigateur et le système d'exploitation
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Créer l'entrée de journal
        log = cls.objects.create(
            user=user,
            adresse_ip=ip,
            navigateur=user_agent,
            systeme_exploitation=user_agent,  # Simplification, idéalement on parserait l'user-agent
            reussi=reussi,
            details=details
        )
        
        # Mettre à jour la date de dernière connexion de l'utilisateur si la connexion a réussi
        if reussi:
            user.date_derniere_connexion = timezone.now()
            user.save(update_fields=['date_derniere_connexion'])
        
        return log
        # À ajouter dans votre models.py

class LangueDisponible(models.Model):
    """Langues disponibles sur la plateforme"""
    code = models.CharField(max_length=5, unique=True)  # 'fr', 'en', 'es', etc.
    nom_natif = models.CharField(max_length=50)  # 'Français', 'English', 'Español'
    nom_francais = models.CharField(max_length=50)  # 'Français', 'Anglais', 'Espagnol'
    active = models.BooleanField(default=True)
    ordre_affichage = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Langue disponible"
        verbose_name_plural = "Langues disponibles"
        ordering = ['ordre_affichage', 'nom_francais']
    
    def __str__(self):
        return f"{self.nom_natif} ({self.code})"

class CategorieTraduction(models.Model):
    """Catégories pour organiser les traductions"""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Catégorie de traduction"
        verbose_name_plural = "Catégories de traductions"
    
    def __str__(self):
        return self.nom

class CleTraduction(models.Model):
    """Clés de traduction avec textes dans différentes langues"""
    cle = models.CharField(max_length=255, unique=True, db_index=True)
    categorie = models.ForeignKey(
        CategorieTraduction, 
        on_delete=models.CASCADE, 
        related_name='cles'
    )
    description = models.TextField(
        blank=True, 
        help_text="Description du contexte d'utilisation"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Clé de traduction"
        verbose_name_plural = "Clés de traductions"
        indexes = [
            models.Index(fields=['cle']),
        ]
    
    def __str__(self):
        return self.cle
    
    def get_traduction(self, langue_code='fr'):
        """Récupère la traduction pour une langue donnée"""
        try:
            traduction = self.traductions.get(langue__code=langue_code)
            return traduction.texte
        except Traduction.DoesNotExist:
            # Fallback vers le français si la traduction n'existe pas
            try:
                traduction = self.traductions.get(langue__code='fr')
                return traduction.texte
            except Traduction.DoesNotExist:
                return self.cle  # Retourne la clé si aucune traduction
    
    def est_complete(self):
        """Vérifie si toutes les langues actives ont une traduction"""
        langues_actives = LangueDisponible.objects.filter(active=True).count()
        traductions_existantes = self.traductions.count()
        return langues_actives == traductions_existantes

class Traduction(models.Model):
    """Traductions des clés dans les différentes langues"""
    cle_traduction = models.ForeignKey(
        CleTraduction, 
        on_delete=models.CASCADE, 
        related_name='traductions'
    )
    langue = models.ForeignKey(
        LangueDisponible, 
        on_delete=models.CASCADE,
        related_name='traductions'
    )
    texte = models.TextField()
    traduit_par = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='traductions_effectuees'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    validee = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Traduction"
        verbose_name_plural = "Traductions"
        unique_together = ('cle_traduction', 'langue')
        indexes = [
            models.Index(fields=['cle_traduction', 'langue']),
        ]
    
    def __str__(self):
        return f"{self.cle_traduction.cle} ({self.langue.code})"

# Fonction utilitaire pour récupérer les traductions
def get_traduction(cle, langue_code='fr', **kwargs):
    """
    Fonction utilitaire pour récupérer une traduction
    Usage: get_traduction('welcome_message', 'en', username='John')
    """
    try:
        cle_obj = CleTraduction.objects.get(cle=cle)
        texte = cle_obj.get_traduction(langue_code)
        
        # Substitution des variables si fournie
        if kwargs:
            texte = texte.format(**kwargs)
        
        return texte
    except CleTraduction.DoesNotExist:
        return cle

# Modèle pour les préférences utilisateur de langue
class PreferenceLangueUtilisateur(models.Model):
    """Préférences de langue par utilisateur"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='preference_langue'
    )
    langue_interface = models.ForeignKey(
        LangueDisponible, 
        on_delete=models.CASCADE,
        related_name='utilisateurs_interface'
    )
    langue_notifications = models.ForeignKey(
        LangueDisponible, 
        on_delete=models.CASCADE,
        related_name='utilisateurs_notifications',
        null=True,
        blank=True
    )
    langue_documents = models.ForeignKey(
        LangueDisponible, 
        on_delete=models.CASCADE,
        related_name='utilisateurs_documents',
        null=True,
        blank=True
    )
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Préférence de langue"
        verbose_name_plural = "Préférences de langues"
    
    def __str__(self):
        return f"{self.user.username} - {self.langue_interface.nom_natif}"
    # À ajouter dans votre models.py

class CategorieEtapeTutoriel(models.Model):
    """Catégories d'étapes de tutoriel par type d'utilisateur"""
    nom = models.CharField(max_length=100)
    type_utilisateur = models.CharField(
        max_length=20, 
        choices=User.USER_TYPE_CHOICES
    )
    ordre = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Catégorie d'étape tutoriel"
        verbose_name_plural = "Catégories d'étapes tutoriel"
        ordering = ['type_utilisateur', 'ordre']
    
    def __str__(self):
        return f"{self.nom} ({self.get_type_utilisateur_display()})"

class EtapeTutoriel(models.Model):
    """Étapes du tutoriel pour chaque type d'utilisateur"""
    TYPE_ETAPE_CHOICES = (
        ('modal', 'Modal/Pop-up'),
        ('overlay', 'Overlay'),
        ('tooltip', 'Info-bulle'),
        ('highlight', 'Mise en évidence'),
        ('video', 'Vidéo'),
        ('interactive', 'Interactif'),
    )
    
    POSITION_CHOICES = (
        ('top', 'Haut'),
        ('bottom', 'Bas'),
        ('left', 'Gauche'),
        ('right', 'Droite'),
        ('center', 'Centre'),
    )
    
    categorie = models.ForeignKey(
        CategorieEtapeTutoriel, 
        on_delete=models.CASCADE, 
        related_name='etapes'
    )
    titre = models.CharField(max_length=255)
    contenu = models.TextField()
    ordre = models.IntegerField()
    type_etape = models.CharField(max_length=20, choices=TYPE_ETAPE_CHOICES)
    
    # Configuration de l'affichage
    element_cible = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Sélecteur CSS de l'élément à cibler"
    )
    position = models.CharField(
        max_length=10, 
        choices=POSITION_CHOICES, 
        default='bottom'
    )
    
    # Options
    obligatoire = models.BooleanField(
        default=True,
        help_text="L'utilisateur doit-il compléter cette étape ?"
    )
    skippable = models.BooleanField(
        default=False,
        help_text="L'utilisateur peut-il passer cette étape ?"
    )
    auto_next = models.BooleanField(
        default=False,
        help_text="Passe automatiquement à l'étape suivante"
    )
    duree_auto = models.IntegerField(
        default=0,
        help_text="Durée en secondes pour l'auto-passage (0 = désactivé)"
    )
    
    # URL et conditions
    url_page = models.CharField(
        max_length=255,
        help_text="URL de la page où afficher cette étape"
    )
    condition_affichage = models.TextField(
        blank=True,
        help_text="Condition JavaScript pour afficher l'étape"
    )
    
    # Multimédia
    image = models.ImageField(upload_to='tutoriel/images/', blank=True, null=True)
    video_url = models.URLField(blank=True)
    
    # Configuration JSON pour des options avancées
    config_avancee = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuration JSON pour des options avancées"
    )
    
    active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Étape de tutoriel"
        verbose_name_plural = "Étapes de tutoriel"
        ordering = ['categorie__type_utilisateur', 'categorie__ordre', 'ordre']
        unique_together = ('categorie', 'ordre')
    
    def __str__(self):
        return f"{self.titre} - {self.categorie.nom}"

class ProgressionTutoriel(models.Model):
    """Progression d'un utilisateur dans le tutoriel"""
    STATUS_CHOICES = (
        ('non_commence', 'Non commencé'),
        ('en_cours', 'En cours'),
        ('complete', 'Terminé'),
        ('abandonne', 'Abandonné'),
        ('reporte', 'Reporté'),
    )
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='progression_tutoriel'
    )
    
    # Statut global
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='non_commence'
    )
    
    # Progression
    premiere_connexion_date = models.DateTimeField(auto_now_add=True)
    tutoriel_commence_date = models.DateTimeField(null=True, blank=True)
    tutoriel_termine_date = models.DateTimeField(null=True, blank=True)
    
    # Configuration
    afficher_au_login = models.BooleanField(
        default=True,
        help_text="Afficher le tutoriel à la prochaine connexion"
    )
    peut_etre_relance = models.BooleanField(
        default=True,
        help_text="L'utilisateur peut-il relancer le tutoriel"
    )
    
    # Compteurs
    nombre_relances = models.IntegerField(default=0)
    temps_total_seconde = models.IntegerField(default=0)
    
    # Dernière étape vue
    derniere_etape = models.ForeignKey(
        EtapeTutoriel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derniere_etape_utilisateurs'
    )
    
    class Meta:
        verbose_name = "Progression tutoriel"
        verbose_name_plural = "Progressions tutoriel"
    
    def __str__(self):
        return f"Tutoriel {self.user.username} - {self.get_status_display()}"
    
    def commencer_tutoriel(self):
        """Démarre le tutoriel pour l'utilisateur"""
        if self.status == 'non_commence':
            self.status = 'en_cours'
            self.tutoriel_commence_date = timezone.now()
            self.save(update_fields=['status', 'tutoriel_commence_date'])
    
    def terminer_tutoriel(self):
        """Marque le tutoriel comme terminé"""
        self.status = 'complete'
        self.tutoriel_termine_date = timezone.now()
        self.afficher_au_login = False
        self.save(update_fields=['status', 'tutoriel_termine_date', 'afficher_au_login'])
        
        # Créer une notification de félicitations
        Notification.creer_notification(
            user=self.user,
            titre="Tutoriel terminé !",
            message="Félicitations ! Vous avez terminé le tutoriel. Vous êtes maintenant prêt à utiliser EcoDeli.",
            type_notification='success'
        )
    
    def relancer_tutoriel(self):
        """Relance le tutoriel"""
        if self.peut_etre_relance:
            self.status = 'en_cours'
            self.nombre_relances += 1
            self.afficher_au_login = True
            self.derniere_etape = None
            self.save(update_fields=['status', 'nombre_relances', 'afficher_au_login', 'derniere_etape'])
            
            # Supprimer les anciennes progressions d'étapes
            self.etapes_completees.all().delete()
    
    def abandonner_tutoriel(self):
        """Abandonne le tutoriel"""
        self.status = 'abandonne'
        self.afficher_au_login = False
        self.save(update_fields=['status', 'afficher_au_login'])
    
    def reporter_tutoriel(self):
        """Reporte le tutoriel à plus tard"""
        self.status = 'reporte'
        self.afficher_au_login = True
        self.save(update_fields=['status', 'afficher_au_login'])
    
    def get_etapes_pour_utilisateur(self):
        """Récupère les étapes du tutoriel pour le type d'utilisateur"""
        categories = CategorieEtapeTutoriel.objects.filter(
            type_utilisateur=self.user.user_type
        ).prefetch_related('etapes')
        
        etapes = []
        for categorie in categories:
            etapes.extend(categorie.etapes.filter(active=True))
        
        return etapes
    
    def get_progression_pourcentage(self):
        """Calcule le pourcentage de progression"""
        etapes_totales = self.get_etapes_pour_utilisateur().count()
        if etapes_totales == 0:
            return 100
        
        etapes_completees = self.etapes_completees.count()
        return int((etapes_completees / etapes_totales) * 100)

class ProgressionEtape(models.Model):
    """Progression d'une étape spécifique du tutoriel"""
    progression = models.ForeignKey(
        ProgressionTutoriel,
        on_delete=models.CASCADE,
        related_name='etapes_completees'
    )
    etape = models.ForeignKey(
        EtapeTutoriel,
        on_delete=models.CASCADE,
        related_name='progressions'
    )
    
    # Timing
    date_debut = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)
    duree_seconde = models.IntegerField(default=0)
    
    # Actions
    completee = models.BooleanField(default=False)
    skippee = models.BooleanField(default=False)
    
    # Interactions
    nombre_clics = models.IntegerField(default=0)
    nombre_retours = models.IntegerField(default=0)
    
    # Feedback
    utile = models.BooleanField(null=True, blank=True)
    commentaire = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Progression d'étape"
        verbose_name_plural = "Progressions d'étapes"
        unique_together = ('progression', 'etape')
    
    def __str__(self):
        return f"{self.progression.user.username} - {self.etape.titre}"
    
    def completer_etape(self, duree=None):
        """Marque l'étape comme complétée"""
        self.completee = True
        self.date_fin = timezone.now()
        
        if duree:
            self.duree_seconde = duree
        elif self.date_debut:
            self.duree_seconde = int((self.date_fin - self.date_debut).total_seconds())
        
        self.save(update_fields=['completee', 'date_fin', 'duree_seconde'])
        
        # Mettre à jour la progression globale
        self.progression.derniere_etape = self.etape
        self.progression.save(update_fields=['derniere_etape'])
        
        # Vérifier si le tutoriel est terminé
        etapes_totales = self.progression.get_etapes_pour_utilisateur().count()
        etapes_completees = self.progression.etapes_completees.filter(completee=True).count()
        
        if etapes_completees >= etapes_totales:
            self.progression.terminer_tutoriel()
    
    def skipper_etape(self):
        """Marque l'étape comme skippée"""
        self.skippee = True
        self.date_fin = timezone.now()
        if self.date_debut:
            self.duree_seconde = int((self.date_fin - self.date_debut).total_seconds())
        
        self.save(update_fields=['skippee', 'date_fin', 'duree_seconde'])

# Signal pour créer automatiquement la progression tutoriel
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def creer_progression_tutoriel(sender, instance, created, **kwargs):
    """Crée automatiquement une progression tutoriel pour les nouveaux utilisateurs"""
    if created and instance.user_type != 'admin':
        ProgressionTutoriel.objects.get_or_create(
            user=instance,
            defaults={
                'status': 'non_commence',
                'afficher_au_login': True,
                'peut_etre_relance': True
            }
        )
    