# 🛡️ VaultFlow: Private Agentic Airlock

**VaultFlow** est un assistant bancaire IA de nouvelle génération conçu avec une approche **Privacy-by-Design**. Il permet à un agent autonome (LLM) d'interagir avec des données sensibles et d'exécuter des actions métier sans jamais voir d'informations personnellement identifiables (PII).

---

## 🚀 Fonctionnalités Clés

*   **PII Airlock (Microsoft Presidio)** : Détection et anonymisation automatique des noms, emails, adresses et numéros de téléphone via NLP (SpaCy `fr_core_news_lg`) et Regex haute précision.
*   **Tokenisation Réversible** : Les données sensibles sont remplacées par des tokens déterministes (ex: `[EMAIL_1]`) avant d'être envoyées au LLM.
*   **Agent n8n Autonome** : Un workflow intelligent capable de bloquer/débloquer des cartes et de consulter des profils via des appels d'outils sécurisés.
*   **Safe-Deobfuscation** : Restauration transparente des données originales dans la réponse finale envoyée à l'utilisateur.
*   **Live Database Monitor** : Une interface moderne (Glassmorphism) avec un tableau de bord en temps réel pour visualiser l'état de la base de données sécurisée.

---

## 🛠️ Architecture Technique

VaultFlow repose sur une architecture en 4 couches garantissant une étanchéité totale :

1.  **Frontend (Vanilla JS/CSS)** : Interface utilisateur fluide et dashboard de monitoring.
2.  **Airlock (FastAPI + Microsoft Presidio)** : Microservice chargé de l'anonymisation, de la gestion des sessions et de l'exécution des outils "blindés".
3.  **Orchestrator (n8n)** : Agent IA (Gemini 2.0) gérant la logique conversationnelle et la prise de décision.
4.  **Secure Vault (SQLite)** : Base de données isolée contenant les informations réelles.

---

## 📦 Installation & Setup

### 1. Backend (FastAPI)
```bash
# Installation des dépendances
pip install -r requirements.txt
python -m spacy download fr_core_news_lg

# Initialisation de la base de données
python database.py

# Lancement du serveur
uvicorn main:app --reload
```

### 2. Orchestrateur (n8n)
*   Importez le fichier `n8n_workflow.json` dans n8n.
*   Configurez votre clé API Google Gemini dans le node approprié.
*   Vérifiez que l'URL du Webhook correspond à l'adresse utilisée par le Frontend.

### 3. Frontend
Ouvrez simplement `frontend/index.html` dans votre navigateur.

---

## 🐳 Docker Setup (Recommandé)

Pour une installation rapide et interconnectée du backend et de n8n :

1.  Assurez-vous d'avoir **Docker Desktop** installé et lancé.
2.  Exécutez le script de lancement automatique :
    - Sur **Windows (PowerShell)** :
      ```powershell
      .\launch.ps1
      ```
    - Sur **WSL / Linux (Bash)** :
      ```bash
      chmod +x launch.sh
      ./launch.sh
      ```
    *Ce script va lancer les containers, attendre leur initialisation, puis ouvrir le frontend dans Chrome.*

Ou manuellement via Docker Compose :
```bash
docker compose up -d
```
*   **Backend** : accessible sur `http://localhost:8000`
*   **n8n** : accessible sur `http://localhost:5678`

---

## 💎 Pourquoi c'est important ?
Dans un monde où la confidentialité des données est primordiale, **VaultFlow** prouve qu'on peut allier la puissance des Agents IA et la conformité RGPD la plus stricte. L'IA ne manipule que des indices anonymes, tandis que le contrôle reste entier entre les mains de l'infrastructure sécurisée de l'entreprise.

