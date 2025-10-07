# Documentation

Documentation complète du système d'arbitrage de funding rates crypto.

## 📖 Table des Matières

### Guide de Démarrage

- **[Installation](installation.md)** - Guide d'installation détaillé avec toutes les dépendances
- **[Exemples d'Utilisation](examples.md)** - Cas d'usage pratiques et exemples de commandes

### Guides des Fonctionnalités

- **[Spread Monitor](spread-monitor.md)** - Guide complet du monitoring en temps réel via WebSocket

### Référence Technique

- **[API Reference](api-reference.md)** - Documentation des APIs internes et externes
- **[Changelog](changelog.md)** - Historique des changements et versions
- **[Structure du Projet](../CLAUDE.md)** - Architecture détaillée et guide pour développeurs
- **[README Principal](../README.md)** - Vue d'ensemble et quick start

## 🚀 Quick Links

### Commandes Principales

```bash
# Analyse des funding rates
python scripts/funding_analyzer.py

# Monitor de spread temps réel
python scripts/spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b mexc

# Trading
python scripts/trade_cli.py open --exchange1 hyperliquid --side1 long \
                                 --exchange2 mexc --side2 short \
                                 --symbol BTC --size 100 --price 50000

# Mise à jour des symboles
python scripts/update_symbols.py
```

## 📊 Structure de la Documentation

```
docs/
├── README.md              # Ce fichier - index de la documentation
├── installation.md        # Guide d'installation
├── examples.md            # Exemples pratiques
├── spread-monitor.md      # Guide du spread monitor
├── api-reference.md       # Référence API complète
└── changelog.md           # Historique des changements
```

## 🤝 Contribution

Pour contribuer à la documentation :

1. Les fichiers de documentation sont en Markdown
2. Suivez le style existant
3. Ajoutez des exemples pratiques
4. Testez tous les exemples de code

## 📝 Notes

- La documentation est maintenue à jour avec chaque release
- Pour les détails d'implémentation, voir `CLAUDE.md`
- Pour un aperçu rapide, voir le README principal

---

[← Retour au README principal](../README.md)
