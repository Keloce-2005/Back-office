from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin', 'Administrateur'),
        ('livreur', 'Livreur'),
        ('client', 'Client'),
        ('commercant', 'Commerçant'),
        ('prestataire', 'Prestataire'),
    )
    
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
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    date_naissance = models.DateField(blank=True, null=True)
    pays = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.username

class Livreur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='livreur_profile')
    verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    vehicle_type = models.CharField(max_length=50, blank=True, null=True)
    id_card = models.FileField(upload_to='documents/id_cards/', blank=True, null=True)
    driving_license = models.FileField(upload_to='documents/driving_licenses/', blank=True, null=True)
    disponible = models.BooleanField(default=True)
    zones_livraison = models.TextField(blank=True, null=True, help_text="Zones de livraison préférées")
    
    def __str__(self):
        return f"Livreur: {self.user.username}"

class Commercant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='commercant_profile')
    company_name = models.CharField(max_length=255)
    siret = models.CharField(max_length=14)
    company_address = models.TextField()
    contract_signed = models.BooleanField(default=False)
    contract_file = models.FileField(upload_to='contracts/', blank=True, null=True)
    contract_start_date = models.DateField(blank=True, null=True)
    contract_end_date = models.DateField(blank=True, null=True)
    contract_type = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return self.company_name

class Prestataire(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='prestataire_profile')
    specialites = models.CharField(max_length=255)
    tarif_horaire = models.DecimalField(max_digits=6, decimal_places=2)
    disponible = models.BooleanField(default=True)
    verified = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    certifications = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Prestataire: {self.user.username}"

class CalendrierDisponibilite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disponibilites')
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    disponible = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Disponibilité: {self.user.username} ({self.date_debut} - {self.date_fin})"

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
    
    def __str__(self):
        return self.titre

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
    
    def __str__(self):
        return self.nom

class Entrepot(models.Model):
    nom = models.CharField(max_length=255)
    adresse = models.TextField()
    ville = models.CharField(max_length=100)
    code_postal = models.CharField(max_length=10)
    capacite_totale = models.IntegerField()
    est_bureau = models.BooleanField(default=False)
    
    def __str__(self):
        return self.nom

class BoxStockage(models.Model):
    entrepot = models.ForeignKey(Entrepot, on_delete=models.CASCADE, related_name='boxes')
    reference = models.CharField(max_length=10)
    capacite = models.DecimalField(max_digits=6, decimal_places=2)  # en m³
    tarif_jour = models.DecimalField(max_digits=6, decimal_places=2)
    disponible = models.BooleanField(default=True)
    
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
    
    def __str__(self):
        return f"Livraison {self.reference}"

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
    
    def __str__(self):
        return f"Paiement {self.reference} - {self.montant}€"

class Facture(models.Model):
    reference = models.CharField(max_length=20, unique=True)
    paiement = models.OneToOneField(Paiement, on_delete=models.CASCADE, related_name='facture')
    pdf_file = models.FileField(upload_to='factures/')
    date_emission = models.DateTimeField(auto_now_add=True)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    status_paiement = models.CharField(max_length=20, choices=Paiement.STATUS_CHOICES, default='en_attente')
    
    def __str__(self):
        return f"Facture {self.reference}"

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
    
    def __str__(self):
        return f"{self.user.username} - {self.get_type_abonnement_display()}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    titre = models.CharField(max_length=255)
    message = models.TextField()
    lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.titre

class Evaluation(models.Model):
    evaluateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluations_donnees')
    evalue = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluations_recues')
    livraison = models.ForeignKey(Livraison, on_delete=models.CASCADE, related_name='evaluations', null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='evaluations', null=True, blank=True)
    note = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    commentaire = models.TextField(blank=True, null=True)
    date_evaluation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Évaluation de {self.evalue.username} par {self.evaluateur.username}"

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
    
    def __str__(self):
        return f"{self.get_type_piece_display()} de {self.user.username}"

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
    
    def __str__(self):
        return f"Contrat {self.reference} - {self.user.username}"

class LogConnexion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs_connexion')
    date_connexion = models.DateTimeField(auto_now_add=True)
    adresse_ip = models.GenericIPAddressField()
    navigateur = models.CharField(max_length=255)
    systeme_exploitation = models.CharField(max_length=255)
    
    def __str__(self):
        return f"Connexion de {self.user.username} le {self.date_connexion}"