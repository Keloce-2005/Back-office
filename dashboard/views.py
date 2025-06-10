from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from django.contrib import messages
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from dashboard.models import (
    User, Livreur, Commercant, Prestataire, Annonce, Livraison, 
    Paiement, Facture, Service, Entrepot, BoxStockage, Abonnement,
    Notification, Evaluation, PieceJustificative, Contrat, LogConnexion,
    DemandeValidationLivreur
)

# Fonction utilitaire pour obtenir le chiffre d'affaires mensuel
def get_monthly_revenue(year=None, month=None):
    """Calcule le chiffre d'affaires pour un mois donné."""
    if year is None or month is None:
        # Utiliser le mois et l'année actuels par défaut
        now = timezone.now()
        year = now.year
        month = now.month
    
    # Calculer les revenus pour le mois spécifié
    revenue = Paiement.objects.filter(
        status='reussi',
        date_paiement__year=year,
        date_paiement__month=month
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    
    return revenue

@login_required
def home(request):
    # Statistiques pour le tableau de bord
    stats = {
        'total_livreurs': Livreur.objects.count(),
        'total_commercants': Commercant.objects.count(),
        'total_clients': User.objects.filter(user_type='client').count(),
        'total_prestataires': Prestataire.objects.count(),
        'livraisons_en_cours': Livraison.objects.filter(status='en_cours').count(),
        'paiements_aujourd_hui': Paiement.objects.filter(
            date_paiement__date=timezone.now().date()
        ).count(),
        'chiffre_affaires_mois': Paiement.objects.filter(
            status='reussi',
            date_paiement__month=timezone.now().month,
            date_paiement__year=timezone.now().year
        ).aggregate(Sum('montant'))['montant__sum'] or 0,
    }
    
    # Dernières livraisons
    livraisons_recentes = Livraison.objects.all().order_by('-created_at')[:5]
    
    # Derniers paiements
    paiements_recents = Paiement.objects.all().order_by('-date_paiement')[:5]
    
    # Notifications non lues
    notifications_non_lues = Notification.objects.filter(lue=False).count()
    
    return render(request, 'dashboard/home.html', {
        'active_menu': 'accueil',
        'stats': stats,
        'livraisons_recentes': livraisons_recentes,
        'paiements_recents': paiements_recents,
        'notifications_non_lues': notifications_non_lues
    })

@login_required
def livreurs(request):
    # Récupérer tous les livreurs de la base de données avec les informations utilisateur
    livreurs_list = Livreur.objects.select_related('user').all()
    
    # Statistiques des livreurs
    stats = {
        'total_livreurs': livreurs_list.count(),
        'livreurs_disponibles': livreurs_list.filter(disponible=True).count(),
        'note_moyenne': livreurs_list.aggregate(Avg('rating'))['rating__avg'] or 0,
    }
    
    return render(request, 'dashboard/livreurs.html', {
        'active_menu': 'livreurs', 
        'livreurs': livreurs_list,
        'stats': stats
    })

@login_required
def livreur_detail(request, livreur_id):
    livreur = get_object_or_404(Livreur, id=livreur_id)
    
    # Récupérer les documents, livraisons et paiements associés
    pieces_justificatives = PieceJustificative.objects.filter(user=livreur.user)
    livraisons = Livraison.objects.filter(livreur=livreur.user).order_by('-created_at')
    paiements = Paiement.objects.filter(beneficiaire=livreur.user).order_by('-date_paiement')
    evaluations = Evaluation.objects.filter(evalue=livreur.user).order_by('-date_evaluation')
    
    # Calculer les statistiques du livreur
    stats = {
        'livraisons_total': livraisons.count(),
        'livraisons_en_cours': livraisons.filter(status='en_cours').count(),
        'livraisons_terminees': livraisons.filter(status='livree').count(),
        'revenus_total': paiements.filter(status='reussi').aggregate(Sum('montant'))['montant__sum'] or 0,
        'note_moyenne': evaluations.aggregate(Avg('note'))['note__avg'] or 0,
    }
    
    return render(request, 'dashboard/livreur_detail.html', {
        'active_menu': 'livreurs',
        'livreur': livreur,
        'pieces_justificatives': pieces_justificatives,
        'livraisons': livraisons,
        'paiements': paiements,
        'evaluations': evaluations,
        'stats': stats
    })

@login_required
def commercants(request):
    commercants_list = Commercant.objects.select_related('user').all()
    
    # Statistiques des commerçants
    stats = {
        'total_commercants': commercants_list.count(),
        'commercants_avec_contrat': commercants_list.filter(contract_signed=True).count(),
    }
    
    return render(request, 'dashboard/commercants.html', {
        'active_menu': 'commercants',
        'commercants': commercants_list,
        'stats': stats
    })

@login_required
def commercant_detail(request, commercant_id):
    commercant = get_object_or_404(Commercant, id=commercant_id)
    annonces = Annonce.objects.filter(created_by=commercant.user).order_by('-created_at')
    contrats = Contrat.objects.filter(user=commercant.user).order_by('-date_debut')
    factures = Facture.objects.filter(paiement__payeur=commercant.user).order_by('-date_emission')
    
    # Statistiques du commerçant
    stats = {
        'annonces_total': annonces.count(),
        'annonces_actives': annonces.filter(status='active').count(),
        'chiffre_affaires': Paiement.objects.filter(
            payeur=commercant.user, status='reussi'
        ).aggregate(Sum('montant'))['montant__sum'] or 0,
    }
    
    return render(request, 'dashboard/commercant_detail.html', {
        'active_menu': 'commercants',
        'commercant': commercant,
        'annonces': annonces,
        'contrats': contrats,
        'factures': factures,
        'stats': stats
    })

@login_required
def clients(request):
    clients_list = User.objects.filter(user_type='client')
    
    # Statistiques des clients
    stats = {
        'total_clients': clients_list.count(),
        'clients_avec_abonnement': Abonnement.objects.filter(
            user__in=clients_list, actif=True
        ).exclude(type_abonnement='free').count(),
    }
    
    return render(request, 'dashboard/clients.html', {
        'active_menu': 'clients',
        'clients': clients_list,
        'stats': stats
    })

@login_required
def client_detail(request, client_id):
    client = get_object_or_404(User, id=client_id, user_type='client')
    annonces = Annonce.objects.filter(created_by=client).order_by('-created_at')
    livraisons = Livraison.objects.filter(client=client).order_by('-created_at')
    paiements = Paiement.objects.filter(payeur=client).order_by('-date_paiement')
    abonnements = Abonnement.objects.filter(user=client).order_by('-date_debut')
    
    # Statistiques du client
    stats = {
        'annonces_total': annonces.count(),
        'livraisons_total': livraisons.count(),
        'depenses_total': paiements.filter(status='reussi').aggregate(Sum('montant'))['montant__sum'] or 0,
    }
    
    return render(request, 'dashboard/client_detail.html', {
        'active_menu': 'clients',
        'client': client,
        'annonces': annonces,
        'livraisons': livraisons,
        'paiements': paiements,
        'abonnements': abonnements,
        'stats': stats
    })

@login_required
def prestataires(request):
    prestataires_list = Prestataire.objects.select_related('user').all()
    
    # Statistiques des prestataires
    stats = {
        'total_prestataires': prestataires_list.count(),
        'prestataires_disponibles': prestataires_list.filter(disponible=True).count(),
        'note_moyenne': prestataires_list.aggregate(Avg('rating'))['rating__avg'] or 0,
    }
    
    return render(request, 'dashboard/prestataires.html', {
        'active_menu': 'prestataires',
        'prestataires': prestataires_list,
        'stats': stats
    })

@login_required
def prestataire_detail(request, prestataire_id):
    prestataire = get_object_or_404(Prestataire, id=prestataire_id)
    services = Service.objects.filter(prestataire=prestataire.user).order_by('-created_at')
    evaluations = Evaluation.objects.filter(evalue=prestataire.user).order_by('-date_evaluation')
    paiements = Paiement.objects.filter(beneficiaire=prestataire.user).order_by('-date_paiement')
    
    # Statistiques du prestataire
    stats = {
        'services_total': services.count(),
        'services_disponibles': services.filter(disponible=True).count(),
        'revenus_total': paiements.filter(status='reussi').aggregate(Sum('montant'))['montant__sum'] or 0,
        'note_moyenne': evaluations.aggregate(Avg('note'))['note__avg'] or 0,
    }
    
    return render(request, 'dashboard/prestataire_detail.html', {
        'active_menu': 'prestataires',
        'prestataire': prestataire,
        'services': services,
        'evaluations': evaluations,
        'paiements': paiements,
        'stats': stats
    })

@login_required
def annonces(request):
    annonces_list = Annonce.objects.all().order_by('-created_at')
    
    # Statistiques des annonces
    stats = {
        'total_annonces': annonces_list.count(),
        'annonces_actives': annonces_list.filter(status='active').count(),
        'annonces_en_cours': annonces_list.filter(status='en_cours').count(),
        'annonces_terminees': annonces_list.filter(status='terminee').count(),
    }
    
    return render(request, 'dashboard/annonces.html', {
        'active_menu': 'annonces',
        'annonces': annonces_list,
        'stats': stats
    })

@login_required
def annonce_detail(request, annonce_id):
    annonce = get_object_or_404(Annonce, id=annonce_id)
    livraisons = Livraison.objects.filter(annonce=annonce).order_by('-created_at')
    
    return render(request, 'dashboard/annonce_detail.html', {
        'active_menu': 'annonces',
        'annonce': annonce,
        'livraisons': livraisons
    })

@login_required
def services(request):
    services_list = Service.objects.all().order_by('-created_at')
    
    # Statistiques des services
    stats = {
        'total_services': services_list.count(),
        'services_disponibles': services_list.filter(disponible=True).count(),
    }
    
    return render(request, 'dashboard/services.html', {
        'active_menu': 'services',
        'services': services_list,
        'stats': stats
    })

@login_required
def service_detail(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    evaluations = Evaluation.objects.filter(service=service).order_by('-date_evaluation')
    
    # Statistiques du service
    stats = {
        'note_moyenne': evaluations.aggregate(Avg('note'))['note__avg'] or 0,
        'nombre_evaluations': evaluations.count(),
    }
    
    return render(request, 'dashboard/service_detail.html', {
        'active_menu': 'services',
        'service': service,
        'evaluations': evaluations,
        'stats': stats
    })

@login_required
def entrepots(request):
    entrepots_list = Entrepot.objects.all()
    
    # Statistiques des entrepôts
    stats = {
        'total_entrepots': entrepots_list.count(),
        'capacite_totale': entrepots_list.aggregate(Sum('capacite_totale'))['capacite_totale__sum'] or 0,
    }
    
    return render(request, 'dashboard/entrepots.html', {
        'active_menu': 'entrepots',
        'entrepots': entrepots_list,
        'stats': stats
    })

@login_required
def entrepot_detail(request, entrepot_id):
    entrepot = get_object_or_404(Entrepot, id=entrepot_id)
    boxes = BoxStockage.objects.filter(entrepot=entrepot)
    
    # Statistiques des boxes
    boxes_disponibles = boxes.filter(disponible=True).count()
    boxes_occupees = boxes.filter(disponible=False).count()
    
    return render(request, 'dashboard/entrepot_detail.html', {
        'active_menu': 'entrepots',
        'entrepot': entrepot,
        'boxes': boxes,
        'boxes_disponibles': boxes_disponibles,
        'boxes_occupees': boxes_occupees
    })

@login_required
def livraisons(request):
    livraisons_list = Livraison.objects.all().order_by('-created_at')
    
    # Statistiques des livraisons
    stats = {
        'total_livraisons': livraisons_list.count(),
        'livraisons_en_attente': livraisons_list.filter(status='en_attente').count(),
        'livraisons_en_cours': livraisons_list.filter(status='en_cours').count(),
        'livraisons_livrees': livraisons_list.filter(status='livree').count(),
        'livraisons_annulees': livraisons_list.filter(status='annulee').count(),
    }
    
    return render(request, 'dashboard/livraisons.html', {
        'active_menu': 'livraisons',
        'livraisons': livraisons_list,
        'stats': stats
    })

@login_required
def livraison_detail(request, livraison_id):
    livraison = get_object_or_404(Livraison, id=livraison_id)
    paiements = Paiement.objects.filter(livraison=livraison)
    
    return render(request, 'dashboard/livraison_detail.html', {
        'active_menu': 'livraisons',
        'livraison': livraison,
        'paiements': paiements
    })

@login_required
def notifications(request):
    # Récupérer toutes les notifications
    notifs = Notification.objects.all().order_by('-date_creation')
    
    # Marquer les notifications comme lues
    notifications_non_lues = notifs.filter(lue=False)
    for notif in notifications_non_lues:
        notif.lue = True
        notif.save()
    
    return render(request, 'dashboard/notifications.html', {
        'active_menu': 'notifications',
        'notifications': notifs
    })

@login_required
def paiements(request):
    paiements_list = Paiement.objects.all().order_by('-date_paiement')
    
    # Calcul des statistiques de paiements
    stats = {
        'total_paiements': paiements_list.count(),
        'paiements_reussis': paiements_list.filter(status='reussi').count(),
        'paiements_en_attente': paiements_list.filter(status='en_attente').count(),
        'paiements_echoues': paiements_list.filter(status='echoue').count(),
        'montant_total': paiements_list.filter(status='reussi').aggregate(Sum('montant'))['montant__sum'] or 0,
    }
    
    return render(request, 'dashboard/paiements.html', {
        'active_menu': 'paiements',
        'paiements': paiements_list,
        'stats': stats
    })

@login_required
def paiement_detail(request, paiement_id):
    paiement = get_object_or_404(Paiement, id=paiement_id)
    facture = Facture.objects.filter(paiement=paiement).first()
    
    return render(request, 'dashboard/paiement_detail.html', {
        'active_menu': 'paiements',
        'paiement': paiement,
        'facture': facture
    })

@login_required
def facturation(request):
    factures = Facture.objects.all().order_by('-date_emission')
    
    # Statistiques des factures
    stats = {
        'total_factures': factures.count(),
        'montant_total': factures.aggregate(Sum('montant_total'))['montant_total__sum'] or 0,
        'factures_payees': factures.filter(status_paiement='reussi').count(),
        'factures_en_attente': factures.filter(status_paiement='en_attente').count(),
    }
    
    return render(request, 'dashboard/facturation.html', {
        'active_menu': 'facturation',
        'factures': factures,
        'stats': stats
    })

@login_required
def abonnements(request):
    abonnements_list = Abonnement.objects.all().order_by('-date_debut')
    
    # Statistiques des abonnements
    stats = {
        'total_abonnements': abonnements_list.count(),
        'abonnements_actifs': abonnements_list.filter(actif=True).count(),
        'abonnements_free': abonnements_list.filter(type_abonnement='free').count(),
        'abonnements_starter': abonnements_list.filter(type_abonnement='starter').count(),
        'abonnements_premium': abonnements_list.filter(type_abonnement='premium').count(),
        'revenus_mensuels': abonnements_list.filter(actif=True).exclude(type_abonnement='free').aggregate(Sum('prix_mensuel'))['prix_mensuel__sum'] or 0,
    }
    
    return render(request, 'dashboard/abonnements.html', {
        'active_menu': 'abonnements',
        'abonnements': abonnements_list,
        'stats': stats
    })

@login_required
def contrats(request):
    contrats_list = Contrat.objects.all().order_by('-date_debut')
    
    # Statistiques des contrats
    stats = {
        'total_contrats': contrats_list.count(),
        'contrats_actifs': contrats_list.filter(status='actif').count(),
        'contrats_en_attente': contrats_list.filter(status='en_attente').count(),
        'contrats_expires': contrats_list.filter(status='expire').count(),
        'contrats_resilies': contrats_list.filter(status='resilie').count(),
    }
    
    return render(request, 'dashboard/contrats.html', {
        'active_menu': 'contrats',
        'contrats': contrats_list,
        'stats': stats
    })

@login_required
def statistiques(request):
    # Statistiques globales
    stats = {
        'total_users': User.objects.count(),
        'total_livreurs': Livreur.objects.count(),
        'total_commercants': Commercant.objects.count(),
        'total_clients': User.objects.filter(user_type='client').count(),
        'total_prestataires': Prestataire.objects.count(),
        'total_annonces': Annonce.objects.count(),
        'total_livraisons': Livraison.objects.count(),
        'total_services': Service.objects.count(),
        'total_paiements': Paiement.objects.filter(status='reussi').count(),
        'montant_total': Paiement.objects.filter(status='reussi').aggregate(Sum('montant'))['montant__sum'] or 0,
    }
    
    # Statistiques par mois (pour les graphiques)
    mois_actuel = timezone.now().month
    annee_actuelle = timezone.now().year
    
    # Données pour le graphique des revenus par mois
    revenus_mensuels = []
    for mois in range(1, 13):
        montant = Paiement.objects.filter(
            status='reussi',
            date_paiement__month=mois,
            date_paiement__year=annee_actuelle
        ).aggregate(Sum('montant'))['montant__sum'] or 0
        revenus_mensuels.append(montant)
    
    # Données pour le graphique des nouvelles inscriptions par mois
    inscriptions_mensuelles = []
    for mois in range(1, 13):
        count = User.objects.filter(
            date_joined__month=mois,
            date_joined__year=annee_actuelle
        ).count()
        inscriptions_mensuelles.append(count)
    
    return render(request, 'dashboard/statistiques.html', {
        'active_menu': 'statistiques',
        'stats': stats,
        'revenus_mensuels': revenus_mensuels,
        'inscriptions_mensuelles': inscriptions_mensuelles
    })

@login_required
def parametres(request):
    # Si l'utilisateur a soumis le formulaire
    if request.method == 'POST':
        # Traiter les paramètres ici
        messages.success(request, 'Les paramètres ont été mis à jour avec succès.')
        return redirect('dashboard:parametres')
    
    return render(request, 'dashboard/parametres.html', {'active_menu': 'parametres'})

@login_required
def support(request):
    return render(request, 'dashboard/support.html', {'active_menu': 'support'})

@login_required
def logs(request):
    logs_list = LogConnexion.objects.all().order_by('-date_connexion')
    
    return render(request, 'dashboard/logs.html', {
        'active_menu': 'logs',
        'logs': logs_list
    })

# Endpoint API pour obtenir le chiffre d'affaires mensuel
@api_view(['GET'])
@permission_classes([IsAdminUser])
def monthly_revenue(request):
    """Endpoint pour obtenir le chiffre d'affaires mensuel."""
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    
    if year and month:
        revenue = get_monthly_revenue(int(year), int(month))
    else:
        revenue = get_monthly_revenue()
    
    return Response({'revenue': revenue})

@login_required
def validation_livreurs(request):
    """Liste des demandes de validation en attente pour les livreurs."""
    # Vérifier que l'utilisateur est un administrateur
    if not request.user.is_superuser:
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette page.")
        return redirect('dashboard:home')
    
    # Récupérer les demandes de validation par statut
    demandes_en_attente = DemandeValidationLivreur.objects.filter(status='en_attente')
    demandes_en_examen = DemandeValidationLivreur.objects.filter(status='en_examen')
    demandes_validees = DemandeValidationLivreur.objects.filter(status='validee')
    demandes_refusees = DemandeValidationLivreur.objects.filter(status='refusee')
    
    # Statistiques des demandes
    stats = {
        'total_demandes': DemandeValidationLivreur.objects.count(),
        'en_attente': demandes_en_attente.count(),
        'en_examen': demandes_en_examen.count(),
        'validees': demandes_validees.count(),
        'refusees': demandes_refusees.count(),
    }
    
    return render(request, 'dashboard/validation_livreurs.html', {
        'active_menu': 'validation_livreurs',
        'demandes_en_attente': demandes_en_attente,
        'demandes_en_examen': demandes_en_examen,
        'demandes_validees': demandes_validees,
        'demandes_refusees': demandes_refusees,
        'stats': stats
    })

@login_required
def validation_livreur_detail(request, demande_id):
    """Détail d'une demande de validation de livreur avec possibilité de traitement."""
    # Vérifier que l'utilisateur est un administrateur
    if request.user.user_type != 'admin':
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette page.")
        return redirect('dashboard:home')
    
    demande = get_object_or_404(DemandeValidationLivreur, pk=demande_id)
    
    # Récupérer le profil livreur associé à la demande
    try:
        livreur = Livreur.objects.get(user=demande.user)
    except Livreur.DoesNotExist:
        livreur = None
    
    # Récupérer les pièces justificatives
    pieces = PieceJustificative.objects.filter(user=demande.user)
    
    # Préparer les documents pour l'affichage
    document_types = {
        'id_card': "Carte d'identité",
        'driving_license': "Permis de conduire",
        # Ajoutez d'autres types si nécessaire
    }
    
    documents_display = []
    for doc_type, doc_name in document_types.items():
        # Vérifier si la pièce existe
        piece = pieces.filter(type_piece=doc_type).first()
        
        documents_display.append({
            'nom': doc_name,
            'fourni': piece is not None,
            'document': piece
        })
    
    # Ajouter des logs pour le débogage
    print(f"Demande ID: {demande_id}, Livreur: {demande.user.username}")
    print(f"Pièces trouvées: {pieces.count()}")
    for piece in pieces:
        print(f"  - Type: {piece.type_piece}, Fichier: {piece.fichier}")
    print(f"Documents display: {documents_display}")
    
    return render(request, 'dashboard/validation_livreur_detail.html', {
        'active_menu': 'validation_livreurs',
        'demande': demande,
        'livreur': livreur,
        'pieces': pieces,
        'documents_display': documents_display
    })

@login_required
def soumettre_pieces_justificatives(request):
    """Vue permettant à un livreur de soumettre ses pièces justificatives."""
    # Vérifier si l'utilisateur est bien un livreur
    if request.user.user_type != 'livreur':
        messages.error(request, "Vous n'êtes pas autorisé à accéder à cette page.")
        return redirect('dashboard:home')
    
    # Récupérer ou créer une demande de validation
    demande, created = DemandeValidationLivreur.objects.get_or_create(
        user=request.user,
        defaults={'status': 'en_attente'}
    )
    
    # Si une demande a déjà été validée, afficher un message
    if demande.status == 'validee':
        messages.info(request, "Votre compte a déjà été validé.")
        return redirect('dashboard:home')
    
    # Récupérer les pièces déjà soumises
    pieces_soumises = PieceJustificative.objects.filter(
        user=request.user,
        demande_validation=demande
    )
    
    # Liste des types de pièces justificatives obligatoires
    pieces_obligatoires = {
        'id_card': 'Carte d\'identité',
        'driving_license': 'Permis de conduire'
    }
    
    # Vérifier quelles pièces ont déjà été soumises
    pieces_manquantes = {}
    for type_piece, nom in pieces_obligatoires.items():
        if not pieces_soumises.filter(type_piece=type_piece).exists():
            pieces_manquantes[type_piece] = nom
    
    if request.method == 'POST':
        type_piece = request.POST.get('type_piece')
        fichier = request.FILES.get('fichier')
        
        if not fichier:
            messages.error(request, "Veuillez sélectionner un fichier à télécharger.")
        elif not type_piece:
            messages.error(request, "Veuillez sélectionner le type de document.")
        else:
            # Vérifier si ce type de pièce existe déjà
            if pieces_soumises.filter(type_piece=type_piece).exists():
                messages.warning(request, f"Vous avez déjà soumis ce type de document. Il sera remplacé.")
                # Supprimer l'ancienne pièce
                pieces_soumises.filter(type_piece=type_piece).delete()
            
            # Créer la nouvelle pièce justificative
            piece = PieceJustificative.objects.create(
                user=request.user,
                type_piece=type_piece,
                fichier=fichier,
                demande_validation=demande
            )
            
            messages.success(request, f"Votre {piece.get_type_piece_display()} a été soumis avec succès.")
            return redirect('dashboard:soumettre_pieces_justificatives')
    
    return render(request, 'dashboard/soumettre_pieces.html', {
        'active_menu': 'validation',
        'demande': demande,
        'pieces_soumises': pieces_soumises,
        'pieces_manquantes': pieces_manquantes
    })
@login_required
def changer_statut_livreur(request):
    """Change le statut d'une demande de validation de livreur."""
    # Vérifier que l'utilisateur est un administrateur
    if request.user.user_type != 'admin' and not request.user.is_superuser:
        messages.error(request, "Vous n'êtes pas autorisé à effectuer cette action.")
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        livreur_id = request.POST.get('livreur_id')  # Le nom du champ dans le formulaire
        nouveau_statut = request.POST.get('nouveau_statut')
        
        # Récupérer la demande
        try:
            demande = DemandeValidationLivreur.objects.get(id=livreur_id)
            
            # Changer le statut selon la demande
            if nouveau_statut == 'en_examen':
                demande.en_examen(request.user)
                messages.info(request, f"La demande de {demande.user.username} a été mise en examen.")
            elif nouveau_statut == 'valide':
                demande.valider(request.user)
                messages.success(request, f"La demande de {demande.user.username} a été validée avec succès.")
            
            return redirect('dashboard:validation_livreurs')
        except DemandeValidationLivreur.DoesNotExist:
            messages.error(request, "Demande non trouvée.")
            return redirect('dashboard:validation_livreurs')
    
    return redirect('dashboard:validation_livreurs')

@login_required
def refuser_livreur(request):
    """Refuse une demande de validation de livreur."""
    # Vérifier que l'utilisateur est un administrateur
    if request.user.user_type != 'admin' and not request.user.is_superuser:
        messages.error(request, "Vous n'êtes pas autorisé à effectuer cette action.")
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        livreur_id = request.POST.get('livreur_id')
        motif = request.POST.get('motif')
        
        if not motif:
            messages.error(request, "Veuillez fournir un motif de refus.")
            return redirect('dashboard:validation_livreur_detail', demande_id=livreur_id)
        
        try:
            demande = DemandeValidationLivreur.objects.get(id=livreur_id)
            demande.refuser(request.user, motif)
            messages.warning(request, f"La demande de {demande.user.username} a été refusée.")
            return redirect('dashboard:validation_livreurs')
        except DemandeValidationLivreur.DoesNotExist:
            messages.error(request, "Demande non trouvée.")
            return redirect('dashboard:validation_livreurs')
    
    return redirect('dashboard:validation_livreurs')

@login_required
def valider_document(request, document_id):
    """Valide un document justificatif."""
    # Vérifier que l'utilisateur est un administrateur
    if request.user.user_type != 'admin' and not request.user.is_superuser:
        messages.error(request, "Vous n'êtes pas autorisé à effectuer cette action.")
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        try:
            document = PieceJustificative.objects.get(id=document_id)
            commentaire = request.POST.get('commentaire', '')
            document.valider(request.user, commentaire)
            messages.success(request, f"Le document {document.get_type_piece_display()} a été validé avec succès.")
            
            # Rediriger vers le détail du livreur associé à ce document
            demande = document.demande_validation
            if demande:
                return redirect('dashboard:validation_livreur_detail', demande_id=demande.id)
            else:
                return redirect('dashboard:validation_livreurs')
        except PieceJustificative.DoesNotExist:
            messages.error(request, "Document non trouvé.")
            return redirect('dashboard:validation_livreurs')
    
    return redirect('dashboard:validation_livreurs')
@login_required
def profil(request):
    """Affiche et gère le profil de l'utilisateur."""
    return render(request, 'dashboard/profil.html')

@login_required
def parametres(request):
    """Affiche et gère les paramètres du compte utilisateur."""
    return render(request, 'dashboard/parametres.html')
@login_required
def parametres_generaux(request):
    """Affiche et gère les paramètres généraux de l'application."""
    if request.method == 'POST':
        # Traiter les paramètres ici
        messages.success(request, 'Les paramètres généraux ont été mis à jour avec succès.')
        return redirect('dashboard:parametres_generaux')
    
    return render(request, 'dashboard/parametres_generaux.html', {'active_menu': 'parametres_generaux'})

@login_required
def parametres_tarifaires(request):
    """Affiche et gère les paramètres tarifaires de l'application."""
    if request.method == 'POST':
        # Traiter les paramètres ici
        messages.success(request, 'Les paramètres tarifaires ont été mis à jour avec succès.')
        return redirect('dashboard:parametres_tarifaires')
    
    return render(request, 'dashboard/parametres_tarifaires.html', {'active_menu': 'parametres_tarifaires'})

@login_required
def utilisateurs_admin(request):
    """Gestion des utilisateurs administrateurs."""
    # Récupérer tous les utilisateurs administrateurs
    admins = User.objects.filter(user_type='admin')
    
    if request.method == 'POST':
        # Traiter les actions sur les utilisateurs administrateurs
        # Par exemple, ajouter un nouvel administrateur
        messages.success(request, 'Les modifications ont été enregistrées avec succès.')
        return redirect('dashboard:utilisateurs_admin')
    
    return render(request, 'dashboard/utilisateurs_admin.html', {
        'active_menu': 'utilisateurs_admin',
        'admins': admins
    })
@login_required
def recherche_clients(request):
    """Recherche des clients selon les critères fournis."""
    nom = request.GET.get('nom', '')
    statut = request.GET.get('statut', '')
    abonnement = request.GET.get('abonnement', '')
    
    # Démarrer avec tous les clients
    clients_query = User.objects.filter(user_type='client')
    
    # Appliquer les filtres si fournis
    if nom:
        clients_query = clients_query.filter(
            Q(first_name__icontains=nom) | 
            Q(last_name__icontains=nom) | 
            Q(email__icontains=nom)
        )
    
    if statut == 'actif':
        clients_query = clients_query.filter(is_active=True)
    elif statut == 'inactif':
        clients_query = clients_query.filter(is_active=False)
    
    if abonnement:
        clients_query = clients_query.filter(abonnement__type_abonnement=abonnement, abonnement__actif=True)
    
    # Statistiques des clients filtrés
    stats = {
        'total_clients': clients_query.count(),
        'clients_avec_abonnement': Abonnement.objects.filter(
            user__in=clients_query, actif=True
        ).exclude(type_abonnement='free').count(),
    }
    
    return render(request, 'dashboard/clients.html', {
        'active_menu': 'clients',
        'clients': clients_query,
        'stats': stats,
        'search_params': {
            'nom': nom,
            'statut': statut,
            'abonnement': abonnement
        }
    })
@login_required
def rejeter_document(request, document_id):
    """Rejette un document justificatif."""
    # Vérifier que l'utilisateur est un administrateur
    if request.user.user_type != 'admin' and not request.user.is_superuser:
        messages.error(request, "Vous n'êtes pas autorisé à effectuer cette action.")
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        try:
            document = PieceJustificative.objects.get(id=document_id)
            raison = request.POST.get('raison', '')
            
            # La méthode valider n'existe pas pour rejeter, donc nous utilisons une approche manuelle
            document.validee = False
            document.commentaire_validation = raison
            document.date_validation = timezone.now()
            document.validee_par = request.user
            document.save()
            
            messages.warning(request, f"Le document {document.get_type_piece_display()} a été rejeté.")
            
            # Rediriger vers le détail du livreur associé à ce document
            demande = document.demande_validation
            if demande:
                return redirect('dashboard:validation_livreur_detail', demande_id=demande.id)
            else:
                return redirect('dashboard:validation_livreurs')
        except PieceJustificative.DoesNotExist:
            messages.error(request, "Document non trouvé.")
            return redirect('dashboard:validation_livreurs')
    
    return redirect('dashboard:validation_livreurs')