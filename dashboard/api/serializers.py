# api/serializers.py
from rest_framework import serializers
from dashboard.models import User, Annonce, Livraison, Commercant, Prestataire, Livreur, Paiement, Message


#By Oceane
class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'user_type', 'phone', 'address', 'date_naissance', 'pays']
        extra_kwargs = {
            'password': {'write_only': True}       #By Oceane
        }

class AnnonceSerializer(serializers.ModelSerializer):
    created_by_username = serializers.SerializerMethodField()
    
    class Meta:
        model = Annonce
        fields = ['id', 'titre', 'description', 'depart', 'arrivee',
                  'date_depart', 'date_arrivee', 'prix', 'status',
                  'type_annonce', 'poids', 'dimensions', 'created_at',
                  'updated_at', 'est_urgente', 'vues', 'created_by',
                  'created_by_username']
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'vues']
    
    def get_created_by_username(self, obj):
        return obj.created_by.username if obj.created_by else None

class LivraisonSerializer(serializers.ModelSerializer):
    # Permet d’envoyer juste l’ID lors du POST, et l’objet complet lors du GET
    annonce = serializers.PrimaryKeyRelatedField(queryset=Annonce.objects.all(), write_only=True)
    annonce_details = AnnonceSerializer(source='annonce', read_only=True)
    livreur_username = serializers.SerializerMethodField()              # Ajouter by Oceane

    class Meta:
        model = Livraison
        fields = [
            'id', 'reference', 'annonce', 'annonce_details', 'livreur', 'client',
            'description_colis', 'poids', 'dimensions',
            'date_prise_en_charge', 'date_livraison_prevue',
            'date_livraison_reelle', 'status', 'created_at', 'updated_at', 'livreur_username'
        ]
        read_only_fields = ['reference', 'code_validation', 'created_at', 'updated_at']

    def create(self, validated_data):
        if 'livreur' not in validated_data:
            validated_data['livreur'] = self.context['request'].user
        return super().create(validated_data)
    
    def get_livreur_username(self, obj):     # Ajouter by Oceane
        return obj.livreur.username if obj.livreur else None


class LivreurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Livreur
        fields = ['user', 'verified', 'rating', 'vehicle_type', 'disponible',
                 'zones_livraison', 'nombre_livraisons']
        read_only_fields = ['verified', 'rating', 'nombre_livraisons']

class CommercantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commercant
        fields = ['user', 'company_name', 'siret', 'company_address',
                 'contract_signed', 'contract_start_date', 'contract_end_date',
                 'contract_type', 'taux_commission']
        read_only_fields = ['contract_signed', 'taux_commission']

class PrestataireSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prestataire
        fields = ['user', 'specialites', 'tarif_horaire', 'disponible',
                 'verified', 'rating', 'certifications', 'nombre_services']
        read_only_fields = ['verified', 'rating', 'nombre_services']
        
        

# Ajout du serializer manquant pour Paiement
class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = '__all__'
        read_only_fields = ['date', 'reference_transaction']

# Serializers pour les modèles manquants (à implémenter lorsque les modèles seront créés)
try:
    from dashboard.models import Contrat, Service, PieceJustificative
    
    class ContratSerializer(serializers.ModelSerializer):
        class Meta:
            model = Contrat
            fields = '__all__'
            read_only_fields = ['created_at', 'updated_at']
    
    class ServiceSerializer(serializers.ModelSerializer):
        class Meta:
            model = Service
            fields = '__all__'
            read_only_fields = ['created_at', 'updated_at']
    
    class PieceJustificativeSerializer(serializers.ModelSerializer):
        class Meta:
            model = PieceJustificative
            fields = '__all__'
            read_only_fields = ['uploaded_at']
            
except ImportError:
    # Ces modèles seront implémentés ultérieurement
    pass