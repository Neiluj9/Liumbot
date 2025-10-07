# Installation du Price Spread Monitor

Guide d'installation complet pour le moniteur de spread en temps réel.

## Prérequis

- Python 3.11+
- pip

## Installation rapide

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Compiler les fichiers protobuf MEXC (déjà fait normalement)
cd collectors/mexc-websocket-proto
protoc --python_out=. *.proto
cd ../..

# 3. Tester le moniteur
python price_spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b mexc --interval 100
```

## Dépendances détaillées

### Obligatoires

```bash
pip install websockets>=10.0    # WebSocket client
pip install colorama>=0.4.6     # Couleurs console
pip install protobuf>=4.21.0    # Protocol Buffers (MEXC)
```

### Optionnelles

```bash
pip install matplotlib>=3.5.0   # Graphiques (plot_spread.py)
```

## Vérification de l'installation

### Test WebSocket Hyperliquid

```bash
python -c "
import asyncio
import websockets
asyncio.run(websockets.connect('wss://api.hyperliquid.xyz/ws'))
print('✅ Hyperliquid OK')
"
```

### Test WebSocket Aster

```bash
python -c "
import asyncio
import websockets
asyncio.run(websockets.connect('wss://fstream.asterdex.com/ws'))
print('✅ Aster OK')
"
```

### Test WebSocket MEXC + Protobuf

```bash
python -c "
import sys, os
sys.path.insert(0, 'collectors/mexc-websocket-proto')
from PushDataV3ApiWrapper_pb2 import PushDataV3ApiWrapper
print('✅ MEXC Protobuf OK')
"
```

## Structure des fichiers

```
liumbot2/
├── price_spread_monitor.py          # Script principal
├── requirements.txt                 # Dépendances Python
├── README_SPREAD_MONITOR.md         # Documentation
├── MEXC_STATUS.md                   # Détails techniques MEXC
├── EXAMPLES.md                      # Exemples d'utilisation
├── plot_spread.py                   # Visualisation graphique
├── collectors/
│   ├── websocket_base.py           # Classe de base WebSocket
│   ├── hyperliquid_ws.py           # Collector Hyperliquid
│   ├── aster_ws.py                 # Collector Aster
│   ├── mexc_ws.py                  # Collector MEXC (Protobuf)
│   └── mexc-websocket-proto/       # Fichiers protobuf MEXC
│       ├── *.proto                 # Définitions protobuf
│       └── *_pb2.py                # Compilés Python
└── exports/                        # Dossier CSV (créé auto)
    └── spreads_log_*.csv           # Logs générés
```

## Compilation des fichiers Protobuf

Si les fichiers `_pb2.py` sont manquants :

```bash
# Installer le compilateur protobuf
# Debian/Ubuntu:
sudo apt-get install protobuf-compiler

# macOS:
brew install protobuf

# Vérifier l'installation
protoc --version

# Compiler les fichiers
cd collectors/mexc-websocket-proto
protoc --python_out=. *.proto

# Vérifier la compilation
ls -l *_pb2.py
```

Vous devriez voir :
```
PushDataV3ApiWrapper_pb2.py
PublicAggreBookTickerV3Api_pb2.py
... (autres fichiers)
```

## Résolution des problèmes courants

### Erreur: `No module named 'google'`

```bash
pip install protobuf
```

### Erreur: `No module named 'PushDataV3ApiWrapper_pb2'`

```bash
cd collectors/mexc-websocket-proto
protoc --python_out=. *.proto
```

### Erreur: `ModuleNotFoundError: No module named 'websockets'`

```bash
pip install websockets
```

### Erreur: `ImportError: cannot import name 'Fore' from 'colorama'`

```bash
pip install --upgrade colorama
```

## Test complet

Pour tester tous les exchanges en une fois :

```bash
# Terminal 1 - MEXC vs Hyperliquid
python price_spread_monitor.py --symbol BTC --exchange-a mexc --exchange-b hyperliquid --interval 100

# Terminal 2 - Hyperliquid vs Aster
python price_spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b aster --interval 100

# Terminal 3 - MEXC vs Aster
python price_spread_monitor.py --symbol BTC --exchange-a mexc --exchange-b aster --interval 100
```

## Support

Si vous rencontrez des problèmes :

1. Vérifiez la version de Python : `python --version` (doit être 3.11+)
2. Réinstallez les dépendances : `pip install -r requirements.txt --force-reinstall`
3. Consultez `MEXC_STATUS.md` pour les détails MEXC
4. Consultez `README_SPREAD_MONITOR.md` pour la documentation complète

## Mise à jour

Pour mettre à jour le projet :

```bash
git pull  # Si vous utilisez git
pip install -r requirements.txt --upgrade
```

---

✅ Vous êtes prêt à monitorer les spreads en temps réel !
