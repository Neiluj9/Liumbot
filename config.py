"""Configuration for crypto funding rate arbitrage"""

# API Endpoints
HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"
MEXC_API_BASE = "https://contract.mexc.com/api/v1/contract"
ASTER_API_BASE = "https://fapi.asterdex.com"

# Exchange configuration
EXCHANGES = {
    "hyperliquid": {
        "name": "Hyperliquid",
        "enabled": True,
        "funding_interval_hours": 1  # Hyperliquid pays every hour
    },
    "mexc": {
        "name": "MEXC",
        "enabled": True,
        "funding_interval_hours": 8  # MEXC pays at 00:00, 08:00, 16:00 UTC
    },
    "aster": {
        "name": "Aster",
        "enabled": True,
        "funding_interval_hours": 8  # Default for symbols not in ASTER_FUNDING_INTERVALS
    }
}

# Aster funding rate intervals by symbol (normalized)
# Most symbols use 8h, but some use 4h or other intervals
ASTER_FUNDING_INTERVALS = {
    # 4h interval (66 symbols)
    "0G": 4, "1000BONK": 4, "AI": 4, "AIA": 4, "AIO": 4, "ARIA": 4,
    "ASTER": 4, "AVNT": 4, "BARD": 4, "BAS": 4, "BIGTIME": 4, "BLESS": 4,
    "BLZ": 4, "BTR": 4, "C": 4, "CAKE": 4, "CUDIS": 4, "CYBER": 4,
    "DAM": 4, "ESPORTS": 4, "FARTCOIN": 4, "FLOCK": 4, "GAS": 4, "HEMI": 4,
    "HOLO": 4, "HYPE": 4, "IMX": 4, "IN": 4, "IO": 4, "LISTA": 4,
    "MANTA": 4, "MITO": 4, "ONDO": 4, "ORDI": 4, "PENGU": 4, "PIXEL": 4,
    "PORT3": 4, "PROVE": 4, "PTB": 4, "PUMP": 4, "PYTH": 4, "Q": 4,
    "SAHARA": 4, "SAPIEN": 4, "SKY": 4, "SPK": 4, "STBL": 4, "STRK": 4,
    "TAKE": 4, "TIA": 4, "TON": 4, "TOSHI": 4, "TOWNS": 4, "TRADOOR": 4,
    "TRB": 4, "TREE": 4, "TRUMP": 4, "UB": 4, "WLFI": 4, "XNY": 4,
    "XPIN": 4, "XPL": 4, "YGG": 4, "ZKC": 4, "ZORA": 4, "ZRC": 4,

    # Unusual intervals (rare cases)
    "2Z": 1, "EDEN": 1, "FF": 1, "SQD": 1, "ZEC": 1,
    "FTT": 2,

    # All other symbols default to 8h
}

# Symbols to track (normalized)
# All symbols available on at least 2 exchanges (225 total)
SYMBOLS = ['0G', '1000BONK', '2Z', 'AAVE', 'ACE', 'ADA', 'AI', 'AI16Z', 'AIA', 'AIO', 'AIXBT', 'ALGO', 'ALT', 'ANIME', 'APE', 'APEX', 'APT', 'AR', 'ARB', 'ARIA', 'ARK', 'ASTER', 'ATOM', 'AVAX', 'AVNT', 'B', 'BABY', 'BADGER', 'BANANA', 'BARD', 'BAS', 'BCH', 'BERA', 'BIGTIME', 'BIO', 'BLAST', 'BLESS', 'BLUR', 'BLZ', 'BNB', 'BNT', 'BOME', 'BRETT', 'BSV', 'BTC', 'BTR', 'C', 'CAKE', 'CATI', 'CELO', 'CFX', 'CHILLGUY', 'COMP', 'CRV', 'CUDIS', 'CYBER', 'DAM', 'DOGE', 'DOOD', 'DOT', 'DYDX', 'DYM', 'EDEN', 'EIGEN', 'ENA', 'ENS', 'ESPORTS', 'ETC', 'ETH', 'ETHFI', 'FARTCOIN', 'FET', 'FF', 'FLOCK', 'FTT', 'FXS', 'GALA', 'GAS', 'GMT', 'GMX', 'GOAT', 'GRASS', 'GRIFFAIN', 'HBAR', 'HEMI', 'HMSTR', 'HOLO', 'HYPE', 'HYPER', 'ILV', 'IMX', 'IN', 'INIT', 'INJ', 'IO', 'IOTA', 'IP', 'JTO', 'JUP', 'KAITO', 'KAS', 'LAUNCHCOIN', 'LAYER', 'LDO', 'LINEA', 'LINK', 'LISTA', 'LTC', 'MANTA', 'MAV', 'MAVIA', 'ME', 'MELANIA', 'MEME', 'MERL', 'MEW', 'MINA', 'MITO', 'MNT', 'MOODENG', 'MORPHO', 'MOVE', 'MYRO', 'NEAR', 'NEO', 'NIL', 'NOT', 'NTRN', 'NXPC', 'OGN', 'OM', 'ONDO', 'OP', 'ORBS', 'ORDI', 'PAXG', 'PENDLE', 'PENGU', 'PEOPLE', 'PIXEL', 'PNUT', 'POL', 'POLYX', 'POPCAT', 'PORT3', 'PROMPT', 'PROVE', 'PTB', 'PUMP', 'PYTH', 'Q', 'RDNT', 'RENDER', 'REQ', 'RESOLV', 'REZ', 'RSR', 'RUNE', 'S', 'SAGA', 'SAHARA', 'SAND', 'SAPIEN', 'SCR', 'SEI', 'SKY', 'SNX', 'SOL', 'SOPH', 'SPK', 'SPX', 'SQD', 'STBL', 'STG', 'STRAX', 'STRK', 'STX', 'SUI', 'SUPER', 'SUSHI', 'SYRUP', 'TAG', 'TAKE', 'TAO', 'TIA', 'TNSR', 'TON', 'TOSHI', 'TOWNS', 'TRADOOR', 'TRB', 'TREE', 'TRUMP', 'TRX', 'TST', 'TURBO', 'UB', 'UMA', 'UNI', 'USTC', 'USUAL', 'VINE', 'VIRTUAL', 'VVV', 'W', 'WCT', 'WIF', 'WLD', 'WLFI', 'XAI', 'XLM', 'XNY', 'XPIN', 'XPL', 'XRP', 'YGG', 'YZY', 'ZEC', 'ZEN', 'ZEREBRO', 'ZETA', 'ZKC', 'ZORA', 'ZRC', 'ZRO']
