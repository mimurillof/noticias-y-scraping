#!/usr/bin/env python3
"""
Orquestador multi-cliente para procesamiento paralelo de portfolios.
Implementa el patrón Strategy para procesamiento eficiente de múltiples clientes.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from portfolio_service import PortfolioService, PortfolioTaskConfig, Portfolio
from supabase_client import SupabaseService
from Script_noticias import build_payload as build_news_payload
from scrape_sentiment import get_fear_and_greed_index
# BYPASS: Reemplazamos TradingView por Expert Analysis (Medium + Seeking Alpha)
# Los datos se guardan en el mismo campo 'tradingview_ideas' para evitar cambios en el frontend
from expert_analysis import collect_expert_analysis


class PortfolioTaskExecutor:
    """
    Ejecutor de tareas para un portfolio individual.
    Encapsula toda la lógica de scraping para un portfolio.
    """
    
    def __init__(self, config: PortfolioTaskConfig):
        self.config = config
        self.supabase_service = SupabaseService()
    
    def execute(self) -> Dict[str, Any]:
        """
        Ejecuta todas las tareas configuradas para el portfolio.
        
        Returns:
            Diccionario con los resultados del procesamiento.
        """
        portfolio = self.config.portfolio
        symbols = self.config.get_symbols()
        storage_path = self.config.get_storage_path()
        
        print(f"\n{'='*70}")
        print(f"Processing Portfolio: {portfolio.portfolio_name}")
        print(f"User: {portfolio.user_id[:8]}...")
        print(f"Assets: {len(portfolio.assets)} | Symbols: {symbols}")
        print(f"{'='*70}")
        
        result = {
            "portfolio_id": portfolio.portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "user_id": portfolio.user_id,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "status": "pending",
            "errors": [],
        }
        
        # 1. Market Sentiment (global, una vez por batch)
        sentiment = None
        if self.config.enable_sentiment:
            print("  [1/3] Fetching market sentiment...")
            try:
                sentiment = get_fear_and_greed_index()
                if sentiment:
                    print(f"    ✓ Sentiment: {sentiment['value']} ({sentiment['description']})")
                else:
                    print("    ✗ Could not fetch sentiment")
                    result["errors"].append("sentiment_fetch_failed")
            except Exception as e:
                print(f"    ✗ Error: {e}")
                result["errors"].append(f"sentiment_error: {str(e)}")
        
        # 2. Portfolio News
        print("  [2/3] Fetching portfolio news...")
        news_payload = {"portfolio_news": []}
        try:
            if symbols:
                news_payload = build_news_payload(
                    tickers=symbols,
                    max_items=self.config.max_news_per_asset,
                    remote_path=storage_path
                )
                print(f"    ✓ Fetched {len(news_payload.get('portfolio_news', []))} news items")
            else:
                print("    ⚠ No symbols to fetch news for")
        except Exception as e:
            print(f"    ✗ Error: {e}")
            result["errors"].append(f"news_error: {str(e)}")
        
        # 3. Expert Analysis (Bypass: reemplaza TradingView, misma estructura JSON)
        tradingview_ideas = []  # Mantenemos el nombre para compatibilidad con frontend
        if self.config.enable_tradingview:
            print("  [3/3] Fetching Expert Analysis (Medium + Seeking Alpha)...")
            try:
                tradingview_ideas = collect_expert_analysis(
                    portfolio_tickers=symbols,  # Pasamos los símbolos del portfolio
                    max_items=self.config.tradingview_max_items,
                )
                print(f"    ✓ Collected {len(tradingview_ideas)} expert analyses")
            except Exception as e:
                print(f"    ✗ Error: {e}")
                result["errors"].append(f"expert_analysis_error: {str(e)}")
        
        # Consolidate final payload
        final_payload = {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "portfolio_id": portfolio.portfolio_id,
            "portfolio_name": portfolio.portfolio_name,
            "user_id": portfolio.user_id,
            "market_sentiment": sentiment,
            "portfolio_news": news_payload.get("portfolio_news", []),
            "tradingview_ideas": tradingview_ideas,
            "assets": [
                {
                    "symbol": asset.symbol,
                    "quantity": asset.quantity,
                    "acquisition_price": asset.acquisition_price,
                }
                for asset in portfolio.assets
            ],
        }
        
        # Upload to Supabase
        print("  [Upload] Saving to Supabase Storage...")
        try:
            json_content = json.dumps(final_payload, ensure_ascii=False, indent=2)
            success = self.supabase_service.upload_json_to_storage(
                file_content=json_content,
                file_path=storage_path,
                overwrite=True
            )
            
            if success:
                print(f"    ✓ Uploaded to: {storage_path}")
                result["status"] = "success"
                result["storage_path"] = storage_path
            else:
                print(f"    ✗ Failed to upload")
                result["status"] = "upload_failed"
                result["errors"].append("upload_failed")
        except Exception as e:
            print(f"    ✗ Upload error: {e}")
            result["status"] = "upload_error"
            result["errors"].append(f"upload_error: {str(e)}")
        
        print(f"  Status: {result['status'].upper()}")
        return result


class MultiClientOrchestrator:
    """
    Orquestador principal para procesamiento multi-cliente.
    Implementa procesamiento paralelo eficiente usando ThreadPoolExecutor.
    """
    
    def __init__(self, max_workers: int = 3):
        """
        Args:
            max_workers: Número máximo de threads para procesamiento paralelo.
                        Default=3 para evitar rate limiting en APIs externas.
        """
        self.portfolio_service = PortfolioService()
        self.max_workers = max_workers
    
    def run_all_portfolios(
        self,
        parallel: bool = True,
        filter_user_id: Optional[str] = None,
        filter_portfolio_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta el procesamiento para todos los portfolios activos.
        
        Args:
            parallel: Si True, procesa portfolios en paralelo.
            filter_user_id: Si se proporciona, procesa solo portfolios de este usuario.
            filter_portfolio_id: Si se proporciona, procesa solo este portfolio.
        
        Returns:
            Resumen del procesamiento con estadísticas y resultados.
        """
        print("\n" + "="*70)
        print("MULTI-CLIENT PORTFOLIO ORCHESTRATOR")
        print("="*70)
        
        # Fetch portfolios
        if filter_portfolio_id:
            print(f"Loading portfolio {filter_portfolio_id}...")
            portfolio = self.portfolio_service.get_portfolio_by_id(filter_portfolio_id)
            portfolios = [portfolio] if portfolio else []
        elif filter_user_id:
            print(f"Loading portfolios for user {filter_user_id[:8]}...")
            user = self.portfolio_service.get_user_by_id(filter_user_id)
            portfolios = user.portfolios if user else []
        else:
            print("Loading all active portfolios...")
            portfolios = self.portfolio_service.get_portfolios_with_assets_only()
        
        if not portfolios:
            print("⚠ No portfolios found matching the criteria.")
            return {
                "status": "no_portfolios",
                "total_portfolios": 0,
                "results": [],
            }
        
        print(f"✓ Found {len(portfolios)} portfolio(s) to process")
        
        # Create task configs
        configs = [self._create_task_config(p) for p in portfolios]
        
        # Execute tasks
        start_time = datetime.now(timezone.utc)
        
        if parallel and len(configs) > 1:
            results = self._execute_parallel(configs)
        else:
            results = self._execute_sequential(configs)
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Generate summary
        summary = self._generate_summary(results, duration)
        self._print_summary(summary)
        
        return summary
    
    def _create_task_config(self, portfolio: Portfolio) -> PortfolioTaskConfig:
        """Crea la configuración para una tarea de portfolio."""
        return PortfolioTaskConfig(
            portfolio=portfolio,
            max_news_per_asset=3,
            enable_sentiment=True,
            enable_tradingview=True,
            tradingview_max_pages=2,
            tradingview_cutoff_hours=48,
            tradingview_max_items=5,
        )
    
    def _execute_parallel(self, configs: List[PortfolioTaskConfig]) -> List[Dict[str, Any]]:
        """Ejecuta las tareas en paralelo usando ThreadPoolExecutor."""
        print(f"\n▶ Parallel execution mode (max_workers={self.max_workers})")
        
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._execute_task, config): config
                for config in configs
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    config = futures[future]
                    print(f"✗ Task failed for {config.portfolio.portfolio_name}: {e}")
                    results.append({
                        "portfolio_id": config.portfolio.portfolio_id,
                        "status": "exception",
                        "errors": [str(e)],
                    })
        
        return results
    
    def _execute_sequential(self, configs: List[PortfolioTaskConfig]) -> List[Dict[str, Any]]:
        """Ejecuta las tareas secuencialmente."""
        print(f"\n▶ Sequential execution mode")
        
        results = []
        for config in configs:
            try:
                result = self._execute_task(config)
                results.append(result)
            except Exception as e:
                print(f"✗ Task failed for {config.portfolio.portfolio_name}: {e}")
                results.append({
                    "portfolio_id": config.portfolio.portfolio_id,
                    "status": "exception",
                    "errors": [str(e)],
                })
        
        return results
    
    def _execute_task(self, config: PortfolioTaskConfig) -> Dict[str, Any]:
        """Ejecuta una tarea individual."""
        executor = PortfolioTaskExecutor(config)
        return executor.execute()
    
    def _generate_summary(
        self, 
        results: List[Dict[str, Any]], 
        duration: float
    ) -> Dict[str, Any]:
        """Genera un resumen estadístico del procesamiento."""
        total = len(results)
        successful = sum(1 for r in results if r.get("status") == "success")
        failed = total - successful
        
        return {
            "orchestration_completed_at": datetime.now(tz=timezone.utc).isoformat(),
            "total_duration_seconds": round(duration, 2),
            "statistics": {
                "total_portfolios": total,
                "successful": successful,
                "failed": failed,
                "success_rate": round((successful / total * 100) if total > 0 else 0, 2),
            },
            "results": results,
        }
    
    def _print_summary(self, summary: Dict[str, Any]) -> None:
        """Imprime un resumen visual del procesamiento."""
        stats = summary["statistics"]
        
        print("\n" + "="*70)
        print("EXECUTION SUMMARY")
        print("="*70)
        print(f"Total Duration: {summary['total_duration_seconds']}s")
        print(f"Total Portfolios: {stats['total_portfolios']}")
        print(f"✓ Successful: {stats['successful']}")
        print(f"✗ Failed: {stats['failed']}")
        print(f"Success Rate: {stats['success_rate']}%")
        print("="*70 + "\n")


def main():
    """Punto de entrada principal."""
    import os
    
    # Leer configuración de variables de entorno
    filter_user_id = os.environ.get("FILTER_USER_ID")
    filter_portfolio_id_str = os.environ.get("FILTER_PORTFOLIO_ID")
    filter_portfolio_id = int(filter_portfolio_id_str) if filter_portfolio_id_str else None
    parallel = os.environ.get("PARALLEL_EXECUTION", "true").lower() == "true"
    max_workers = int(os.environ.get("MAX_WORKERS", "3"))
    
    orchestrator = MultiClientOrchestrator(max_workers=max_workers)
    
    summary = orchestrator.run_all_portfolios(
        parallel=parallel,
        filter_user_id=filter_user_id,
        filter_portfolio_id=filter_portfolio_id,
    )
    
    # Guardar resumen de ejecución
    summary_path = "orchestration_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"Orchestration summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
