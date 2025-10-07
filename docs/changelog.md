# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

## [Unreleased] - 2025-10-07

### 🎨 Réorganisation Majeure

#### Structure du Projet

**Ajouté**
- Nouveau dossier `collectors/rest/` pour les collecteurs REST API
- Nouveau dossier `collectors/websocket/` pour les collecteurs WebSocket
- Nouveau dossier `scripts/` pour tous les scripts CLI
- Nouveau dossier `utils/` pour les utilitaires partagés
- Nouveau dossier `docs/` pour toute la documentation

**Déplacé**
- `main.py` → `scripts/funding_analyzer.py`
- `price_spread_monitor.py` → `scripts/spread_monitor.py`
- `plot_spread.py` → `scripts/spread_plotter.py`
- `trade.py` → `scripts/trade_cli.py`
- `update_symbols.py` → `scripts/update_symbols.py`
- Collecteurs REST vers `collectors/rest/`
- Collecteurs WebSocket vers `collectors/websocket/`
- Documentation vers `docs/`

**Modifié**
- Tous les imports mis à jour pour refléter la nouvelle structure
- `collectors/__init__.py` simplifié avec imports depuis `rest/`
- Scripts CLI ajustés avec imports relatifs corrects

#### Documentation

**Ajouté**
- `docs/README.md` - Index de la documentation
- `docs/api-reference.md` - Documentation complète des APIs
- README principal restructuré avec liens vers la documentation
- Section "Documentation" dans CLAUDE.md

**Déplacé**
- `EXAMPLES.md` → `docs/examples.md`
- `INSTALLATION.md` → `docs/installation.md`
- `README_SPREAD_MONITOR.md` → `docs/spread-monitor.md`

#### Utilities

**Ajouté**
- `utils/time_utils.py` - Fonctions de formatage de temps
  - `format_time_until_funding()` - Format countdown strings
  - `get_countdown_color()` - Colorama colors for countdowns

**Modifié**
- Scripts utilisent maintenant les utilitaires depuis `utils/`
- Code dédupliqué entre scripts

### 🐛 Corrections

- Correction des imports WebSocket (`WebSocketBase` → `WebSocketCollector`)
- Correction du path pour `spread_plotter.py` dans `spread_monitor.py`
- Correction des paths relatifs dans `update_symbols.py`

### 📝 Améliorations

- Meilleure séparation des responsabilités
- Structure plus maintenable et extensible
- Documentation mieux organisée et accessible
- Imports plus clairs et explicites

---

## [Initial] - 2025-10-02

### Ajouté

- Collecteurs pour Hyperliquid, MEXC, Aster (REST API)
- Analyse d'arbitrage de funding rates
- Monitor de spread en temps réel (WebSocket)
- Génération de graphiques
- Exécution de trades synchronisés
- Système de gestion des symboles
- Configuration centralisée
- Documentation de base

---

## Format

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

### Types de Changements

- **Ajouté** - Nouvelles fonctionnalités
- **Modifié** - Changements de fonctionnalités existantes
- **Déprécié** - Fonctionnalités bientôt supprimées
- **Supprimé** - Fonctionnalités supprimées
- **Corrigé** - Corrections de bugs
- **Sécurité** - Corrections de vulnérabilités

---

[← Back to Documentation](README.md)
