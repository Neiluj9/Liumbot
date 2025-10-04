# Crypto Funding Rate Arbitrage

Système de collecte et d'analyse des funding rates pour l'arbitrage sur les exchanges crypto.

## Exchanges Supportés

- ✅ **Hyperliquid**: API complète, funding toutes les heures
- ✅ **MEXC**: API complète, funding toutes les 8h (00:00, 08:00, 16:00 UTC)
- ✅ **Aster**: API indépendante, funding toutes les 8h (certains symbols 4h ou 1h)

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

### Collecte et analyse en temps réel

```bash
python main.py
```

Cela va :
1. Collecter les funding rates actuels de Hyperliquid et MEXC
2. Identifier les opportunités d'arbitrage
3. Calculer les statistiques
4. Sauvegarder les opportunités dans `arbitrage_opportunities.json`

### Configuration

Modifier `config.py` pour ajuster :
- `SYMBOLS`: Liste des cryptos à suivre
- `EXCHANGES`: Activer/désactiver les exchanges

## Structure du Projet

```
.
├── config.py              # Configuration
├── models.py              # Modèles de données (FundingRate, ArbitrageOpportunity)
├── collectors/
│   ├── base.py           # Classe de base pour collecteurs
│   ├── hyperliquid.py    # Collecteur Hyperliquid
│   └── mexc.py           # Collecteur MEXC
├── analyzer.py           # Analyse et détection d'arbitrage
└── main.py              # Script principal
```

## API Endpoints

### Hyperliquid
- Endpoint: `https://api.hyperliquid.xyz/info`
- Funding rates prédictifs: `{"type": "predictedFundings"}`
- Historique: `{"type": "fundingHistory", "coin": "BTC", "startTime": ...}`

### MEXC
- Base: `https://contract.mexc.com/api/v1/contract`
- Rate actuel: `/funding_rate/{symbol}`
- Historique: `/funding_rate/history?symbol={symbol}&page_num=1&page_size=100`

### Aster
- Base: `https://fapi.asterdex.com`
- Rate actuel: `/fapi/v1/premiumIndex` (contient `lastFundingRate`)
- Historique: `/fapi/v1/fundingRate?symbol={symbol}&startTime=...`

## Exemple de Sortie

```
==================================================================================================================
CRYPTO FUNDING RATE ARBITRAGE ANALYZER
==================================================================================================================
Timestamp: 2025-10-02T10:30:00
Tracking symbols: BTC, ETH, SOL, ...

📊 Collecting funding rates...
  → Starting Hyperliquid...
  ✓ Hyperliquid: 150 rates collected
  → Starting MEXC...
  ✓ MEXC: 120 rates collected
  → Starting Aster...
  ✓ Aster: 180 rates collected
✅ Collected 450 funding rates

💾 Saved current rates to current_funding_rates.json

🎯 ARBITRAGE OPPORTUNITIES FOUND
====================================================================================================

Top 5 opportunities out of 25 total

#   Symbol     Long Exchange    Long Rate    Short Exchange   Short Rate   Spread       Annual Return
----------------------------------------------------------------------------------------------------
1   BTC        hyperliquid      0.0125%      mexc             0.0350%      0.0225%      24.66%
2   ETH        hyperliquid     -0.0050%      aster            0.0200%      0.0250%      27.38%
3   SOL        mexc             0.0100%      aster            0.0280%      0.0180%      19.71%
4   AVAX       hyperliquid      0.0080%      mexc             0.0220%      0.0140%      15.33%
5   ARB        aster           -0.0020%      hyperliquid      0.0110%      0.0130%      14.24%
====================================================================================================

💾 Saved opportunities to arbitrage_opportunities.json
```

## Stratégie d'Arbitrage

1. **Long** sur l'exchange avec le funding rate le plus BAS (vous recevez le funding)
2. **Short** sur l'exchange avec le funding rate le plus HAUT (vous recevez le funding)
3. **Profit** = différence entre les deux rates × capital

⚠️ **Risques** : Exposition au prix, frais de transaction, liquidité, écarts de prix entre exchanges

## Todo

- [ ] WebSocket pour données temps réel (Aster supporte wss://fstream.asterdex.com)
- [ ] Base de données pour historique
- [ ] Alertes automatiques (Telegram/Discord)
- [ ] Backtesting sur données historiques
- [ ] Calculer les coûts réels (frais de trading, slippage)
