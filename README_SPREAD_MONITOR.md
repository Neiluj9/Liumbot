# Price Spread Monitor

Moniteur en temps réel des écarts de prix bid/ask entre deux plateformes crypto via WebSocket.

## Description

Ce script compare en temps réel :
- **Best bid** de la plateforme A (meilleur prix d'achat)
- **Best ask** de la plateforme B (meilleur prix de vente)

Et calcule le **spread** : `bid_A - ask_B`

Un spread positif indique une opportunité potentielle d'acheter sur B (à ask_B) et vendre sur A (à bid_A).

## Installation

```bash
pip install -r requirements.txt
```

Les dépendances nécessaires :
- `websockets` : connexions WebSocket
- `colorama` : affichage coloré en console
- `asyncio` : gestion asynchrone

## Utilisation

```bash
python price_spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b aster --interval 100
```

### Arguments

- `--symbol` : Symbol à monitorer (ex: BTC, ETH, SOL)
- `--exchange-a` : Première plateforme (hyperliquid, aster, ou mexc)
- `--exchange-b` : Deuxième plateforme (hyperliquid, aster, ou mexc)
- `--interval` : Intervalle de rafraîchissement en millisecondes (défaut: 100)

### Exemples

```bash
# Monitorer BTC sur Hyperliquid vs Aster avec refresh 100ms
python price_spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b aster --interval 100

# Monitorer ETH sur Aster vs Hyperliquid avec refresh 200ms
python price_spread_monitor.py --symbol ETH --exchange-a aster --exchange-b hyperliquid --interval 200
```

## Sortie

### Affichage console

```
================================================================================
PRICE SPREAD MONITOR
================================================================================
Symbol: BTC
Exchange A: HYPERLIQUID
Exchange B: ASTER
Update interval: 100ms
Logging to: spreads_log_20251006_215224.csv
================================================================================

[Hyperliquid] Connected to WebSocket
[Hyperliquid] Subscribed to BTC orderbook
[Aster] Connected to WebSocket
[Aster] Subscribed to BTC orderbook
[21:52:25.313] BTC    H: 125495.00 ↔ A: 125394.60  Spread: +  100.40 (+ 0.0801%)
[21:52:25.413] BTC    H: 125495.00 ↔ A: 125394.60  Spread: +  100.40 (+ 0.0801%)
[21:52:25.516] BTC    H: 125494.00 ↔ A: 125394.60  Spread: +   99.40 (+ 0.0793%)
```

**Légende :**
- `H` : Hyperliquid
- `A` : Aster
- Vert : spread positif (opportunité potentielle)
- Rouge : spread négatif

### Fichier CSV

Un fichier CSV est automatiquement créé : `spreads_log_{timestamp}.csv`

Format :
```csv
timestamp,exchange_a,exchange_b,symbol,bid_a,ask_b,spread,spread_pct
2025-10-06T21:52:25.313660,hyperliquid,aster,BTC,125495.00,125394.60,100.40,0.0801
```

Ce fichier peut être utilisé pour :
- Tracer des graphiques de l'évolution du spread
- Analyser les patterns
- Calculer des statistiques

## Architecture

### Fichiers

```
collectors/
  ├── websocket_base.py       # Classe abstraite pour WebSocket
  ├── hyperliquid_ws.py       # Collector Hyperliquid
  └── aster_ws.py             # Collector Aster

price_spread_monitor.py       # Script principal
```

### Classes WebSocket

Chaque collector hérite de `WebSocketCollector` et implémente :
- `get_ws_url()` : URL du WebSocket
- `get_subscribe_message()` : Message de souscription
- `parse_orderbook()` : Parse les messages et extrait best bid/ask

### Reconnexion automatique

Le système reconnecte automatiquement en cas de déconnexion avec un délai de 5 secondes.

## Limitations volontaires

- ✅ Simple : un seul symbole à la fois
- ✅ Pas de calcul de fees
- ✅ Comparaison entre deux plateformes uniquement
- ✅ Focus sur la donnée brute en temps réel

## Ajouter une nouvelle plateforme

1. Créer `collectors/nouvelle_plateforme_ws.py`
2. Hériter de `WebSocketCollector`
3. Implémenter les 3 méthodes abstraites
4. Ajouter le choix dans `price_spread_monitor.py` ligne 46

Exemple minimal :
```python
from collectors.websocket_base import WebSocketCollector, OrderbookData

class NouvellePlateformeWebSocket(WebSocketCollector):
    def __init__(self):
        super().__init__("NouvellePlateforme")
        self.ws_url = "wss://..."

    async def get_ws_url(self, symbol: str) -> str:
        return self.ws_url

    async def get_subscribe_message(self, symbol: str) -> str:
        return json.dumps({"subscribe": symbol})

    def parse_orderbook(self, message: str, symbol: str) -> Optional[OrderbookData]:
        # Parser le message et retourner OrderbookData
        pass
```

## Notes

- Le spread ne prend PAS en compte les fees de trading
- Les timestamps sont en heure locale du système
- Le rafraîchissement console est throttlé par `--interval`
- Les données WebSocket arrivent plus fréquemment mais sont filtrées pour l'affichage

## Arrêt

`Ctrl+C` pour arrêter proprement le moniteur. Le fichier CSV est sauvegardé automatiquement.

## Exchanges supportés

| Exchange | WebSocket | Status | Format | Notes |
|----------|-----------|--------|--------|-------|
| Hyperliquid | ✅ | Fonctionnel | JSON | Refresh rapide |
| Aster | ✅ | Fonctionnel | JSON | Binance-like API |
| **MEXC** | ✅ | **Fonctionnel** | **Protobuf** | Nouveau format août 2025 |

**Note MEXC** : Utilise Protocol Buffers depuis août 2025. Nécessite `pip install protobuf`. Voir `MEXC_STATUS.md` pour détails techniques.
