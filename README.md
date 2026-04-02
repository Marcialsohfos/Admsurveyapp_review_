# DocAdminApp AI - Extraction intelligente de données administratives

[![Hugging Face Spaces](https://img.shields.io/badge/🤗-Hugging%20Face%20Spaces-blue)](https://huggingface.co/spaces)
[![Streamlit](https://img.shields.io/badge/🚀-Streamlit-FF4B4B)](https://streamlit.io)

## 🎯 Description

**DocAdminApp AI** est une application de numérisation intelligente qui permet d'extraire automatiquement des données de documents administratifs scannés (PDF, images) et de les convertir en formats exploitables.

## ✨ Fonctionnalités

- **OCR multilingue** (Français + Anglais)
- **Détection automatique** du type de document
- **Support multi-formats** : PDF scannés, PNG, JPG, TIFF
- **Conversion** vers CSV, Excel, Stata, SPSS, JSON, XML, HTML, Word
- **Interface Streamlit** moderne et intuitive

## 📦 Installation

```bash
# Cloner le repository
git clone https://github.com/votre-repo/documiner-ai.git
cd documiner-ai

# Installer les dépendances
pip install -r requirements.txt

# Installer Tesseract (Ubuntu/Debian)
sudo apt-get install tesseract-ocr tesseract-ocr-fra poppler-utils

# Lancer l'application
streamlit run app.py