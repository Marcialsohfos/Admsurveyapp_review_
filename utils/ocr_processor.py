"""
Module OCR amélioré pour DocuMiner AI - Version avec fallback PDF
"""

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import pdf2image
import re
import subprocess
import os
import sys
from typing import Dict, List, Any
import streamlit as st

class OCRProcessor:
    def __init__(self):
        """Initialise le processeur OCR"""
        self._configure_tesseract()
        self._verify_tesseract()
        self._check_poppler()
        
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
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Tesseract opérationnel")
            else:
                st.warning("⚠️ Tesseract non trouvé - fonctionnalités OCR limitées")
        except:
            st.warning("⚠️ Tesseract non trouvé - fonctionnalités OCR limitées")
    
    def _check_poppler(self):
        """Vérifie si poppler est installé"""
        try:
            result = subprocess.run(['pdfinfo', '-v'], 
                                  capture_output=True, text=True, timeout=5)
            self.poppler_available = result.returncode == 0
            if self.poppler_available:
                print("✅ Poppler installé")
            else:
                print("⚠️ Poppler non trouvé - utilisation de fallback")
                self.poppler_available = False
        except:
            self.poppler_available = False
            print("⚠️ Poppler non trouvé - utilisation de fallback")
    
    def process_file(self, filepath: str, data_type: str = 'auto') -> Dict[str, Any]:
        """Traite un fichier et extrait les données"""
        
        # Extraction OCR
        text = self._extract_text(filepath)
        
        # Vérifier si l'extraction a fonctionné
        if not text or "Erreur" in text:
            # Essayer une extraction directe du texte sans OCR
            if filepath.lower().endswith('.pdf'):
                text = self._extract_text_from_pdf_direct(filepath)
            
            if not text or "Erreur" in text:
                return {
                    'type': 'error',
                    'ocr_success': False,
                    'raw_text': text if text else "Aucun texte extrait",
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
    
    def _extract_text_from_pdf_direct(self, filepath: str) -> str:
        """Extrait le texte directement d'un PDF sans OCR"""
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
                    print(f"✅ Texte extrait directement du PDF: {len(text)} caractères")
                    return text
                else:
                    return ""
        except Exception as e:
            print(f"⚠️ Erreur extraction directe PDF: {e}")
            return ""
    
    def _extract_text(self, filepath: str) -> str:
        """Extrait le texte d'un fichier (PDF ou image)"""
        if filepath.lower().endswith('.pdf'):
            # D'abord essayer l'extraction directe
            direct_text = self._extract_text_from_pdf_direct(filepath)
            if direct_text:
                return direct_text
            
            # Sinon utiliser OCR
            return self._extract_text_from_pdf_ocr(filepath)
        else:
            return self._extract_text_from_image(filepath)
    
    def _extract_text_from_pdf_ocr(self, filepath: str) -> str:
        """Extrait le texte d'un PDF avec OCR"""
        try:
            # Vérifier si poppler est disponible
            if not self.poppler_available:
                # Fallback: utiliser une résolution plus basse
                try:
                    images = pdf2image.convert_from_path(
                        filepath, 
                        dpi=150,  # Résolution plus basse pour économiser les ressources
                        fmt='jpeg'
                    )
                except:
                    return "Erreur: Poppler non installé. Impossible de traiter le PDF scanné."
            else:
                images = pdf2image.convert_from_path(filepath, dpi=200)
            
            text = ""
            for i, image in enumerate(images):
                page_text = self._extract_text_from_image(image)
                if page_text and "Aucun texte" not in page_text:
                    text += f"--- Page {i+1} ---\n{page_text}\n\n"
            
            return text if text.strip() else "Aucun texte détecté dans le PDF"
            
        except Exception as e:
            error_msg = str(e)
            if "poppler" in error_msg.lower():
                return "Erreur: Poppler non installé. Veuillez contacter l'administrateur."
            return f"Erreur extraction PDF: {error_msg}"
    
    def _preprocess_image_pil(self, image):
        """Prétraitement d'image avec PIL (sans OpenCV)"""
        try:
            # Convertir en niveaux de gris si nécessaire
            if image.mode != 'L':
                image = image.convert('L')
            
            # Amélioration du contraste
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Amélioration de la netteté
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Réduction du bruit avec un filtre médian
            image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Seuillage pour obtenir une image binaire
            threshold = 128
            image = image.point(lambda p: 255 if p > threshold else 0)
            
            return image
            
        except Exception as e:
            print(f"Erreur prétraitement PIL: {e}")
            return image
    
    def _extract_text_from_image(self, image_input) -> str:
        """Extrait le texte d'une image avec prétraitement PIL"""
        try:
            # Chargement de l'image
            if isinstance(image_input, str):
                image = Image.open(image_input)
            else:
                image = image_input
            
            # Prétraitement
            processed_image = self._preprocess_image_pil(image)
            
            # Configuration OCR optimisée
            custom_config = r'--oem 3 --psm 6'
            
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
                except Exception as e:
                    print(f"Erreur avec langue {lang}: {e}")
                    continue
            
            return best_text.strip() if best_text.strip() else "Aucun texte détecté dans l'image"
            
        except Exception as e:
            return f"Erreur extraction OCR: {str(e)}"
    
    def _auto_detect_content_type(self, text: str) -> str:
        """Détection automatique du type de contenu"""
        # Vérifier spécifiquement pour les données RH
        if re.search(r'ATMS|TMS|TPMS|ITMS|IMS|Technicien|Agent|Grade', text, re.IGNORECASE):
            if re.search(r'effectif|personnel|grade', text, re.IGNORECASE):
                return 'rh_laboratoire'
        
        # Vérifier pour les tableaux
        if re.search(r'\|.*\|', text) or re.search(r'\s{2,}.*\s{2,}', text):
            if re.search(r'Effectif|Grade|Fréquence|Pourcentage', text, re.IGNORECASE):
                return 'tabular'
        
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
        
        # Nettoyer le texte des caractères spéciaux
        clean_text = re.sub(r'[^\x20-\x7E\xC0-\xFF\n\t]', '', text)
        
        return {
            'type': 'universal',
            'raw_text': clean_text,
            'sections': self._extract_semantic_sections(lines),
            'text_length': len(clean_text),
            'line_count': len(lines)
        }
    
    def _extract_semantic_sections(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extrait les sections sémantiques"""
        sections = []
        current_section = []
        current_title = "Début du document"
        
        for line in lines:
            # Nettoyer la ligne
            line = re.sub(r'[^\w\s\-\.,;:!?€%()]', '', line)
            
            # Détection de titres
            if (line.isupper() and len(line) > 5) or (len(line) < 80 and (line.endswith(':') or 'Tableau' in line)):
                if current_section:
                    sections.append({
                        'title': current_title,
                        'content': current_section[:10]
                    })
                current_section = []
                current_title = line
            elif len(line) > 10:
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
        """Parse les données RH spécifiquement pour votre fichier"""
        data = {
            'type': 'rh_laboratoire',
            'personnel_par_grade': [],
            'statistiques': {},
            'observations': [],
            'tableaux': []
        }
        
        lines = text.split('\n')
        
        # Pattern pour extraire grade et effectif
        patterns = [
            r'([A-Za-z\s\(\)\-]+)\s+(\d{1,4})(?:\s|$)',
            r'([A-Za-z\s\(\)]+)\s*:\s*(\d{1,4})',
            r'(\d{1,4})\s+([A-Za-z\s\(\)]+)',
        ]
        
        for line in lines:
            line = line.strip()
            
            # Chercher les grades RH spécifiques
            rh_grades = ['ATMS', 'TMS', 'TPMS', 'ITMS', 'IMS', 'ASOL', 'TAL']
            for grade in rh_grades:
                if grade in line:
                    # Extraire le nombre
                    numbers = re.findall(r'\b(\d{1,4})\b', line)
                    if numbers:
                        data['personnel_par_grade'].append({
                            'grade': grade,
                            'effectif': numbers[0]
                        })
            
            # Pattern générique
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # Déterminer quel groupe est le grade et quel groupe est l'effectif
                    groups = match.groups()
                    if groups[0].isdigit():
                        effectif, grade = groups[0], groups[1]
                    else:
                        grade, effectif = groups[0], groups[1]
                    
                    # Nettoyer le grade
                    grade = grade.strip()
                    if len(grade) > 3 and effectif.isdigit() and int(effectif) > 0:
                        data['personnel_par_grade'].append({
                            'grade': grade,
                            'effectif': effectif
                        })
        
        # Supprimer les doublons
        seen = set()
        unique_grades = []
        for item in data['personnel_par_grade']:
            key = item['grade']
            if key not in seen:
                seen.add(key)
                unique_grades.append(item)
        data['personnel_par_grade'] = unique_grades
        
        # Extraire le total général
        total_match = re.search(r'Total[^\d]*(\d{1,5})', text, re.IGNORECASE)
        if total_match:
            data['statistiques']['total_effectif'] = int(total_match.group(1))
        
        # Extraire les observations
        for line in lines:
            if any(word in line.lower() for word in ['prédominance', 'points clés', 'structure', 'coherent']):
                data['observations'].append(line.strip())
        
        # Extraire les tableaux
        tabular_data = self._parse_tabular_data_enhanced(text)
        data['tableaux'] = tabular_data.get('tables', [])
        
        return data
    
    def _parse_tabular_data_enhanced(self, text: str) -> Dict[str, Any]:
        """Parse amélioré pour données tabulaires"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        data = {
            'type': 'tabular',
            'tables': []
        }
        
        # Chercher les lignes qui ressemblent à des tableaux
        table_data = []
        in_table = False
        
        for line in lines:
            # Nettoyer la ligne
            clean_line = re.sub(r'[^\w\s\-\.,;:!?€%()/]', '', line)
            
            # Vérifier si la ligne contient des séparateurs de tableau
            if re.search(r'\s{2,}', clean_line) and len(clean_line.split()) >= 2:
                columns = re.split(r'\s{2,}', clean_line)
                columns = [col.strip() for col in columns if col.strip()]
                if len(columns) >= 2:
                    table_data.append(columns)
                    in_table = True
            elif in_table and len(table_data) >= 2:
                # Traiter le tableau
                headers = table_data[0]
                rows = table_data[1:]
                data['tables'].append({
                    'headers': headers,
                    'rows': rows,
                    'row_count': len(rows),
                    'column_count': len(headers)
                })
                table_data = []
                in_table = False
        
        # Traiter le dernier tableau
        if in_table and len(table_data) >= 2:
            headers = table_data[0]
            rows = table_data[1:]
            data['tables'].append({
                'headers': headers,
                'rows': rows,
                'row_count': len(rows),
                'column_count': len(headers)
            })
        
        return data
    
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