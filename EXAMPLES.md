# Exemples d'utilisation - Price Spread Monitor

## Cas d'usage 1 : Monitoring simple BTC

Surveiller l'écart de prix BTC entre Hyperliquid et Aster avec refresh toutes les 100ms :

```bash
python price_spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b aster --interval 100
```

**Sortie attendue :**
```
[21:55:14.640] BTC    H: 125415.00 ↔ A: 125314.00  Spread: +  101.00 (+ 0.0806%)
```

➜ Spread positif = Hyperliquid bid plus élevé qu'Aster ask = opportunité potentielle

---

## Cas d'usage 2 : Monitoring inverse

Surveiller dans l'autre sens (Aster → Hyperliquid) :

```bash
python price_spread_monitor.py --symbol BTC --exchange-a aster --exchange-b hyperliquid --interval 100
```

**Sortie attendue :**
```
[21:55:14.640] BTC    A: 125314.00 ↔ H: 125416.00  Spread: -  102.00 (- 0.0813%)
```

➜ Spread négatif = Aster bid inférieur à Hyperliquid ask = pas d'opportunité dans ce sens

---

## Cas d'usage 3 : Monitoring long terme

Lancer le monitoring pendant plusieurs heures et analyser les patterns :

```bash
# Lancer en background
nohup python price_spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b aster --interval 1000 > monitor.log 2>&1 &

# Vérifier le process
ps aux | grep price_spread

# Arrêter quand nécessaire
kill <PID>
```

Le fichier CSV sera créé automatiquement avec timestamp.

---

## Cas d'usage 4 : Visualisation des données

Après avoir collecté des données, tracer les graphiques :

```bash
# Collecter pendant 5 minutes
timeout 300 python price_spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b aster --interval 100

# Tracer le graphique
python plot_spread.py spreads_log_20251006_215513.csv
```

**Résultat :**
- Graphique 1 : Best Bid A vs Best Ask B
- Graphique 2 : Evolution du spread dans le temps
- Statistiques : moyenne, max, min du spread
- Fichier PNG sauvegardé

---

## Cas d'usage 5 : Monitoring multi-symboles

Surveiller plusieurs symboles en parallèle (plusieurs terminaux) :

**Terminal 1 - BTC :**
```bash
python price_spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b aster --interval 100
```

**Terminal 2 - ETH :**
```bash
python price_spread_monitor.py --symbol ETH --exchange-a hyperliquid --exchange-b aster --interval 100
```

**Terminal 3 - SOL :**
```bash
python price_spread_monitor.py --symbol SOL --exchange-a hyperliquid --exchange-b aster --interval 100
```

Chaque terminal affichera son propre spread en temps réel et créera son propre fichier CSV.

---

## Cas d'usage 6 : Analyse rapide avec grep

Trouver les spreads supérieurs à 100$ dans les logs :

```bash
# Pendant le monitoring
python price_spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b aster --interval 100 | grep "Spread: +  1[0-9][0-9]\."

# Ou après dans le CSV
awk -F',' '$7 > 100 {print $1, $7}' spreads_log_20251006_215513.csv
```

---

## Cas d'usage 7 : Alertes personnalisées

Créer un wrapper bash pour alerter quand le spread dépasse un seuil :

```bash
#!/bin/bash
# alert_spread.sh

THRESHOLD=150

python price_spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b aster --interval 100 | \
while IFS= read -r line; do
    echo "$line"

    # Extract spread value
    if [[ $line =~ Spread:\ \+\ +([0-9]+\.[0-9]+) ]]; then
        spread="${BASH_REMATCH[1]}"

        # Alert if above threshold
        if (( $(echo "$spread > $THRESHOLD" | bc -l) )); then
            echo "🚨 ALERT: Spread above threshold! $spread > $THRESHOLD"
            # Ajouter notification ici (mail, webhook, etc.)
        fi
    fi
done
```

---

## Cas d'usage 8 : Mode ultra-rapide

Monitoring à haute fréquence (25ms de refresh) :

```bash
python price_spread_monitor.py --symbol BTC --exchange-a hyperliquid --exchange-b aster --interval 25
```

⚠️ **Attention :** Plus l'interval est court, plus il y aura de lignes dans le CSV et d'affichage console.

---

## Cas d'usage 9 : Analyse de volatilité

Utiliser le CSV pour calculer la volatilité du spread :

```python
import pandas as pd

# Charger les données
df = pd.read_csv('spreads_log_20251006_215513.csv')

# Calculer stats
print(f"Mean spread: {df['spread'].mean():.2f}")
print(f"Std spread: {df['spread'].std():.2f}")
print(f"Volatility: {df['spread'].std() / df['spread'].mean() * 100:.2f}%")

# Identifier les pics
threshold = df['spread'].mean() + 2 * df['spread'].std()
peaks = df[df['spread'] > threshold]
print(f"\nPeaks above threshold ({threshold:.2f}):")
print(peaks[['timestamp', 'spread']])
```

---

## Notes importantes

### Lecture du spread

- **Spread positif** : `bid_A > ask_B` → Acheter sur B, vendre sur A
- **Spread négatif** : `bid_A < ask_B` → Pas d'opportunité dans ce sens

### Limitations

- ❌ **Pas de prise en compte des fees** : Les fees de trading ne sont pas déduites
- ❌ **Pas de prise en compte de la liquidité** : On regarde seulement best bid/ask, pas les volumes
- ❌ **Pas de prise en compte du slippage** : Dans la réalité, les prix peuvent bouger pendant l'exécution

### Pour une analyse complète

Il faudrait également considérer :
1. Fees de maker/taker sur chaque exchange
2. Depth du carnet d'ordres (liquidité disponible)
3. Latence réseau et temps d'exécution
4. Risque de funding rate et autres frais
5. Capital disponible et impact sur le marché

Ce script est volontairement simple et se concentre sur la **donnée brute en temps réel**.
