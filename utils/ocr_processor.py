"""
Module OCR amélioré pour DocuMiner AI
"""

import pytesseract
from PIL import Image
import cv2
import numpy as np
import pdf2image
import re
import subprocess
import os
from typing import Dict, List, Any
import streamlit as st

class OCRProcessor:
    def __init__(self):
        """Initialise le processeur OCR"""
        self._configure_tesseract()
        self._verify_tesseract()
        
        # Détecteurs de contenu
        self.content_detectors = [
            self._detect_budget,
            self._detect_formation,
            self._detect_tabular,
            self._detect_legal,
            self._detect_administrative,
            self._detect_rh_laboratoire
        ]
        
        # Parsers spécialisés
        self.specialized_parsers = {
            'budget': self._parse_budget_data,
            'formation': self._parse_formation_data,
            'laboratoire': self._parse_lab_data,
            'voirie': self._parse_voirie_data,
            'legal': self._parse_legal_data,
            'administrative': self._parse_administrative_data,
            'rh_laboratoire': self._parse_rh_data,
            'tabular': self._parse_tabular_data_enhanced
        }
    
    def _configure_tesseract(self):
        """Configure Tesseract pour l'environnement"""
        # Chemins possibles pour différents environnements
        possible_paths = [
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/opt/homebrew/bin/tesseract',
            'tesseract'
        ]
        
        for path in possible_paths:
            if os.path.exists(path) or path == 'tesseract':
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"✅ Tesseract configuré: {path}")
                return
    
    def _verify_tesseract(self):
        """Vérifie l'installation de Tesseract"""
        try:
            result = subprocess.run(['tesseract', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Tesseract opérationnel")
            else:
                st.warning("⚠️ Tesseract non trouvé - fonctionnalités OCR limitées")
        except:
            st.warning("⚠️ Tesseract non trouvé - fonctionnalités OCR limitées")
    
    def process_file(self, filepath: str, data_type: str = 'auto') -> Dict[str, Any]:
        """Traite un fichier et extrait les données"""
        
        # Extraction OCR
        text = self._extract_text(filepath)
        
        # Vérifier si l'extraction a fonctionné
        if not text or "Erreur" in text:
            return {
                'type': 'error',
                'ocr_success': False,
                'raw_text': text,
                'detected_type': 'error',
                'message': "L'OCR n'a pas pu extraire de texte. Vérifiez la qualité du document."
            }
        
        # Détection automatique du type
        if data_type == 'auto':
            detected_type = self._auto_detect_content_type(text)
            parser = self.specialized_parsers.get(detected_type, self._parse_universal)
            data_type = detected_type
        else:
            parser = self.specialized_parsers.get(data_type, self._parse_universal)
        
        # Parsing
        parsed_data = parser(text)
        parsed_data['detected_type'] = data_type
        parsed_data['ocr_success'] = True
        parsed_data['text_length'] = len(text)
        parsed_data['line_count'] = len(text.split('\n'))
        
        return parsed_data
    
    def _extract_text(self, filepath: str) -> str:
        """Extrait le texte d'un fichier (PDF ou image)"""
        if filepath.lower().endswith('.pdf'):
            return self._extract_text_from_pdf(filepath)
        else:
            return self._extract_text_from_image(filepath)
    
    def _extract_text_from_pdf(self, filepath: str) -> str:
        """Extrait le texte d'un PDF avec OCR si nécessaire"""
        try:
            # Tentative d'extraction directe
            try:
                import PyPDF2
                with open(filepath, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    
                    if len(text.strip()) > 50:
                        return text
            except:
                pass
            
            # Fallback: conversion image + OCR
            images = pdf2image.convert_from_path(filepath, dpi=300)
            text = ""
            for i, image in enumerate(images):
                page_text = self._extract_text_from_image(image)
                text += f"--- Page {i+1} ---\n{page_text}\n\n"
            
            return text
            
        except Exception as e:
            return f"Erreur extraction PDF: {str(e)}"
    
    def _extract_text_from_image(self, image_input) -> str:
        """Extrait le texte d'une image avec prétraitement avancé"""
        try:
            # Chargement de l'image
            if isinstance(image_input, str):
                image = cv2.imread(image_input)
                if image is None:
                    return f"Erreur: Impossible de charger l'image {image_input}"
            else:
                image = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
            
            # Prétraitement
            processed_image = self._preprocess_image(image)
            
            # Configuration OCR optimisée
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,!?;:()-[]€$%/\|"\''
            
            # Essayer différentes langues
            languages = ['fra+eng', 'fra', 'eng']
            best_text = ""
            
            for lang in languages:
                try:
                    text = pytesseract.image_to_string(
                        processed_image, 
                        lang=lang, 
                        config=custom_config
                    )
                    if len(text.strip()) > len(best_text.strip()):
                        best_text = text
                except:
                    continue
            
            return best_text.strip() if best_text.strip() else "Aucun texte détecté dans l'image"
            
        except Exception as e:
            return f"Erreur extraction OCR: {str(e)}"
    
    def _preprocess_image(self, image):
        """Prétraitement avancé de l'image"""
        try:
            # Conversion en niveaux de gris
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Réduction du bruit
            denoised = cv2.medianBlur(gray, 3)
            
            # Amélioration du contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            contrast_enhanced = clahe.apply(denoised)
            
            # Seuillage Otsu
            _, binary = cv2.threshold(contrast_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return binary
            
        except Exception as e:
            print(f"Erreur prétraitement: {e}")
            return image
    
    def _auto_detect_content_type(self, text: str) -> str:
        """Détection automatique du type de contenu"""
        scores = {}
        
        for detector in self.content_detectors:
            detector_name, score = detector(text)
            scores[detector_name] = score
        
        best_type = max(scores.items(), key=lambda x: x[1])[0]
        return best_type if scores.get(best_type, 0) > 0 else 'universal'
    
    def _detect_budget(self, text: str) -> tuple:
        keywords = ['budget', 'montant', 'euro', '€', 'total', 'dépense', 'recette']
        score = sum(1 for kw in keywords if kw in text.lower())
        return 'budget', score
    
    def _detect_formation(self, text: str) -> tuple:
        keywords = ['exercice', 'question', 'réponse', 'évaluation', 'formation']
        score = sum(1 for kw in keywords if kw in text.lower())
        return 'formation', score
    
    def _detect_tabular(self, text: str) -> tuple:
        lines = text.split('\n')
        if not lines:
            return 'tabular', 0
        tabular_lines = sum(1 for line in lines 
                          if re.search(r'\s{2,}|\t|\|', line) and len(line.split()) >= 2)
        score = tabular_lines / len(lines) if lines else 0
        return 'tabular', score
    
    def _detect_legal(self, text: str) -> tuple:
        keywords = ['article', 'loi', 'décret', 'juridique', 'contrat']
        score = sum(1 for kw in keywords if kw in text.lower())
        return 'legal', score
    
    def _detect_administrative(self, text: str) -> tuple:
        keywords = ['référence', 'objet', 'destinataire', 'expéditeur']
        score = sum(1 for kw in keywords if kw in text.lower())
        return 'administrative', score
    
    def _detect_rh_laboratoire(self, text: str) -> tuple:
        keywords = ['technicien', 'atms', 'tms', 'effectif', 'grade', 'personnel']
        score = sum(1 for kw in keywords if kw in text.lower())
        return 'rh_laboratoire', score
    
    def _parse_universal(self, text: str) -> Dict[str, Any]:
        """Parser universel"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        return {
            'type': 'universal',
            'raw_text': text,
            'sections': self._extract_semantic_sections(lines),
            'text_length': len(text),
            'line_count': len(lines)
        }
    
    def _extract_semantic_sections(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extrait les sections sémantiques"""
        sections = []
        current_section = []
        current_title = "Début du document"
        
        for line in lines:
            # Détection de titres (mots en majuscules ou courts)
            if (line.isupper() and len(line) > 5) or (len(line) < 50 and line.endswith(':')):
                if current_section:
                    sections.append({
                        'title': current_title,
                        'content': current_section[:10]  # Limiter
                    })
                current_section = []
                current_title = line
            else:
                current_section.append(line)
        
        if current_section:
            sections.append({
                'title': current_title,
                'content': current_section[:10]
            })
        
        return sections
    
    def _parse_budget_data(self, text: str) -> Dict[str, Any]:
        """Parse les données budgétaires"""
        data = {
            'type': 'budget',
            'lignes_budgetaires': [],
            'total': 0
        }
        
        lines = text.split('\n')
        for line in lines:
            montant_match = re.search(r'(\d{1,3}(?:\s?\d{3})*(?:,\d+)?)\s*€?', line)
            if montant_match:
                montant_str = montant_match.group(1).replace(' ', '').replace(',', '.')
                try:
                    montant = float(montant_str)
                    data['lignes_budgetaires'].append({
                        'description': line[:100],
                        'montant': montant
                    })
                    data['total'] += montant
                except:
                    pass
        
        return data
    
    def _parse_rh_data(self, text: str) -> Dict[str, Any]:
        """Parse les données RH"""
        data = {
            'type': 'rh_laboratoire',
            'personnel_par_grade': [],
            'statistiques': {},
            'observations': []
        }
        
        lines = text.split('\n')
        for line in lines:
            grade_match = re.search(r'([A-Z]{2,}[\s]*[A-Z]*)\s+(\d+)', line)
            if grade_match:
                data['personnel_par_grade'].append({
                    'grade': grade_match.group(1).strip(),
                    'effectif': grade_match.group(2)
                })
        
        if data['personnel_par_grade']:
            total = sum(int(item['effectif']) for item in data['personnel_par_grade'] 
                       if item['effectif'].isdigit())
            data['statistiques']['total_effectif'] = total
        
        return data
    
    def _parse_tabular_data_enhanced(self, text: str) -> Dict[str, Any]:
        """Parse amélioré pour données tabulaires"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        data = {
            'type': 'tabular',
            'tables': []
        }
        
        current_table = []
        for line in lines:
            if re.search(r'\s{2,}|\t', line) and len(line.split()) >= 2:
                columns = re.split(r'\s{2,}|\t', line)
                current_table.append([col.strip() for col in columns if col.strip()])
            elif current_table and len(current_table) >= 2:
                data['tables'].append({
                    'headers': current_table[0],
                    'rows': current_table[1:],
                    'row_count': len(current_table) - 1,
                    'column_count': len(current_table[0])
                })
                current_table = []
        
        if current_table and len(current_table) >= 2:
            data['tables'].append({
                'headers': current_table[0],
                'rows': current_table[1:],
                'row_count': len(current_table) - 1,
                'column_count': len(current_table[0])
            })
        
        return data
    
    # Méthodes supplémentaires simplifiées
    def _parse_formation_data(self, text: str) -> Dict[str, Any]:
        return {'type': 'formation', 'raw_text': text}
    
    def _parse_lab_data(self, text: str) -> Dict[str, Any]:
        return {'type': 'laboratoire', 'raw_text': text}
    
    def _parse_voirie_data(self, text: str) -> Dict[str, Any]:
        return {'type': 'voirie', 'raw_text': text}
    
    def _parse_legal_data(self, text: str) -> Dict[str, Any]:
        return {'type': 'legal', 'raw_text': text}
    
    def _parse_administrative_data(self, text: str) -> Dict[str, Any]:
        return {'type': 'administrative', 'raw_text': text}