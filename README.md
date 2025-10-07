# Crypto Funding Rate Arbitrage System

Système complet de collecte et d'analyse des funding rates pour l'arbitrage sur les exchanges crypto, avec monitoring en temps réel et exécution automatisée de trades.

## 🚀 Quick Start

```bash
# Installation
pip install -r requirements.txt

# Analyser les funding rates
python scripts/funding_analyzer.py

# Monitor le spread en temps réel
python scripts/spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b mexc
```

## 📚 Documentation

- **[Installation](docs/installation.md)** - Guide d'installation complet
- **[Exemples d'utilisation](docs/examples.md)** - Exemples pratiques et cas d'usage
- **[Spread Monitor](docs/spread-monitor.md)** - Guide du monitoring en temps réel

## 🎯 Fonctionnalités

- ✅ **Collecte de funding rates** via REST API (Hyperliquid, MEXC, Aster)
- ✅ **Analyse d'arbitrage** avec calcul des opportunités et rendements annualisés
- ✅ **Monitor temps réel** via WebSocket avec streaming des orderbooks
- ✅ **Visualisation** avec génération automatique de graphiques
- ✅ **Exécution de trades** synchronisés entre exchanges
- ✅ **Gestion des symboles** avec mise à jour automatique

## 🏗️ Architecture

```
liumbot2/
├── collectors/
│   ├── rest/              # Collecteurs REST API
│   └── websocket/         # Collecteurs WebSocket temps réel
├── executors/             # Exécuteurs de trades
├── scripts/               # Scripts CLI
│   ├── funding_analyzer.py
│   ├── spread_monitor.py
│   ├── spread_plotter.py
│   ├── trade_cli.py
│   └── update_symbols.py
├── utils/                 # Utilitaires
├── docs/                  # Documentation
├── config.py              # Configuration
├── models.py              # Modèles de données
└── analyzer.py            # Logique d'analyse
```

## 💡 Usage

### Analyse des Funding Rates

```bash
python scripts/funding_analyzer.py
```

Collecte les funding rates de tous les exchanges activés, analyse les opportunités d'arbitrage et exporte les résultats vers `exports/`.

### Monitor de Spread Temps Réel

```bash
python scripts/spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b mexc --interval 100
```

Surveille le spread de prix entre deux exchanges via WebSocket et génère automatiquement des graphiques.

### Trading

```bash
# Ouvrir une position
python scripts/trade_cli.py open \
    --exchange1 hyperliquid --side1 long \
    --exchange2 mexc --side2 short \
    --symbol BTC --size 100 --price 50000

# Fermer une position
python scripts/trade_cli.py close \
    --exchange1 mexc --side1 close_short \
    --exchange2 hyperliquid --side2 close_long \
    --symbol BTC --size 100 --price 50000
```

### Mise à Jour des Symboles

```bash
python scripts/update_symbols.py
```

Met à jour `symbols_data.json` avec les derniers symboles disponibles sur chaque exchange.

## 📊 Exchanges Supportés

| Exchange | REST API | WebSocket | Funding Interval |
|----------|----------|-----------|------------------|
| **Hyperliquid** | ✅ | ✅ | 1h |
| **MEXC** | ✅ | ✅ | 8h (00:00, 08:00, 16:00 UTC) |
| **Aster** | ✅ | ✅ | 8h (certains 4h ou 1h) |

## ⚙️ Configuration

Modifiez `config.py` pour ajuster :

- **`SYMBOLS`** - Liste des cryptos à suivre (225+ symboles)
- **`EXCHANGES`** - Activer/désactiver les exchanges
- **`TRADING_CONFIG`** - Credentials pour l'exécution de trades

## 📈 Stratégie d'Arbitrage

1. **Long** sur l'exchange avec le funding rate le plus BAS (vous recevez le funding)
2. **Short** sur l'exchange avec le funding rate le plus HAUT (vous recevez le funding)
3. **Profit** = différence entre les deux rates × capital

⚠️ **Risques** : Exposition au prix, frais de transaction, liquidité, écarts de prix entre exchanges

## 🔧 Développement

### Structure des Modules

- **collectors/rest/** - Collecteurs REST héritant de `BaseCollector`
- **collectors/websocket/** - Collecteurs WebSocket héritant de `WebSocketCollector`
- **executors/** - Exécuteurs de trades héritant de `BaseExecutor`
- **scripts/** - Scripts CLI autonomes
- **utils/** - Fonctions utilitaires réutilisables

### Ajouter un Nouvel Exchange

1. Créer `collectors/rest/your_exchange.py` héritant de `BaseCollector`
2. Implémenter `get_funding_rates()` et `get_funding_history()`
3. (Optionnel) Créer `collectors/websocket/your_exchange_ws.py`
4. Ajouter la config dans `config.py`
5. Importer dans les scripts nécessaires

## 📄 Licence

Ce projet est fourni à des fins éducatives. Utilisez-le à vos propres risques.

## 🤝 Contributing

Les contributions sont les bienvenues ! Veuillez consulter la documentation pour les détails d'implémentation.

---

Pour plus d'informations, consultez la [documentation complète](docs/).
