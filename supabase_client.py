#!/usr/bin/env python3
"""
Cliente centralizado de Supabase para gestión de conexiones y operaciones comunes.
Implementa el patrón Singleton para eficiencia en conexiones.
"""

import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from supabase import create_client, Client


_ENV_LOADED = False
_SUPABASE_CLIENT: Optional[Client] = None


def ensure_env_loaded() -> None:
    """Carga variables de entorno desde .env una sola vez."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    
    try:
        from dotenv import load_dotenv
    except ImportError:
        _load_env_file()
        _ENV_LOADED = True
        return
    
    load_dotenv()
    _ENV_LOADED = True


def _load_env_file() -> None:
    """Cargador manual de .env como fallback."""
    candidate_paths = [
        Path(__file__).resolve().parent / ".env",
        Path.cwd() / ".env",
    ]
    
    for env_path in candidate_paths:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        break


def get_supabase_client() -> Client:
    """
    Retorna una instancia Singleton del cliente de Supabase.
    
    Raises:
        ValueError: Si las credenciales de Supabase no están configuradas.
    
    Returns:
        Client: Cliente de Supabase autenticado.
    """
    global _SUPABASE_CLIENT
    
    if _SUPABASE_CLIENT is not None:
        return _SUPABASE_CLIENT
    
    ensure_env_loaded()
    
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") 
        or os.environ.get("SUPABASE_ANON_KEY")
    )
    
    if not supabase_url or not supabase_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY) "
            "must be set in environment variables."
        )
    
    _SUPABASE_CLIENT = create_client(supabase_url, supabase_key)
    return _SUPABASE_CLIENT


def get_bucket_name() -> str:
    """Retorna el nombre del bucket configurado."""
    ensure_env_loaded()
    return os.environ.get("SUPABASE_BUCKET_NAME", "portfolio-files")


def get_base_prefix() -> str:
    """Retorna el prefijo base para archivos en storage."""
    ensure_env_loaded()
    return os.environ.get("SUPABASE_BASE_PREFIX", "Informes")


class SupabaseService:
    """Servicio de alto nivel para operaciones comunes en Supabase."""
    
    def __init__(self):
        self.client = get_supabase_client()
        self.bucket = get_bucket_name()
        self.base_prefix = get_base_prefix()
    
    def fetch_all_users(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los usuarios activos del sistema.
        
        Returns:
            Lista de diccionarios con información de usuarios.
        """
        try:
            response = self.client.table("users").select("*").execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []
    
    def fetch_portfolios_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los portfolios de un usuario específico.
        
        Args:
            user_id: UUID del usuario.
        
        Returns:
            Lista de portfolios del usuario.
        """
        try:
            response = (
                self.client.table("portfolios")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching portfolios for user {user_id}: {e}")
            return []
    
    def fetch_assets_by_portfolio(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene todos los assets de un portfolio específico.
        
        Args:
            portfolio_id: ID del portfolio.
        
        Returns:
            Lista de assets con sus símbolos y cantidades.
        """
        try:
            response = (
                self.client.table("assets")
                .select("*")
                .eq("portfolio_id", portfolio_id)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            print(f"Error fetching assets for portfolio {portfolio_id}: {e}")
            return []
    
    def upload_json_to_storage(
        self, 
        file_content: str, 
        file_path: str,
        overwrite: bool = True
    ) -> bool:
        """
        Sube un archivo JSON al storage de Supabase.
        
        Args:
            file_content: Contenido del archivo en formato string.
            file_path: Ruta relativa dentro del bucket.
            overwrite: Si es True, elimina el archivo existente antes de subir.
        
        Returns:
            True si la operación fue exitosa, False en caso contrario.
        """
        try:
            content_bytes = file_content.encode("utf-8")
            
            if overwrite:
                try:
                    self.client.storage.from_(self.bucket).remove([file_path])
                except Exception:
                    pass  # El archivo puede no existir
            
            self.client.storage.from_(self.bucket).upload(
                path=file_path,
                file=content_bytes,
                file_options={"content-type": "application/json;charset=utf-8"}
            )
            
            return True
        except Exception as e:
            print(f"Error uploading to storage: {e}")
            return False
    
    def download_json_from_storage(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Descarga y parsea un archivo JSON del storage.
        
        Args:
            file_path: Ruta relativa dentro del bucket.
        
        Returns:
            Diccionario con el contenido del JSON o None si falla.
        """
        try:
            import json
            content_bytes = self.client.storage.from_(self.bucket).download(file_path)
            return json.loads(content_bytes)
        except Exception:
            return None
    
    def build_storage_path(self, user_id: str, portfolio_id: int, filename: str) -> str:
        """
        Construye la ruta de storage siguiendo la estructura:
        {user_id}/{filename}
        
        Args:
            user_id: UUID del usuario (cliente).
            portfolio_id: ID del portfolio (no se usa en la ruta).
            filename: Nombre del archivo.
        
        Returns:
            Ruta completa dentro del bucket.
        """
        return f"{user_id}/{filename}"
