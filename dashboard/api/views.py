from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db.models import Sum, Count, Q
from django.utils import timezone
import datetime
# Ajoutez ces imports nécessaires
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from dashboard.models import User, Livreur, DemandeValidationLivreur, PieceJustificative, Livraison, Paiement, Annonce, Contrat, Service
from .serializers import (
    UserSerializer, LivraisonSerializer, AnnonceSerializer, PaiementSerializer,
    ContratSerializer, ServiceSerializer, PieceJustificativeSerializer
)
from dashboard.services.stats_service import get_monthly_revenue


from .serializers import MessageSerializer
from dashboard.models import Message
from rest_framework.exceptions import ValidationError
from rest_framework import status as drf_status



class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        receiver = self.request.query_params.get('receiver')
        annonce = self.request.query_params.get('annonce')
        if receiver:
            queryset = queryset.filter(receiver=receiver)
        if annonce:
            queryset = queryset.filter(annonce=annonce)
        return queryset

# puis le reste de votre code...
class RegisterLivreurView(APIView):
    """
    Vue API spécifique pour l'inscription des livreurs avec upload de documents.
    """
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)
    
    @transaction.atomic
    def post(self, request, format=None):
        """
        Gère l'inscription d'un livreur avec téléchargement des pièces justificatives.
        """
        # Log des données reçues pour le débogage
        print("DATA:", request.data)
        print("FILES:", request.FILES)
        for key, file_obj in request.FILES.items():
            print(f"  - {key}: {file_obj.name} ({file_obj.size} bytes)")
        
        # Vérifier les données minimales requises
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if field not in request.data or not request.data[field]:
                return Response(
                    {"error": f"Le champ {field} est requis"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Créer un utilisateur de type livreur
        user_data = {
            'username': request.data.get('username'),
            'email': request.data.get('email'),
            'first_name': request.data.get('first_name'),
            'last_name': request.data.get('last_name'),
            'phone': request.data.get('phone', ''),
            'address': request.data.get('address', ''),
            'user_type': 'livreur',  # Forcer le type livreur
        }
        
        # Vérifier que le nom d'utilisateur et l'email sont uniques
        if User.objects.filter(username=user_data['username']).exists():
            return Response(
                {"error": "Ce nom d'utilisateur est déjà utilisé"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(email=user_data['email']).exists():
            return Response(
                {"error": "Cet email est déjà utilisé"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Créer l'utilisateur
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                phone=user_data['phone'],
                address=user_data['address'],
                user_type='livreur',
                password=request.data.get('password')
            )
            
            # La création de l'utilisateur déclenche automatiquement la création
            # du profil livreur et de la demande de validation via le signal post_save
            # dans le modèle User. On récupère ces objets.
            
            try:
                livreur = Livreur.objects.get(user=user)
                demande = DemandeValidationLivreur.objects.get(user=user)
                
                # Traiter les pièces justificatives
                # 1. Carte d'identité
                if 'id_card' in request.FILES:
                    # Enregistrer dans le modèle Livreur
                    livreur.id_card = request.FILES['id_card']
                    
                    # Créer une entrée dans PieceJustificative
                    PieceJustificative.objects.create(
                        user=user,
                        type_piece='id_card',
                        fichier=request.FILES['id_card'],
                        demande_validation=demande
                    )
                    print(f"Carte d'identité enregistrée pour {user.username}")
                else:
                    print("Aucune carte d'identité fournie")
                
                # 2. Permis de conduire
                if 'driver_license' in request.FILES:
                    # Enregistrer dans le modèle Livreur
                    livreur.driving_license = request.FILES['driver_license']
                    
                    # Créer une entrée dans PieceJustificative
                    PieceJustificative.objects.create(
                        user=user,
                        type_piece='driving_license',
                        fichier=request.FILES['driver_license'],
                        demande_validation=demande
                    )
                    print(f"Permis de conduire enregistré pour {user.username}")
                else:
                    print("Aucun permis de conduire fourni")
                
                # Sauvegarder les modifications du livreur
                livreur.save()
                
            except (Livreur.DoesNotExist, DemandeValidationLivreur.DoesNotExist) as e:
                print(f"Erreur lors de la récupération du livreur ou de la demande: {e}")
                user.delete()  # Supprimer l'utilisateur pour éviter des problèmes
                return Response(
                    {"error": "Erreur lors de la création du profil livreur"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Créer un token d'authentification
            token, _ = Token.objects.get_or_create(user=user)
            
            # Retourner les informations de l'utilisateur créé
            return Response({
                'token': token.key,
                'user_id': user.id,
                'user_type': user.user_type,
                'username': user.username,
                'message': 'Inscription réussie. Vos documents sont en cours de vérification.'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # En cas d'erreur, supprimer l'utilisateur s'il a été créé
            if 'user' in locals():
                user.delete()
            
            print(f"Erreur lors de l'inscription: {e}")
            return Response(
                {"error": f"Erreur lors de l'inscription: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
from dashboard.models import User, Livraison, Paiement, Annonce, Contrat, Service, PieceJustificative
from .serializers import (
    UserSerializer, LivraisonSerializer, AnnonceSerializer, PaiementSerializer,
    ContratSerializer, ServiceSerializer, PieceJustificativeSerializer
)
from dashboard.services.stats_service import get_monthly_revenue

# ViewSets de base
class UserViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les opérations CRUD sur les utilisateurs."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

class LivraisonViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les opérations CRUD sur les livraisons."""
    queryset = Livraison.objects.all()
    serializer_class = LivraisonSerializer
    permission_classes = [permissions.IsAuthenticated]    #J'ai ajouté permissions.
    
    def perform_create(self, serializer):
       livreur = self.request.user
       annonce = serializer.validated_data.get('annonce')

       # Empêche les doublons (même livreur, même annonce)
       if Livraison.objects.filter(livreur=livreur, annonce=annonce).exists():
           raise ValidationError("Vous vous êtes déjà proposé sur cette annonce.")

       serializer.save(livreur=livreur)     #Ajouter By Oceane
    
    def get_queryset(self):
        """Filtrer les livraisons selon le type d'utilisateur."""
        user = self.request.user
        if user.user_type == 'admin':
            return Livraison.objects.all()
        elif user.user_type == 'livreur':
            return Livraison.objects.filter(livreur=user)
        elif user.user_type == 'client':
            return Livraison.objects.filter(client=user)
        return Livraison.objects.all()  # pour test seulement
    
    @action(detail=True, methods=['post'])
    def valider(self, request, pk=None):
        livraison = self.get_object()
        annonce_id = livraison.annonce.id

        # 1. Marquer cette livraison comme "en_cours"
        livraison.status = "en_cours"
        livraison.save()

        # 2. Annuler les autres livraisons associées à cette annonce
        Livraison.objects.filter(annonce_id=annonce_id).exclude(pk=livraison.pk).update(status="annulee")

        return Response({'message': 'Livreur validé.'}, status=drf_status.HTTP_200_OK)


class AnnonceViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les opérations CRUD sur les annonces."""
    queryset = Annonce.objects.all().order_by('-created_at')
    serializer_class = AnnonceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        """Associe l'utilisateur connecté à l'annonce lors de sa création."""
        serializer.save(created_by=self.request.user)
        
    def perform_update(self, serializer):         # Ajouter by Oceane
        annonce = serializer.save()

        # Synchroniser les dates dans toutes les livraisons liées
        Livraison.objects.filter(annonce=annonce).update(
            date_prise_en_charge=annonce.date_depart,
            date_livraison_prevue=annonce.date_arrivee
        )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_annonces(self, request):
        """Endpoint pour obtenir les annonces de l'utilisateur connecté."""
        annonces = Annonce.objects.filter(created_by=request.user).order_by('-created_at')
        serializer = self.get_serializer(annonces, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def available(self, request):
        """Endpoint pour obtenir les annonces disponibles pour les livreurs."""
        if request.user.user_type != 'livreur':
            return Response({"error": "Accès non autorisé"}, status=status.HTTP_403_FORBIDDEN)
        
        annonces = Annonce.objects.filter(status='active').order_by('-created_at')
        serializer = self.get_serializer(annonces, many=True)
        return Response(serializer.data)

# ViewSets spécifiques par type d'utilisateur
class LivreurLivraisonsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet dédié aux livraisons des livreurs."""
    serializer_class = LivraisonSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Ne retourne que les livraisons assignées au livreur connecté."""
        user = self.request.user
        if user.user_type != 'livreur':
            return Livraison.objects.none()
        return Livraison.objects.filter(livreur=user).order_by('-created_at')

class ClientAnnoncesViewSet(viewsets.ModelViewSet):
    """ViewSet dédié aux annonces des clients."""
    serializer_class = AnnonceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Ne retourne que les annonces créées par le client connecté."""
        user = self.request.user
        if user.user_type != 'client':
            return Annonce.objects.none()
        return Annonce.objects.filter(created_by=user).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Associe le client connecté à l'annonce lors de sa création."""
        serializer.save(created_by=self.request.user)

class CommercantContratsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet dédié aux contrats des commerçants."""
    serializer_class = ContratSerializer  # Assurez-vous que ce serializer existe
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Ne retourne que les contrats liés au commerçant connecté."""
        user = self.request.user
        if user.user_type != 'commercant':
            return Contrat.objects.none()
        return Contrat.objects.filter(commercant=user).order_by('-created_at')

class PrestataireServicesViewSet(viewsets.ModelViewSet):
    """ViewSet dédié aux services des prestataires."""
    serializer_class = ServiceSerializer  # Assurez-vous que ce serializer existe
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Ne retourne que les services proposés par le prestataire connecté."""
        user = self.request.user
        if user.user_type != 'prestataire':
            return Service.objects.none()
        return Service.objects.filter(prestataire=user).order_by('-created_at')
    
    def perform_create(self, serializer):
        """Associe le prestataire connecté au service lors de sa création."""
        serializer.save(prestataire=self.request.user)

# ViewSets d'administration
class AdminUserViewSet(viewsets.ModelViewSet):
    """ViewSet pour l'administration des utilisateurs."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

class AdminLivraisonViewSet(viewsets.ModelViewSet):
    """ViewSet pour l'administration des livraisons."""
    queryset = Livraison.objects.all()
    serializer_class = LivraisonSerializer
    permission_classes = [IsAdminUser]

class AdminValidationLivreurViewSet(viewsets.ModelViewSet):
    """ViewSet pour la validation des livreurs par les administrateurs."""
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        """Ne retourne que les utilisateurs de type livreur en attente de validation."""
        return User.objects.filter(user_type='livreur', is_active=False)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approuver un livreur."""
        livreur = self.get_object()
        livreur.is_active = True
        livreur.save()
        return Response({"message": "Livreur approuvé avec succès"})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Rejeter un livreur."""
        livreur = self.get_object()
        # Vous pouvez ajouter ici une logique pour envoyer un email de rejet
        return Response({"message": "Livreur rejeté"})

class AdminPieceJustificativeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour consulter les pièces justificatives (admin uniquement)."""
    serializer_class = PieceJustificativeSerializer
    permission_classes = [IsAdminUser]
    queryset = PieceJustificative.objects.all()

# Vues API statistiques et rapports
@api_view(['GET'])
@permission_classes([IsAdminUser])
def monthly_revenue(request):
    """Endpoint pour obtenir le chiffre d'affaires mensuel."""
    year = request.query_params.get('year')
    month = request.query_params.get('month')
    
    try:
        if year and month:
            revenue = get_monthly_revenue(int(year), int(month))
        else:
            revenue = get_monthly_revenue()
        
        return Response({'revenue': revenue})
    except ValueError:
        return Response(
            {"error": "Les paramètres year et month doivent être des nombres valides"}, 
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_dashboard_stats(request):
    """Statistiques pour le tableau de bord administrateur."""
    current_date = timezone.now()
    
    # Statistiques des utilisateurs
    total_users = User.objects.count()
    total_livreurs = User.objects.filter(user_type='livreur').count()
    total_clients = User.objects.filter(user_type='client').count()
    
    # Statistiques des livraisons
    total_livraisons = Livraison.objects.count()
    livraisons_en_cours = Livraison.objects.filter(status='en_cours').count()
    livraisons_completees = Livraison.objects.filter(status='complete').count()
    
    # Statistiques financières
    today = timezone.now().date()
    first_day_of_month = today.replace(day=1)
    revenue_this_month = Paiement.objects.filter(
        date__gte=first_day_of_month
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    return Response({
        'utilisateurs': {
            'total': total_users,
            'livreurs': total_livreurs,
            'clients': total_clients
        },
        'livraisons': {
            'total': total_livraisons,
            'en_cours': livraisons_en_cours,
            'completees': livraisons_completees
        },
        'finances': {
            'revenue_ce_mois': revenue_this_month
        }
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_monthly_financial_report(request, year):
    """Rapport financier mensuel pour une année spécifique."""
    # Vérifier que l'année est valide
    current_year = timezone.now().year
    if year < 2020 or year > current_year:
        return Response(
            {"error": f"L'année doit être comprise entre 2020 et {current_year}"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Récupérer les revenus pour chaque mois de l'année
    monthly_revenues = []
    for month in range(1, 13):
        start_date = datetime.date(year, month, 1)
        if month < 12:
            end_date = datetime.date(year, month + 1, 1)
        else:
            end_date = datetime.date(year + 1, 1, 1)
        
        revenue = Paiement.objects.filter(
            date__gte=start_date, 
            date__lt=end_date
        ).aggregate(total=Sum('montant'))['total'] or 0
        
        monthly_revenues.append({
            'mois': month,
            'revenue': revenue
        })
    
    return Response(monthly_revenues)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_yearly_financial_report(request):
    """Rapport financier annuel."""
    # Récupérer les années pour lesquelles nous avons des paiements
    first_payment = Paiement.objects.order_by('date').first()
    
    if not first_payment:
        return Response([])
    
    start_year = first_payment.date.year
    current_year = timezone.now().year
    
    yearly_revenues = []
    for year in range(start_year, current_year + 1):
        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year + 1, 1, 1)
        
        revenue = Paiement.objects.filter(
            date__gte=start_date, 
            date__lt=end_date
        ).aggregate(total=Sum('montant'))['total'] or 0
        
        yearly_revenues.append({
            'annee': year,
            'revenue': revenue
        })
    
    return Response(yearly_revenues)

# Vues API pour l'authentification
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Endpoint pour l'inscription d'un nouvel utilisateur."""
    # Vérifier si le mot de passe est présent
    if 'password' not in request.data or not request.data['password']:
        return Response(
            {"error": "Le mot de passe est requis"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        # Créer l'utilisateur avec le mot de passe correctement haché
        user = serializer.save()
        user.set_password(request.data['password'])
        user.save()
        
        # Créer un token d'authentification
        token, _ = Token.objects.get_or_create(user=user)
        
        # Retourner les informations de l'utilisateur créé
        return Response({
            'token': token.key,
            'user_id': user.id,
            'user_type': user.user_type,
            'username': user.username
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Endpoint pour la connexion d'un utilisateur."""
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    
    # Vérifier que les informations de connexion sont fournies
    if not password:
        return Response(
            {"error": "Le mot de passe est requis"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not username and not email:
        return Response(
            {"error": "Le nom d'utilisateur ou l'email est requis"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Gestion de l'authentification par email
    if email and not username:
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            return Response(
                {"error": "Aucun utilisateur trouvé avec cet email"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
    # Si username contient un @ mais que email n'est pas fourni, supposer que c'est un email
    elif username and '@' in username and not email:
        try:
            user_obj = User.objects.get(email=username)
            username = user_obj.username
        except User.DoesNotExist:
            pass
    
    # Authentifier l'utilisateur
    user = authenticate(username=username, password=password)
    
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'user_type': user.user_type,
            'username': user.username
        })
    
    return Response({"error": "Identifiants invalides"}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Endpoint pour la déconnexion d'un utilisateur."""
    try:
        # Supprimer le token d'authentification
        request.user.auth_token.delete()
        return Response({"message": "Déconnexion réussie"})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Endpoint pour obtenir le profil de l'utilisateur connecté."""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def test_connection(request):
    """Endpoint simple pour tester la connexion à l'API."""
    return Response({
        "status": "success",
        "message": "Connexion à l'API réussie",
        "api_version": "1.0"
    })