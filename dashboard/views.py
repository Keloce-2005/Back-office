from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from django.contrib import messages

from .models import (
    User, Livreur, Commercant, Prestataire, Annonce, Livraison, 
    Paiement, Facture, Service, Entrepot, BoxStockage, Abonnement,
    Notification, Evaluation, PieceJustificative, Contrat, LogConnexion
)

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