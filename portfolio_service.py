#!/usr/bin/env python3
"""
Servicio de gestión de portfolios para operaciones dinámicas multi-cliente.
Implementa la lógica de negocio para leer y procesar portfolios desde Supabase.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from supabase_client import SupabaseService


@dataclass
class Asset:
    """Representa un activo financiero en un portfolio."""
    asset_id: int
    portfolio_id: int
    symbol: str
    quantity: float
    acquisition_price: Optional[float] = None
    acquisition_date: Optional[str] = None
    
    @classmethod
    def from_db_record(cls, record: Dict[str, Any]) -> "Asset":
        """Construye un Asset desde un registro de base de datos."""
        return cls(
            asset_id=record.get("asset_id"),
            portfolio_id=record.get("portfolio_id"),
            symbol=record.get("asset_symbol", "").upper(),
            quantity=float(record.get("quantity", 0)),
            acquisition_price=record.get("acquisition_price"),
            acquisition_date=record.get("acquisition_date"),
        )


@dataclass
class Portfolio:
    """Representa un portfolio de inversión."""
    portfolio_id: int
    user_id: str
    portfolio_name: str
    description: Optional[str] = None
    assets: List[Asset] = None
    
    def __post_init__(self):
        if self.assets is None:
            self.assets = []
    
    @classmethod
    def from_db_record(cls, record: Dict[str, Any]) -> "Portfolio":
        """Construye un Portfolio desde un registro de base de datos."""
        return cls(
            portfolio_id=record.get("portfolio_id"),
            user_id=record.get("user_id"),
            portfolio_name=record.get("portfolio_name", ""),
            description=record.get("description"),
            assets=[],
        )
    
    def get_symbols(self) -> List[str]:
        """Retorna la lista de símbolos únicos en el portfolio."""
        return list(set(asset.symbol for asset in self.assets if asset.symbol))
    
    def has_assets(self) -> bool:
        """Verifica si el portfolio tiene assets."""
        return len(self.assets) > 0


@dataclass
class User:
    """Representa un usuario del sistema."""
    user_id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    portfolios: List[Portfolio] = None
    
    def __post_init__(self):
        if self.portfolios is None:
            self.portfolios = []
    
    @classmethod
    def from_db_record(cls, record: Dict[str, Any]) -> "User":
        """Construye un User desde un registro de base de datos."""
        return cls(
            user_id=record.get("user_id"),
            email=record.get("email", ""),
            first_name=record.get("first_name"),
            last_name=record.get("last_name"),
            portfolios=[],
        )
    
    def get_full_name(self) -> str:
        """Retorna el nombre completo del usuario."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or self.email


class PortfolioService:
    """
    Servicio de alto nivel para gestión de portfolios.
    Implementa la lógica de negocio para acceso a datos de portfolios.
    """
    
    def __init__(self):
        self.supabase_service = SupabaseService()
    
    def get_all_users_with_portfolios(self) -> List[User]:
        """
        Obtiene todos los usuarios con sus portfolios y assets cargados.
        Complejidad: O(U + P + A) donde U=usuarios, P=portfolios, A=assets.
        
        Returns:
            Lista de usuarios con sus portfolios completos.
        """
        users_data = self.supabase_service.fetch_all_users()
        users = [User.from_db_record(u) for u in users_data]
        
        for user in users:
            portfolios_data = self.supabase_service.fetch_portfolios_by_user(user.user_id)
            user.portfolios = [Portfolio.from_db_record(p) for p in portfolios_data]
            
            for portfolio in user.portfolios:
                assets_data = self.supabase_service.fetch_assets_by_portfolio(
                    portfolio.portfolio_id
                )
                portfolio.assets = [Asset.from_db_record(a) for a in assets_data]
        
        return users
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Obtiene un usuario específico con sus portfolios cargados.
        
        Args:
            user_id: UUID del usuario.
        
        Returns:
            Objeto User con portfolios o None si no existe.
        """
        try:
            response = (
                self.supabase_service.client.table("users")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            
            if not response.data:
                return None
            
            user = User.from_db_record(response.data[0])
            portfolios_data = self.supabase_service.fetch_portfolios_by_user(user_id)
            user.portfolios = [Portfolio.from_db_record(p) for p in portfolios_data]
            
            for portfolio in user.portfolios:
                assets_data = self.supabase_service.fetch_assets_by_portfolio(
                    portfolio.portfolio_id
                )
                portfolio.assets = [Asset.from_db_record(a) for a in assets_data]
            
            return user
        except Exception as e:
            print(f"Error fetching user {user_id}: {e}")
            return None
    
    def get_portfolio_by_id(self, portfolio_id: int) -> Optional[Portfolio]:
        """
        Obtiene un portfolio específico con sus assets.
        
        Args:
            portfolio_id: ID del portfolio.
        
        Returns:
            Objeto Portfolio con assets o None si no existe.
        """
        try:
            response = (
                self.supabase_service.client.table("portfolios")
                .select("*")
                .eq("portfolio_id", portfolio_id)
                .execute()
            )
            
            if not response.data:
                return None
            
            portfolio = Portfolio.from_db_record(response.data[0])
            assets_data = self.supabase_service.fetch_assets_by_portfolio(portfolio_id)
            portfolio.assets = [Asset.from_db_record(a) for a in assets_data]
            
            return portfolio
        except Exception as e:
            print(f"Error fetching portfolio {portfolio_id}: {e}")
            return None
    
    def get_all_active_portfolios(self) -> List[Portfolio]:
        """
        Obtiene todos los portfolios activos del sistema con sus assets.
        
        Returns:
            Lista de portfolios con assets cargados.
        """
        users = self.get_all_users_with_portfolios()
        portfolios = []
        
        for user in users:
            portfolios.extend(user.portfolios)
        
        return portfolios
    
    def get_portfolios_with_assets_only(self) -> List[Portfolio]:
        """
        Filtra portfolios que tienen al menos un asset.
        
        Returns:
            Lista de portfolios no vacíos.
        """
        all_portfolios = self.get_all_active_portfolios()
        return [p for p in all_portfolios if p.has_assets()]


class PortfolioTaskConfig:
    """
    Configuración para ejecutar tareas sobre un portfolio específico.
    """
    
    def __init__(
        self,
        portfolio: Portfolio,
        max_news_per_asset: int = 3,
        enable_sentiment: bool = True,
        enable_tradingview: bool = True,
        tradingview_max_pages: int = 2,
        tradingview_cutoff_hours: int = 48,
        tradingview_max_items: int = 5,
    ):
        self.portfolio = portfolio
        self.max_news_per_asset = max_news_per_asset
        self.enable_sentiment = enable_sentiment
        self.enable_tradingview = enable_tradingview
        self.tradingview_max_pages = tradingview_max_pages
        self.tradingview_cutoff_hours = tradingview_cutoff_hours
        self.tradingview_max_items = tradingview_max_items
    
    def get_symbols(self) -> List[str]:
        """Retorna los símbolos del portfolio para scraping."""
        return self.portfolio.get_symbols()
    
    def get_storage_path(self) -> str:
        """Construye la ruta de storage para el resultado."""
        supabase_service = SupabaseService()
        return supabase_service.build_storage_path(
            user_id=self.portfolio.user_id,
            portfolio_id=self.portfolio.portfolio_id,
            filename="portfolio_news.json"
        )
    
    def __repr__(self) -> str:
        return (
            f"PortfolioTaskConfig("
            f"user={self.portfolio.user_id[:8]}..., "
            f"portfolio={self.portfolio.portfolio_name}, "
            f"assets={len(self.portfolio.assets)})"
        )
