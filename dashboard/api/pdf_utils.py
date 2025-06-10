from io import BytesIO
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from django.conf import settings
import os

def generate_invoice_pdf(facture):
    """Génère un PDF de facture"""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Titre
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, f"FACTURE N° {facture.reference}")
    
    # Infos société
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 80, "EcoDeli")
    p.drawString(50, height - 95, "110, rue de Flandre")
    p.drawString(50, height - 110, "75019 Paris")
    
    # Infos client
    p.drawString(350, height - 80, f"Client: {facture.paiement.payeur.get_full_name()}")
    p.drawString(350, height - 95, f"Email: {facture.paiement.payeur.email}")
    
    # Date
    p.drawString(50, height - 140, f"Date d'émission: {facture.date_emission.strftime('%d/%m/%Y')}")
    
    # Tableau des détails
    data = [
        ["Description", "Quantité", "Prix unitaire", "Total"],
        [
            f"Livraison {facture.paiement.livraison.reference}",
            "1",
            f"{facture.paiement.montant}€",
            f"{facture.paiement.montant}€"
        ],
    ]
    
    table = Table(data, colWidths=[200, 100, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (3, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (3, 0), colors.white),
        ('ALIGN', (0, 0), (3, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (3, 0), 12),
        ('BACKGROUND', (0, 1), (3, 1), colors.white),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    table.wrapOn(p, width, height)
    table.drawOn(p, 50, height - 230)
    
    # Total
    p.setFont("Helvetica-Bold", 14)
    p.drawString(350, height - 260, f"Total: {facture.paiement.montant}€")
    
    # Pied de page
    p.setFont("Helvetica", 10)
    p.drawString(50, 50, "EcoDeli - SIRET: 123456789 - TVA: FR123456789")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer

def save_invoice_pdf(facture):
    """Enregistre le PDF de facture dans le système de fichiers"""
    buffer = generate_invoice_pdf(facture)
    
    # Créer le chemin du fichier
    filename = f"facture_{facture.reference}.pdf"
    filepath = os.path.join(settings.MEDIA_ROOT, 'factures', filename)
    
    # Assurez-vous que le répertoire existe
    os.makedirs(os.path.join(settings.MEDIA_ROOT, 'factures'), exist_ok=True)
    
    # Enregistrez le fichier
    with open(filepath, 'wb') as f:
        f.write(buffer.read())
    
    # Mettez à jour le chemin du fichier dans l'instance de facture
    facture.pdf_file.name = os.path.join('factures', filename)
    facture.save()
    
    return facture.pdf_file.url