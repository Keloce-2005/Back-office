# dashboard/services/stats_service.py

from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from dashboard.models import Livraison, User, Paiement, Annonce

def get_monthly_revenue(year=None, month=None):
    """Calcule le chiffre d'affaires du mois spécifié ou du mois en cours."""
    if not year:
        today = timezone.now()
        year = today.year
        month = today.month
    
    # Revenus totaux du mois (paiements réussis)
    revenue = Paiement.objects.filter(
        status='reussi',
        date_paiement__year=year,
        date_paiement__month=month
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    return revenue

def get_livreur_stats(livreur_id, period=30):
    """Obtient les statistiques d'un livreur sur la période spécifiée (en jours)."""
    livreur = User.objects.get(id=livreur_id, user_type='livreur')
    
    # Date de début pour la période
    start_date = timezone.now() - timedelta(days=period)
    
    # Nombre de livraisons effectuées
    livraisons_count = Livraison.objects.filter(
        livreur=livreur,
        date_livraison_reelle__gte=start_date,
        status='livree'
    ).count()
    
    # Revenus générés
    revenus = Paiement.objects.filter(
        beneficiaire=livreur,
        status='reussi',
        date_paiement__gte=start_date
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    # Note moyenne
    rating_avg = livreur.evaluations_recues.filter(
        date_evaluation__gte=start_date
    ).aggregate(avg=Avg('note'))['avg'] or 0
    
    return {
        'livraisons_count': livraisons_count,
        'revenus': revenus,
        'rating_avg': rating_avg,
        'period_days': period
    }

def get_client_membership_stats(client_id):
    """Obtient des statistiques sur l'adhésion et l'activité d'un client."""
    client = User.objects.get(id=client_id, user_type='client')
    
    # Date d'inscription
    date_inscription = client.date_joined
    
    # Durée d'adhésion en jours
    days_since_signup = (timezone.now() - date_inscription).days
    
    # Nombre de commandes passées
    commandes_count = Livraison.objects.filter(client=client).count()
    
    # Montant total dépensé
    total_spent = Paiement.objects.filter(
        payeur=client,
        status='reussi'
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    # Type d'abonnement actuel
    current_subscription = client.abonnements.filter(actif=True).first()
    
    return {
        'date_inscription': date_inscription,
        'days_since_signup': days_since_signup,
        'commandes_count': commandes_count,
        'total_spent': total_spent,
        'current_subscription': current_subscription
    }

def get_platform_stats(days=30):
    """Obtient des statistiques globales de la plateforme."""
    start_date = timezone.now() - timedelta(days=days)
    
    # Nombre total d'utilisateurs inscrits
    users_count = User.objects.filter(date_joined__gte=start_date).count()
    
    # Répartition par type d'utilisateur
    user_types = User.objects.filter(date_joined__gte=start_date).values('user_type').annotate(count=Count('id'))
    
    # Nombre de livraisons effectuées
    livraisons_count = Livraison.objects.filter(date_livraison_reelle__gte=start_date, status='livree').count()
    
    # Chiffre d'affaires total
    revenue = Paiement.objects.filter(status='reussi', date_paiement__gte=start_date).aggregate(total=Sum('montant'))['total'] or 0
    
    # Nombre d'annonces créées
    annonces_count = Annonce.objects.filter(created_at__gte=start_date).count()
    
    return {
        'users_count': users_count,
        'user_types': user_types,
        'livraisons_count': livraisons_count,
        'revenue': revenue,
        'annonces_count': annonces_count,
        'period_days': days
    }

def get_top_livreurs(limit=5, period=30):
    """Obtient les meilleurs livreurs en fonction du nombre de livraisons."""
    start_date = timezone.now() - timedelta(days=period)
    
    top_livreurs = Livraison.objects.filter(
        date_livraison_reelle__gte=start_date,
        status='livree'
    ).values('livreur').annotate(
        count=Count('id')
    ).order_by('-count')[:limit]
    
    # Enrichir les données
    result = []
    for item in top_livreurs:
        livreur = User.objects.get(id=item['livreur'])
        result.append({
            'livreur_id': livreur.id,
            'nom': livreur.username,
            'livraisons_count': item['count'],
            'rating': livreur.livreur_profile.rating if hasattr(livreur, 'livreur_profile') else 0
        })
    
    return result

def get_top_clients(limit=5, period=30):
    """Obtient les meilleurs clients en fonction du montant dépensé."""
    start_date = timezone.now() - timedelta(days=period)
    
    top_clients = Paiement.objects.filter(
        date_paiement__gte=start_date,
        status='reussi'
    ).values('payeur').annotate(
        total=Sum('montant')
    ).order_by('-total')[:limit]
    
    # Enrichir les données
    result = []
    for item in top_clients:
        client = User.objects.get(id=item['payeur'])
        result.append({
            'client_id': client.id,
            'nom': client.username,
            'montant_total': item['total'],
            'commandes_count': Livraison.objects.filter(client=client, date_livraison_reelle__gte=start_date).count()
        })
    
    return result