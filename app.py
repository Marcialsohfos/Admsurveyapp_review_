"""
DocAdminApp AI - Application de numérisation intelligente de documents
Extraction et conversion de données administratives (PDF scannés, images, etc.)
"""

import streamlit as st
import pandas as pd
import os
import tempfile
import time
from pathlib import Path
import base64
from io import BytesIO
from datetime import datetime, timedelta
import hashlib

# Ajout après les imports existants
from utils.file_handler import get_file_handler, display_file_stats, cleanup_session_files

# ============================================
# 🔐 CONFIGURATION DE SÉCURITÉ - CLÉ D'ACCÈS
# ============================================

# Clé de sécurité unique
SECRET_KEY = "32015labmath@docadmnsurvey"

# Configuration de l'authentification
AUTH_CONFIG = {
    'session_duration_hours': 8,      # Durée de session en heures
    'max_login_attempts': 3,           # Tentatives max avant blocage
    'block_duration_minutes': 15,      # Durée de blocage après trop de tentatives
    'require_auth': True               # Activer/désactiver l'authentification
}

def hash_password(password: str) -> str:
    """Hash le mot de passe pour la vérification"""
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(password: str) -> bool:
    """Vérifie si le mot de passe est correct"""
    return password == SECRET_KEY

def init_auth_session():
    """Initialise les variables de session pour l'authentification"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'login_attempts' not in st.session_state:
        st.session_state.login_attempts = 0
    if 'blocked_until' not in st.session_state:
        st.session_state.blocked_until = None
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None

def is_blocked() -> bool:
    """Vérifie si l'utilisateur est actuellement bloqué"""
    if st.session_state.blocked_until:
        if datetime.now() < st.session_state.blocked_until:
            remaining = (st.session_state.blocked_until - datetime.now()).seconds // 60
            st.error(f"🔒 Trop de tentatives. Réessayez dans {remaining} minutes.")
            return True
        else:
            # Réinitialiser le blocage
            st.session_state.blocked_until = None
            st.session_state.login_attempts = 0
    return False

def login_page():
    """Affiche la page de connexion"""
    
    # CSS pour la page de connexion
    st.markdown("""
    <style>
    .login-container {
        max-width: 450px;
        margin: 0 auto;
        padding: 2rem;
        background: white;
        border-radius: 15px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        text-align: center;
    }
    .login-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .login-header h1 {
        color: white;
        margin: 0;
        font-size: 2rem;
    }
    .login-header p {
        color: rgba(255,255,255,0.9);
        margin-top: 0.5rem;
    }
    .security-badge {
        background-color: #e8f5e9;
        padding: 0.5rem;
        border-radius: 5px;
        margin-top: 1rem;
        font-size: 0.8rem;
        color: #2e7d32;
    }
    .key-info {
        background-color: #fff3e0;
        padding: 0.8rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-size: 0.85rem;
        color: #e65100;
        border-left: 3px solid #ff9800;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # En-tête
    st.markdown("""
    <div class="login-header">
        <h1>📄 DocAdminApp AI</h1>
        <p>Extraction intelligente de données administratives</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Formulaire de connexion
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        st.markdown("### 🔐 Accès sécurisé")
        st.markdown("Veuillez entrer votre clé d'accès pour continuer")
        
        # Afficher le nombre de tentatives restantes
        remaining_attempts = AUTH_CONFIG['max_login_attempts'] - st.session_state.login_attempts
        if remaining_attempts > 0 and st.session_state.login_attempts > 0:
            st.warning(f"⚠️ Tentatives restantes: {remaining_attempts}")
        
        # Information sur la clé
        st.markdown("""
        <div class="key-info">
            🔑 Une clé d'accès vous a été fournie par l'administrateur.<br>
            Contactez <strong>Lab_Math & Label CIE</strong> pour obtenir votre clé.
        </div>
        """, unsafe_allow_html=True)
        
        # Champ de mot de passe
        password = st.text_input(
            "Clé d'accès",
            type="password",
            placeholder="Entrez votre clé de sécurité",
            key="login_password",
            help="Contactez l'administrateur pour obtenir la clé d'accès"
        )
        
        # Bouton de connexion
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔓 Se connecter", use_container_width=True):
                if is_blocked():
                    pass
                elif not password:
                    st.error("Veuillez entrer la clé d'accès")
                elif check_credentials(password):
                    st.session_state.authenticated = True
                    st.session_state.login_time = datetime.now()
                    st.session_state.login_attempts = 0
                    st.success("✅ Connexion réussie ! Redirection...")
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    remaining = AUTH_CONFIG['max_login_attempts'] - st.session_state.login_attempts
                    
                    if st.session_state.login_attempts >= AUTH_CONFIG['max_login_attempts']:
                        st.session_state.blocked_until = datetime.now() + timedelta(minutes=AUTH_CONFIG['block_duration_minutes'])
                        st.error(f"🔒 Trop de tentatives. Compte bloqué pour {AUTH_CONFIG['block_duration_minutes']} minutes.")
                    else:
                        st.error(f"❌ Clé incorrecte. Plus que {remaining} tentative(s).")
        
        # Informations de sécurité
        st.markdown("---")
        st.markdown("""
        <div class="security-badge">
            🔒 Connexion sécurisée | Données chiffrées | Session limitée à 8h
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: gray; font-size: 0.8rem;'>DocAdminApp AI - Tous droits réservés © 2024 | Lab_Math & Label CIE</p>",
        unsafe_allow_html=True
    )

def check_session_validity():
    """Vérifie si la session est encore valide"""
    if st.session_state.login_time:
        session_age = datetime.now() - st.session_state.login_time
        if session_age > timedelta(hours=AUTH_CONFIG['session_duration_hours']):
            st.session_state.authenticated = False
            st.session_state.login_time = None
            st.warning("⏰ Session expirée. Veuillez vous reconnecter.")
            st.rerun()

def logout():
    """Déconnecte l'utilisateur"""
    st.session_state.authenticated = False
    st.session_state.login_time = None
    st.session_state.login_attempts = 0
    st.session_state.blocked_until = None
    st.success("🔓 Déconnecté avec succès")
    st.rerun()

# Initialiser l'authentification
init_auth_session()

# Vérifier la session si authentifié
if st.session_state.authenticated:
    check_session_validity()

# ============================================
# FIN DE LA CONFIGURATION DE SÉCURITÉ
# ============================================

# Configuration de la page
st.set_page_config(
    page_title="DocAdminApp AI - Extraction intelligente de documents",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import des modules personnalisés
from utils.ocr_processor import OCRProcessor
from utils.data_converter import DataConverter
from utils.file_handler import FileHandler

# Styles CSS personnalisés
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
    }
    .main-header p {
        color: rgba(255,255,255,0.9);
        margin-top: 0.5rem;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    .info-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
    .stButton > button {
        background: linear-gradient(135deg, #2ecc71, #27ae60);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        font-size: 1rem;
        border-radius: 25px;
        transition: transform 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        background: linear-gradient(135deg, #27ae60, #229954);
    }
    .logout-btn {
        background: linear-gradient(135deg, #e74c3c, #c0392b) !important;
    }
    .logout-btn:hover {
        background: linear-gradient(135deg, #c0392b, #a93226) !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation des sessions
def init_session_state():
    """Initialise les variables de session"""
    if 'ocr_processor' not in st.session_state:
        st.session_state.ocr_processor = OCRProcessor()
    if 'data_converter' not in st.session_state:
        st.session_state.data_converter = DataConverter()
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'converted_file' not in st.session_state:
        st.session_state.converted_file = None
    if 'temp_files' not in st.session_state:
        st.session_state.temp_files = []  # Pour le nettoyage
    if 'file_handler' not in st.session_state:
        st.session_state.file_handler = get_file_handler()


# En-tête principal
def display_header():
    """Affiche l'en-tête de l'application"""
    st.markdown("""
    <div class="main-header">
        <h1>📄 DocAdminApp AI</h1>
        <p>Extraction intelligente de données administratives - Power by Lab_Math & Label CIE</p>
    </div>
    """, unsafe_allow_html=True)

# Sidebar avec informations
def display_sidebar():
    """Affiche la barre latérale"""
    with st.sidebar:
        st.markdown("## 🎯 À propos")
        st.info(
            "**DocAdminApp AI** permet d'extraire automatiquement des données "
            "de documents scannés (PDF, images) et de les convertir en formats "
            "exploitables (Excel, CSV, Stata, SPSS, etc.)"
        )
        
        st.markdown("## 📂 Formats supportés")
        st.markdown("""
        **Entrée :**
        - PDF (scannés et natifs)
        - PNG, JPG, JPEG
        - TIFF
        
        **Sortie :**
        - CSV / Excel
        - Stata (.dta)
        - SPSS (.sav)
        - JSON / XML / HTML
        - Word (.docx)
        """)
        
        st.markdown("## 🔧 Technologies")
        st.markdown("""
        - Tesseract OCR (Français + Anglais)
        - Traitement d'image avancé
        - Détection automatique du type de document
        - Conversion multi-formats
        """)
        
        st.markdown("---")
        
        # Informations de session
        if st.session_state.login_time:
            session_elapsed = datetime.now() - st.session_state.login_time
            hours_left = max(0, AUTH_CONFIG['session_duration_hours'] - session_elapsed.total_seconds() / 3600)
            st.caption(f"🕐 Session: {hours_left:.1f}h restantes")
        
        # Ajouter les statistiques
        display_file_stats()
        
        # Bouton de nettoyage
        st.markdown("---")
        if st.button("🧹 Nettoyer les fichiers temporaires", use_container_width=True):
            count = st.session_state.file_handler.clear_all_files()
            st.success(f"{count} fichiers supprimés")
            st.rerun()
        
        # Bouton de déconnexion
        st.markdown("---")
        if st.button("🚪 Se déconnecter", use_container_width=True, key="logout_btn"):
            logout()

# Configuration des paramètres
def display_configuration():
    """Affiche les paramètres de configuration"""
    col1, col2 = st.columns(2)
    
    with col1:
        data_type = st.selectbox(
            "📊 Type de document",
            options=[
                "auto", "budget", "laboratoire", "voirie",
                "formation", "legal", "administrative", "tabular"
            ],
            format_func=lambda x: {
                "auto": "🔍 Détection automatique",
                "budget": "💰 Budget d'investissement",
                "laboratoire": "🔬 Données laboratoires",
                "voirie": "🛣️ Voirie et réseaux",
                "formation": "📚 Documents de formation",
                "legal": "⚖️ Documents juridiques",
                "administrative": "📋 Documents administratifs",
                "tabular": "📊 Données tabulaires"
            }.get(x, x)
        )
    
    with col2:
        output_format = st.selectbox(
            "💾 Format de sortie",
            options=["csv", "xlsx", "dta", "sav", "json", "xml", "html", "docx", "txt"],
            format_func=lambda x: {
                "csv": "CSV", "xlsx": "Excel (.xlsx)", "dta": "Stata (.dta)",
                "sav": "SPSS (.sav)", "json": "JSON", "xml": "XML",
                "html": "HTML", "docx": "Word (.docx)", "txt": "Texte (.txt)"
            }.get(x, x.upper())
        )
    
    return data_type, output_format

# Upload de fichier
def display_upload():
    """Affiche la zone d'upload"""
    uploaded_file = st.file_uploader(
        "📁 Déposez votre fichier ici",
        type=['png', 'jpg', 'jpeg', 'pdf', 'tiff'],
        help="Formats supportés: PNG, JPG, JPEG, PDF, TIFF"
    )
    
    if uploaded_file:
        st.success(f"✅ Fichier chargé: {uploaded_file.name} ({(uploaded_file.size / 1024):.1f} KB)")
        
        # Aperçu selon le type
        if uploaded_file.type.startswith('image/'):
            st.image(uploaded_file, caption="Aperçu de l'image", use_container_width=True)
        elif uploaded_file.type == 'application/pdf':
            st.info("📄 Fichier PDF chargé - L'OCR sera appliqué si nécessaire")
    
    return uploaded_file

# Traitement du fichier
def process_file(uploaded_file, data_type, output_format):
    """Traite le fichier uploadé"""
    
    # Créer un fichier temporaire
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Barre de progression
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Étape 1: OCR
        status_text.text("🔍 Extraction OCR en cours...")
        progress_bar.progress(25)
        
        extracted_data = st.session_state.ocr_processor.process_file(tmp_path, data_type)
        
        progress_bar.progress(60)
        status_text.text("🔄 Conversion des données...")
        
        # Étape 2: Conversion
        output_filename = st.session_state.data_converter.convert_data(extracted_data, output_format)
        
        progress_bar.progress(90)
        status_text.text("✅ Finalisation...")
        
        time.sleep(0.5)
        progress_bar.progress(100)
        status_text.text("✅ Traitement terminé!")
        
        # Nettoyage
        progress_bar.empty()
        status_text.empty()
        
        return extracted_data, output_filename
        
    except Exception as e:
        st.error(f"❌ Erreur lors du traitement: {str(e)}")
        return None, None
    finally:
        # Nettoyer le fichier temporaire
        try:
            os.unlink(tmp_path)
        except:
            pass

# Affichage des résultats
def display_results(extracted_data, output_filename):
    """Affiche les résultats de l'extraction"""
    
    st.markdown("---")
    st.markdown("## 📊 Résultats de l'extraction")
    
    # Métadonnées
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Type détecté", extracted_data.get('detected_type', 'Inconnu').upper())
    with col2:
        st.metric("📝 Caractères extraits", extracted_data.get('text_length', 0))
    with col3:
        st.metric("📑 Lignes traitées", extracted_data.get('line_count', 0))
    
    # Aperçu du texte extrait
    with st.expander("📝 Aperçu du texte extrait", expanded=False):
        raw_text = extracted_data.get('raw_text', '')
        if raw_text:
            st.text_area("Texte brut", raw_text[:2000] + ("..." if len(raw_text) > 2000 else ""), height=200)
        else:
            st.warning("Aucun texte extrait")
    
    # Affichage structuré selon le type
    with st.expander("📊 Données structurées", expanded=True):
        data_type = extracted_data.get('type')
        
        if data_type == 'budget':
            display_budget_results(extracted_data)
        elif data_type == 'rh_laboratoire':
            display_rh_results(extracted_data)
        elif data_type == 'tabular':
            display_tabular_results(extracted_data)
        else:
            display_universal_results(extracted_data)
    
    # Téléchargement
    st.markdown("---")
    st.markdown("## 💾 Téléchargement")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Lire le fichier converti
        converted_path = os.path.join('converted', output_filename)
        if os.path.exists(converted_path):
            with open(converted_path, 'rb') as f:
                file_data = f.read()
            
            st.download_button(
                label=f"📥 Télécharger en {output_filename.split('.')[-1].upper()}",
                data=file_data,
                file_name=output_filename,
                mime="application/octet-stream"
            )
    
    with col2:
        # Option d'export en CSV
        if st.button("📋 Exporter les métadonnées (CSV)"):
            export_metadata_to_csv(extracted_data)

def display_budget_results(data):
    """Affiche les résultats budgétaires"""
    df = pd.DataFrame(data.get('lignes_budgetaires', []))
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.metric("💰 Total", f"{data.get('total', 0):,.2f} €")
    else:
        st.info("Aucune donnée budgétaire détectée")

def display_rh_results(data):
    """Affiche les résultats RH"""
    if data.get('personnel_par_grade'):
        df = pd.DataFrame(data['personnel_par_grade'])
        st.dataframe(df, use_container_width=True)
    
    if data.get('statistiques'):
        st.markdown("### 📊 Statistiques")
        for key, value in data['statistiques'].items():
            st.metric(key.replace('_', ' ').title(), value)

def display_tabular_results(data):
    """Affiche les résultats tabulaires"""
    for i, table in enumerate(data.get('tables', [])):
        st.markdown(f"### Tableau {i+1}")
        if table.get('headers'):
            df = pd.DataFrame(table.get('rows', []), columns=table['headers'])
            st.dataframe(df, use_container_width=True)
        st.caption(f"Dimensions: {table.get('row_count', 0)} lignes x {table.get('column_count', 0)} colonnes")

def display_universal_results(data):
    """Affiche les résultats universels"""
    sections = data.get('sections', [])
    if sections:
        st.markdown("### 📑 Sections détectées")
        for section in sections[:5]:
            st.markdown(f"**{section.get('title', 'Section')}**")
            if section.get('content'):
                preview = ' '.join(section['content'][:2])
                st.caption(preview[:200] + ("..." if len(preview) > 200 else ""))

def export_metadata_to_csv(data):
    """Exporte les métadonnées en CSV"""
    metadata = {
        'Type': [data.get('type', '')],
        'Détecté': [data.get('detected_type', '')],
        'Caractères': [data.get('text_length', 0)],
        'Lignes': [data.get('line_count', 0)]
    }
    df = pd.DataFrame(metadata)
    csv = df.to_csv(index=False)
    
    st.download_button(
        label="📊 Télécharger métadonnées",
        data=csv,
        file_name="metadata.csv",
        mime="text/csv"
    )

# Main
def main():
    """Fonction principale avec authentification"""
    
    # Vérifier si l'authentification est requise et si l'utilisateur est connecté
    if AUTH_CONFIG['require_auth'] and not st.session_state.authenticated:
        login_page()
        return
    
    # Initialisation
    init_session_state()
    
    # Header
    display_header()
    
    # Sidebar
    display_sidebar()
    
    # Configuration
    data_type, output_format = display_configuration()
    
    # Upload
    uploaded_file = display_upload()
    
    # Bouton de traitement
    if uploaded_file:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Lancer l'extraction", use_container_width=True):
                with st.spinner("Traitement en cours..."):
                    extracted_data, output_filename = process_file(
                        uploaded_file, data_type, output_format
                    )
                    
                    if extracted_data and output_filename:
                        display_results(extracted_data, output_filename)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: gray;'>DocAdminApp AI - Extraction intelligente de données administratives | 🔐 Accès sécurisé</p>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()