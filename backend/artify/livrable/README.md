  # 🎨 ARTIFY — Face to Artistic Style Transfer using GANs

## 📌 Objectif du projet
ARTIFY est une application d’intelligence artificielle permettant de transformer un visage réel en œuvre artistique à l’aide de modèles GAN (CycleGAN et GAN conditionnel).

L’utilisateur peut :
- importer une image de visage
- appliquer un style artistique
- générer automatiquement une version stylisée

---

## 🧠 Technologies utilisées

### IA / Deep Learning
- Python
- PyTorch
- CycleGAN
- Conditional GAN

### Outils
- GitLab
- VS Code
- GPU (optionnel pour accélérer l’entraînement)

---

## 📂 Structure du projet
artify/
├── dataset/
├── models/
├── livrable/
├── train.py
├── test.py
└── requirements.txt


### Description des dossiers

- dataset/ : images d’entraînement et de test
- models/ : implémentation des modèles GAN
- train.py : script d’entraînement
- test.py : génération d’images
- livrable/ : documentation du projet
- requirements.txt : dépendances Python

---

## 📊 Organisation des données (Dataset)

dataset/
├── trainA/ → visages réels (CelebA)
├── trainB/ → images artistiques (WikiArt)
├── testA/
└── testB/

---

## 🔗 Liens des datasets

### CelebA (visages)
https://mmlab.ie.cuhk.edu.hk/projects/CelebA.html

### WikiArt (peintures)
https://www.wikiart.org/

---

## 👥 Répartition des tâches

### 👤 Dorra Belkahla — Données
- Télécharger les datasets
- Nettoyage et redimensionnement (256x256)
- Normalisation
- Organisation des dossiers

### 👤 Emna Belkahla — CycleGAN (modèle principal)
- Implémentation du CycleGAN
- Entraînement du modèle
- Sauvegarde des poids (.pth)
- Génération des images artistiques
- Analyse des résultats

### 👤 Yessmine Nouira — GAN conditionnel
- Implémentation du modèle alternatif
- Entraînement
- Comparaison avec CycleGAN

### 👤 Eya Jmili — Interface utilisateur
- Design de l’interface
- Upload d’images
- Affichage des résultats
- Intégration du modèle entraîné
- Démonstration finale

---

## 🚀 Lancer le projet

### Installation
pip install -r requirements.txt

### Entraînement
python train.py

### Test / Génération
python test.py

---

## 🎯 Résultat attendu

Entrée : image réelle  
Sortie : image stylisée (peinture artistique)

---

## 📌 Remarque
Les datasets volumineux ne sont pas stockés sur GitLab.  
Ils doivent être téléchargés localement via les liens fournis.
