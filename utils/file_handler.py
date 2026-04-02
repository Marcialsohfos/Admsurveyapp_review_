"""
Module de gestion de fichiers pour DocuMiner AI
Gère l'upload, la validation, le nettoyage et la gestion des fichiers temporaires
"""

import os
import shutil
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
import streamlit as st
from werkzeug.utils import secure_filename

class FileHandler:
    """Gestionnaire de fichiers pour l'application"""
    
    # Extensions autorisées
    ALLOWED_EXTENSIONS = {
        'image': {'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif'},
        'document': {'pdf'},
        'all': {'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif', 'pdf'}
    }
    
    # Types MIME autorisés
    ALLOWED_MIME_TYPES = {
        'image/png', 'image/jpeg', 'image/jpg', 
        'image/tiff', 'image/bmp', 'image/gif',
        'application/pdf'
    }
    
    # Taille maximale par défaut (50 MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    def __init__(self, upload_dir: str = 'uploads', converted_dir: str = 'converted'):
        """
        Initialise le gestionnaire de fichiers
        
        Args:
            upload_dir: Dossier pour les fichiers uploadés
            converted_dir: Dossier pour les fichiers convertis
        """
        self.upload_dir = upload_dir
        self.converted_dir = converted_dir
        self.temp_dir = tempfile.gettempdir()
        
        # Créer les dossiers nécessaires
        self._create_directories()
        
        # Statistiques
        self.stats = {
            'files_processed': 0,
            'total_size_processed': 0,
            'errors': 0
        }
    
    def _create_directories(self):
        """Crée les dossiers nécessaires s'ils n'existent pas"""
        for directory in [self.upload_dir, self.converted_dir]:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Dossier vérifié/créé: {directory}")
    
    def validate_file(self, file) -> Tuple[bool, Optional[str]]:
        """
        Valide un fichier uploadé
        
        Args:
            file: Fichier uploadé (objet BytesIO)
            
        Returns:
            Tuple (est_valide, message_erreur)
        """
        # Vérifier si un fichier a été fourni
        if file is None:
            return False, "Aucun fichier fourni"
        
        # Vérifier le nom du fichier
        if not file.name:
            return False, "Nom de fichier invalide"
        
        # Vérifier l'extension
        extension = self._get_extension(file.name)
        if extension not in self.ALLOWED_EXTENSIONS['all']:
            return False, f"Extension non supportée: {extension}. Extensions acceptées: {', '.join(self.ALLOWED_EXTENSIONS['all'])}"
        
        # Vérifier la taille
        file_size = self._get_file_size(file)
        if file_size > self.MAX_FILE_SIZE:
            return False, f"Fichier trop volumineux: {file_size / (1024*1024):.1f} MB. Maximum: {self.MAX_FILE_SIZE / (1024*1024):.0f} MB"
        
        # Vérifier le type MIME (si disponible)
        if hasattr(file, 'type') and file.type:
            if file.type not in self.ALLOWED_MIME_TYPES:
                st.warning(f"Type MIME non standard: {file.type}. Le fichier sera quand même traité.")
        
        return True, None
    
    def save_uploaded_file(self, file) -> Optional[str]:
        """
        Sauvegarde un fichier uploadé
        
        Args:
            file: Fichier uploadé
            
        Returns:
            Chemin du fichier sauvegardé ou None en cas d'erreur
        """
        try:
            # Valider le fichier
            is_valid, error_msg = self.validate_file(file)
            if not is_valid:
                st.error(error_msg)
                return None
            
            # Créer un nom de fichier sécurisé avec timestamp
            original_name = secure_filename(file.name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = hashlib.md5(f"{original_name}{timestamp}".encode()).hexdigest()[:8]
            
            # Nouveau nom: original_timestamp_id.ext
            name_parts = os.path.splitext(original_name)
            secure_name = f"{name_parts[0]}_{timestamp}_{unique_id}{name_parts[1]}"
            
            # Chemin complet
            filepath = os.path.join(self.upload_dir, secure_name)
            
            # Sauvegarder le fichier
            with open(filepath, 'wb') as f:
                f.write(file.getvalue())
            
            # Mettre à jour les statistiques
            self.stats['files_processed'] += 1
            self.stats['total_size_processed'] += os.path.getsize(filepath)
            
            print(f"✅ Fichier sauvegardé: {filepath}")
            return filepath
            
        except Exception as e:
            self.stats['errors'] += 1
            st.error(f"Erreur lors de la sauvegarde: {str(e)}")
            return None
    
    def save_converted_file(self, data: bytes, original_filename: str, output_format: str) -> Optional[str]:
        """
        Sauvegarde un fichier converti
        
        Args:
            data: Données du fichier converti
            original_filename: Nom du fichier original
            output_format: Format de sortie
            
        Returns:
            Chemin du fichier sauvegardé ou None
        """
        try:
            # Créer un nom de fichier pour le résultat
            original_name = os.path.splitext(secure_filename(original_filename))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{original_name}_{timestamp}.{output_format}"
            filepath = os.path.join(self.converted_dir, output_filename)
            
            # Sauvegarder
            with open(filepath, 'wb') as f:
                f.write(data)
            
            print(f"✅ Fichier converti sauvegardé: {filepath}")
            return filepath
            
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde du fichier converti: {str(e)}")
            return None
    
    def cleanup_file(self, filepath: str) -> bool:
        """
        Supprime un fichier
        
        Args:
            filepath: Chemin du fichier à supprimer
            
        Returns:
            True si supprimé avec succès
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"🗑️ Fichier supprimé: {filepath}")
                return True
            return False
        except Exception as e:
            print(f"⚠️ Erreur lors de la suppression {filepath}: {e}")
            return False
    
    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        Supprime les fichiers plus vieux que max_age_hours
        
        Args:
            max_age_hours: Âge maximum en heures
        """
        current_time = datetime.now().timestamp()
        max_age_seconds = max_age_hours * 3600
        
        for directory in [self.upload_dir, self.converted_dir]:
            if not os.path.exists(directory):
                continue
                
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    if file_age > max_age_seconds:
                        self.cleanup_file(filepath)
    
    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """
        Obtient des informations sur un fichier
        
        Args:
            filepath: Chemin du fichier
            
        Returns:
            Dictionnaire d'informations
        """
        if not os.path.exists(filepath):
            return {'exists': False}
        
        stat = os.stat(filepath)
        return {
            'exists': True,
            'size': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'extension': self._get_extension(filepath),
            'filename': os.path.basename(filepath)
        }
    
    def create_temp_file(self, suffix: str = '') -> str:
        """
        Crée un fichier temporaire
        
        Args:
            suffix: Suffixe optionnel (ex: '.pdf')
            
        Returns:
            Chemin du fichier temporaire
        """
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        return path
    
    def cleanup_temp_file(self, filepath: str):
        """Supprime un fichier temporaire"""
        try:
            if os.path.exists(filepath):
                os.unlink(filepath)
        except Exception as e:
            print(f"⚠️ Erreur suppression fichier temporaire: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne les statistiques du gestionnaire
        
        Returns:
            Dictionnaire des statistiques
        """
        # Calculer l'espace utilisé
        upload_size = self._get_directory_size(self.upload_dir)
        converted_size = self._get_directory_size(self.converted_dir)
        
        return {
            **self.stats,
            'upload_dir_size_mb': upload_size / (1024 * 1024),
            'converted_dir_size_mb': converted_size / (1024 * 1024),
            'total_size_mb': (upload_size + converted_size) / (1024 * 1024),
            'files_in_upload': len(os.listdir(self.upload_dir)) if os.path.exists(self.upload_dir) else 0,
            'files_in_converted': len(os.listdir(self.converted_dir)) if os.path.exists(self.converted_dir) else 0
        }
    
    def reset_stats(self):
        """Réinitialise les statistiques"""
        self.stats = {
            'files_processed': 0,
            'total_size_processed': 0,
            'errors': 0
        }
    
    def clear_all_files(self) -> int:
        """
        Supprime tous les fichiers des dossiers upload et converted
        
        Returns:
            Nombre de fichiers supprimés
        """
        count = 0
        for directory in [self.upload_dir, self.converted_dir]:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    filepath = os.path.join(directory, filename)
                    if os.path.isfile(filepath):
                        if self.cleanup_file(filepath):
                            count += 1
        return count
    
    # Méthodes privées
    
    def _get_extension(self, filename: str) -> str:
        """Extrait l'extension d'un nom de fichier"""
        return filename.lower().split('.')[-1] if '.' in filename else ''
    
    def _get_file_size(self, file) -> int:
        """Obtient la taille d'un fichier uploadé"""
        try:
            # Chercher la taille de différentes manières
            if hasattr(file, 'size'):
                return file.size
            elif hasattr(file, 'getbuffer'):
                return file.getbuffer().nbytes
            else:
                # Lire le contenu pour obtenir la taille
                current_pos = file.tell()
                file.seek(0, os.SEEK_END)
                size = file.tell()
                file.seek(current_pos)
                return size
        except Exception:
            return 0
    
    def _get_directory_size(self, directory: str) -> int:
        """Calcule la taille totale d'un dossier"""
        total = 0
        if os.path.exists(directory):
            for entry in os.scandir(directory):
                if entry.is_file():
                    total += entry.stat().st_size
        return total


# Fonctions utilitaires pour Streamlit
def get_file_handler() -> FileHandler:
    """
    Obtient ou crée une instance de FileHandler dans la session Streamlit
    
    Returns:
        Instance de FileHandler
    """
    if 'file_handler' not in st.session_state:
        st.session_state.file_handler = FileHandler()
    return st.session_state.file_handler


def display_file_stats():
    """Affiche les statistiques des fichiers dans la sidebar"""
    handler = get_file_handler()
    stats = handler.get_stats()
    
    with st.sidebar:
        st.markdown("## 📊 Statistiques")
        st.metric("📄 Fichiers traités", stats['files_processed'])
        st.metric("💾 Taille traitée", f"{stats['total_size_processed'] / (1024*1024):.1f} MB")
        st.metric("❌ Erreurs", stats['errors'])
        
        if stats['upload_dir_size_mb'] > 0 or stats['converted_dir_size_mb'] > 0:
            st.markdown("### 💿 Stockage")
            st.progress(min(1.0, stats['total_size_mb'] / 500))  # Max 500 MB
            st.caption(f"Total: {stats['total_size_mb']:.1f} MB")


def cleanup_session_files():
    """Nettoie les fichiers de la session courante"""
    handler = get_file_handler()
    
    # Supprimer les fichiers temporaires de la session
    if 'temp_files' in st.session_state:
        for temp_file in st.session_state.temp_files:
            handler.cleanup_temp_file(temp_file)
        st.session_state.temp_files = []
    
    # Nettoyer les vieux fichiers (plus de 24h)
    handler.cleanup_old_files(max_age_hours=24)