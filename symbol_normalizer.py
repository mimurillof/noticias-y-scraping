#!/usr/bin/env python3
"""
Módulo de normalización de símbolos de assets.
Convierte símbolos mal formateados a formato compatible con yfinance.
"""

import re
from typing import Dict, Optional


class SymbolNormalizer:
    """
    Clase para normalizar símbolos de assets financieros.
    
    Maneja casos comunes de símbolos mal formateados:
    - Cryptocurrencias sin guion: BTCUSD → BTC-USD
    - Tickers incompletos: NVD → NVDA
    - Formato de exchanges extranjeros: *.F, *.DE
    """
    
    # Diccionario de correcciones conocidas
    KNOWN_CORRECTIONS: Dict[str, str] = {
        "NVD": "NVDA",          # NVIDIA
        "MSFT": "MSFT",         # Microsoft (ya correcto)
        "APPL": "AAPL",         # Apple (error común)
        "GOOGL": "GOOGL",       # Google (ya correcto)
        "GOOG": "GOOGL",        # Google Class C → Class A
        "TSLA": "TSLA",         # Tesla (ya correcto)
        "AMZN": "AMZN",         # Amazon (ya correcto)
        "META": "META",         # Meta (ya correcto)
        "NFLX": "NFLX",         # Netflix (ya correcto)
        "AMD": "AMD",           # AMD (ya correcto)
        "INTC": "INTC",         # Intel (ya correcto)
    }
    
    # Mapeo de cryptocurrencias principales
    CRYPTO_MAPPING: Dict[str, str] = {
        "BTC": "BTC-USD",
        "BTCUSD": "BTC-USD",
        "BTCUSDT": "BTC-USD",
        "BITCOIN": "BTC-USD",
        
        "ETH": "ETH-USD",
        "ETHUSD": "ETH-USD",
        "ETHUSDT": "ETH-USD",
        "ETHEREUM": "ETH-USD",
        
        "SOL": "SOL-USD",
        "SOLUSD": "SOL-USD",
        "SOLANA": "SOL-USD",
        
        "DOGE": "DOGE-USD",
        "DOGEUSD": "DOGE-USD",
        "DOGECOIN": "DOGE-USD",
        
        "ADA": "ADA-USD",
        "ADAUSD": "ADA-USD",
        "CARDANO": "ADA-USD",
        
        "XRP": "XRP-USD",
        "XRPUSD": "XRP-USD",
        "RIPPLE": "XRP-USD",
        
        "DOT": "DOT-USD",
        "DOTUSD": "DOT-USD",
        "POLKADOT": "DOT-USD",
        
        "AVAX": "AVAX-USD",
        "AVAXUSD": "AVAX-USD",
        "AVALANCHE": "AVAX-USD",
        
        "MATIC": "MATIC-USD",
        "MATICUSD": "MATIC-USD",
        "POLYGON": "MATIC-USD",
        
        "LINK": "LINK-USD",
        "LINKUSD": "LINK-USD",
        "CHAINLINK": "LINK-USD",
    }
    
    # Mapeo de stablecoins
    STABLECOIN_MAPPING: Dict[str, str] = {
        "USDT": "USDT-USD",
        "USDTUSD": "USDT-USD",
        "TETHER": "USDT-USD",
        
        "USDC": "USDC-USD",
        "USDCUSD": "USDC-USD",
        
        "BUSD": "BUSD-USD",
        "BUSDUSD": "BUSD-USD",
        
        "DAI": "DAI-USD",
        "DAIUSD": "DAI-USD",
        
        "PAXG": "PAXG-USD",
        "PAXGUSD": "PAXG-USD",
        "PAXOS": "PAXG-USD",
        
        "TUSD": "TUSD-USD",
        "TUSDUSD": "TUSD-USD",
        
        "USDP": "USDP-USD",
        "USDPUSD": "USDP-USD",
    }
    
    @classmethod
    def normalize(cls, symbol: str, verbose: bool = False) -> str:
        """
        Normaliza un símbolo de asset para que sea compatible con yfinance.
        
        Args:
            symbol: Símbolo original del asset
            verbose: Si True, imprime el proceso de normalización
            
        Returns:
            Símbolo normalizado compatible con yfinance
        """
        if not symbol or not isinstance(symbol, str):
            return symbol
        
        original_symbol = symbol
        symbol = symbol.strip().upper()
        
        # 1. Corregir tickers conocidos
        if symbol in cls.KNOWN_CORRECTIONS:
            corrected = cls.KNOWN_CORRECTIONS[symbol]
            if verbose and corrected != symbol:
                print(f"  🔧 {original_symbol} → {corrected} (ticker conocido)")
            return corrected
        
        # 2. Corregir cryptocurrencias
        if symbol in cls.CRYPTO_MAPPING:
            corrected = cls.CRYPTO_MAPPING[symbol]
            if verbose:
                print(f"  🔧 {original_symbol} → {corrected} (crypto)")
            return corrected
        
        # 3. Corregir stablecoins
        if symbol in cls.STABLECOIN_MAPPING:
            corrected = cls.STABLECOIN_MAPPING[symbol]
            if verbose:
                print(f"  🔧 {original_symbol} → {corrected} (stablecoin)")
            return corrected
        
        # 4. Detectar formato alemán y convertir
        if symbol.endswith(".F") or symbol.endswith(".DE"):
            base_symbol = symbol.split(".")[0]
            us_equivalent = cls.KNOWN_CORRECTIONS.get(base_symbol, None)
            if us_equivalent:
                if verbose:
                    print(f"  🔧 {original_symbol} → {us_equivalent} (exchange alemán)")
                return us_equivalent
            else:
                if verbose:
                    print(f"  ⚠️  {original_symbol} - Exchange alemán sin mapeo (usando original)")
                return symbol
        
        # 5. Detectar formato crypto sin guion (patrón: 3-5 letras + USD)
        crypto_pattern = re.match(r'^([A-Z]{3,5})USD[T]?$', symbol)
        if crypto_pattern:
            base = crypto_pattern.group(1)
            corrected = f"{base}-USD"
            if verbose:
                print(f"  🔧 {original_symbol} → {corrected} (patrón crypto)")
            return corrected
        
        # 6. Si ya tiene formato crypto correcto, dejarlo
        if re.match(r'^[A-Z]{3,5}-USD$', symbol):
            return symbol
        
        # 7. Si es un ticker normal de acciones (1-5 letras), dejarlo
        if re.match(r'^[A-Z]{1,5}$', symbol):
            return symbol
        
        # 8. Caso por defecto: retornar sin cambios pero con advertencia
        if verbose:
            print(f"  ⚠️  {original_symbol} - No se pudo normalizar (usando original)")
        return symbol
    
    @classmethod
    def normalize_batch(cls, symbols: list, verbose: bool = False) -> list:
        """
        Normaliza una lista de símbolos.
        
        Args:
            symbols: Lista de símbolos a normalizar
            verbose: Si True, imprime el proceso de normalización
            
        Returns:
            Lista de símbolos normalizados
        """
        return [cls.normalize(symbol, verbose=verbose) for symbol in symbols]
    
    @classmethod
    def is_crypto(cls, symbol: str) -> bool:
        """
        Verifica si un símbolo es una criptomoneda.
        
        Args:
            symbol: Símbolo a verificar
            
        Returns:
            True si es una criptomoneda
        """
        symbol = symbol.upper().strip()
        normalized = cls.normalize(symbol)
        return normalized.endswith("-USD") and len(normalized.split("-")[0]) <= 5
    
    @classmethod
    def get_base_symbol(cls, symbol: str) -> str:
        """
        Obtiene el símbolo base sin sufijos de exchange.
        
        Args:
            symbol: Símbolo completo (ej: "BTC-USD", "AAPL")
            
        Returns:
            Símbolo base (ej: "BTC", "AAPL")
        """
        normalized = cls.normalize(symbol)
        
        # Si es crypto, quitar el sufijo -USD
        if "-USD" in normalized:
            return normalized.split("-")[0]
        
        # Si tiene sufijo de exchange, quitarlo
        if "." in normalized:
            return normalized.split(".")[0]
        
        return normalized


# Función de conveniencia para uso rápido
def normalize_symbol(symbol: str, verbose: bool = False) -> str:
    """
    Función de conveniencia para normalizar un símbolo.
    
    Args:
        symbol: Símbolo a normalizar
        verbose: Si True, imprime el proceso
        
    Returns:
        Símbolo normalizado
    """
    return SymbolNormalizer.normalize(symbol, verbose=verbose)


# Función para uso en batch
def normalize_symbols(symbols: list, verbose: bool = False) -> list:
    """
    Función de conveniencia para normalizar múltiples símbolos.
    
    Args:
        symbols: Lista de símbolos a normalizar
        verbose: Si True, imprime el proceso
        
    Returns:
        Lista de símbolos normalizados
    """
    return SymbolNormalizer.normalize_batch(symbols, verbose=verbose)


if __name__ == "__main__":
    # Tests
    test_symbols = [
        "BTCUSD",
        "NVD",
        "PAXGUSD",
        "AAPL",
        "ETHUSD",
        "NVD.F",
        "SOLUSD",
        "MSFT",
    ]
    
    print("\n" + "="*70)
    print("TEST: Normalización de Símbolos")
    print("="*70 + "\n")
    
    for symbol in test_symbols:
        normalized = normalize_symbol(symbol, verbose=True)
    
    print("\n" + "="*70)
    print("✅ Tests completados")
    print("="*70 + "\n")
