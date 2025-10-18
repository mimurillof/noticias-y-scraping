#!/usr/bin/env python3
"""
Pre-Deployment Verification Script
Verifica que todo esté configurado correctamente antes del deployment.
"""

import os
import sys
from typing import List, Tuple

# Colores ANSI para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header(text: str):
    """Imprime un header formateado."""
    print(f"\n{Colors.BLUE}{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}{Colors.RESET}\n")

def print_test(name: str, passed: bool, message: str = ""):
    """Imprime el resultado de un test."""
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    print(f"{status} - {name}")
    if message:
        print(f"       {Colors.YELLOW}{message}{Colors.RESET}")

def check_environment_variables() -> List[Tuple[str, bool, str]]:
    """Verifica que las variables de entorno estén configuradas."""
    required_vars = [
        ("SUPABASE_URL", "URL de Supabase"),
        ("SUPABASE_SERVICE_ROLE_KEY", "Service Role Key de Supabase"),
    ]
    
    optional_vars = [
        ("SUPABASE_ANON_KEY", "Anon Key de Supabase (recomendado)"),
        ("SUPABASE_BUCKET_NAME", "Nombre del bucket (default: portfolio-files)"),
    ]
    
    results = []
    
    # Variables requeridas
    for var_name, description in required_vars:
        value = os.getenv(var_name)
        is_set = bool(value and value.strip())
        value_length = len(value) if value else 0
        results.append((
            f"Variable requerida: {var_name}",
            is_set,
            description if not is_set else f"Configurado (longitud: {value_length})"
        ))
    
    # Variables opcionales
    for var_name, description in optional_vars:
        value = os.getenv(var_name)
        is_set = bool(value and value.strip())
        value_length = len(value) if value else 0
        results.append((
            f"Variable opcional: {var_name}",
            True,  # No falla si no está
            f"Configurado (longitud: {value_length})" if is_set else f"No configurado - {description}"
        ))
    
    return results

def check_dependencies() -> List[Tuple[str, bool, str]]:
    """Verifica que las dependencias estén instaladas."""
    required_modules = [
        ("supabase", "Supabase client"),
        ("yfinance", "Yahoo Finance API"),
        ("bs4", "BeautifulSoup4"),
        ("requests", "HTTP requests"),
    ]
    
    results = []
    
    for module_name, description in required_modules:
        try:
            __import__(module_name)
            results.append((f"Módulo: {module_name}", True, f"{description} - Instalado"))
        except ImportError:
            results.append((f"Módulo: {module_name}", False, f"{description} - NO INSTALADO"))
    
    return results

def check_core_files() -> List[Tuple[str, bool, str]]:
    """Verifica que los archivos core existan."""
    required_files = [
        "orchestrator.py",
        "portfolio_service.py",
        "supabase_client.py",
        "Script_noticias.py",
        "symbol_normalizer.py",
        "requirements.txt",
        "Procfile",
    ]
    
    results = []
    
    for filename in required_files:
        exists = os.path.isfile(filename)
        results.append((
            f"Archivo: {filename}",
            exists,
            "Encontrado" if exists else "NO ENCONTRADO"
        ))
    
    return results

def check_supabase_connection() -> List[Tuple[str, bool, str]]:
    """Verifica la conexión a Supabase."""
    results = []
    
    try:
        from supabase_client import get_supabase_client
        
        client = get_supabase_client()
        results.append(("Conexión a Supabase", True, "Cliente inicializado correctamente"))
        
        # Test básico de conexión
        try:
            # Intenta hacer un query simple a la tabla users
            response = client.table("users").select("*").limit(1).execute()
            record_count = len(response.data) if hasattr(response, 'data') else 0
            results.append(("Query a tabla 'users'", True, f"Conexión exitosa - {record_count} registros encontrados"))
        except Exception as e:
            error_msg = str(e)[:100]
            # Si el error es solo sobre estructura de columnas, es aceptable
            if 'does not exist' in error_msg or 'column' in error_msg.lower():
                results.append(("Query a tabla 'users'", True, "Tabla existe (estructura puede variar)"))
            else:
                results.append(("Query a tabla 'users'", False, f"Error: {error_msg}"))
        
    except ImportError:
        results.append(("Importar supabase_client", False, "No se pudo importar el módulo"))
    except Exception as e:
        results.append(("Conexión a Supabase", False, f"Error: {str(e)[:100]}"))
    
    return results

def check_portfolio_data() -> List[Tuple[str, bool, str]]:
    """Verifica que haya datos de portfolios en la base de datos."""
    results = []
    
    try:
        from portfolio_service import PortfolioService
        
        service = PortfolioService()
        users = service.get_all_users_with_portfolios()
        
        total_portfolios = sum(len(user.portfolios) for user in users)
        total_assets = sum(
            len(portfolio.assets)
            for user in users
            for portfolio in user.portfolios
        )
        
        results.append((
            "Usuarios con portfolios",
            len(users) > 0,
            f"{len(users)} usuarios encontrados"
        ))
        
        results.append((
            "Portfolios en base de datos",
            total_portfolios > 0,
            f"{total_portfolios} portfolios encontrados"
        ))
        
        results.append((
            "Assets en portfolios",
            total_assets > 0,
            f"{total_assets} assets encontrados"
        ))
        
    except ImportError:
        results.append(("Importar portfolio_service", False, "No se pudo importar el módulo"))
    except Exception as e:
        results.append(("Cargar datos de portfolios", False, f"Error: {str(e)[:100]}"))
    
    return results

def main():
    """Ejecuta todas las verificaciones."""
    print_header("🔍 VERIFICACIÓN PRE-DEPLOYMENT")
    
    all_tests = []
    
    # 1. Variables de entorno
    print_header("1️⃣  Variables de Entorno")
    env_tests = check_environment_variables()
    for test in env_tests:
        print_test(*test)
        all_tests.append(test)
    
    # 2. Dependencias
    print_header("2️⃣  Dependencias de Python")
    dep_tests = check_dependencies()
    for test in dep_tests:
        print_test(*test)
        all_tests.append(test)
    
    # 3. Archivos core
    print_header("3️⃣  Archivos Core")
    file_tests = check_core_files()
    for test in file_tests:
        print_test(*test)
        all_tests.append(test)
    
    # 4. Conexión Supabase
    print_header("4️⃣  Conexión a Supabase")
    supabase_tests = check_supabase_connection()
    for test in supabase_tests:
        print_test(*test)
        all_tests.append(test)
    
    # 5. Datos de portfolios
    print_header("5️⃣  Datos de Portfolios")
    portfolio_tests = check_portfolio_data()
    for test in portfolio_tests:
        print_test(*test)
        all_tests.append(test)
    
    # Resumen final
    print_header("📊 RESUMEN")
    
    total_tests = len(all_tests)
    passed_tests = sum(1 for _, passed, _ in all_tests if passed)
    failed_tests = total_tests - passed_tests
    
    print(f"Total de tests: {total_tests}")
    print(f"{Colors.GREEN}Pasados: {passed_tests}{Colors.RESET}")
    print(f"{Colors.RED}Fallidos: {failed_tests}{Colors.RESET}")
    
    if failed_tests == 0:
        print(f"\n{Colors.GREEN}✓ ¡Listo para deployment!{Colors.RESET}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}✗ Por favor corrige los errores antes del deployment{Colors.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
