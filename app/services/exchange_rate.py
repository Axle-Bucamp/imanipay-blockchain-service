"""
Exchange rate service for ImaniPay Blockchain Service.

This module provides real-time exchange rate management and currency
conversion functionality for the payment platform.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID

import httpx
from sqlalchemy import select, update, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database import get_async_session_context
from app.models import ExchangeRate
from app.schemas import ExchangeRate as ExchangeRateSchema

logger = logging.getLogger(__name__)
settings = get_settings()


class ExchangeRateError(Exception):
    """Base exception for exchange rate errors."""
    pass


class RateProviderError(ExchangeRateError):
    """Exception raised when rate provider fails."""
    pass


class ExchangeRateService:
    """Comprehensive exchange rate management service."""
    
    def __init__(self):
        self.logger = logger
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Rate providers configuration
        self.providers = {
            "coinbase": {
                "base_url": "https://api.coinbase.com/v2/exchange-rates",
                "api_key": None,  # Public API
                "weight": 0.3
            },
            "coingecko": {
                "base_url": "https://api.coingecko.com/api/v3",
                "api_key": None,  # Public API
                "weight": 0.3
            },
            "exchangerate_api": {
                "base_url": "https://api.exchangerate-api.com/v4/latest",
                "api_key": None,  # Public API
                "weight": 0.2
            },
            "fixer": {
                "base_url": "https://api.fixer.io/latest",
                "api_key": None,  # Requires API key
                "weight": 0.2
            }
        }
        
        # Currency mappings
        self.crypto_currencies = {
            "ALGO": "algorand",
            "USDC": "usd-coin",
            "BTC": "bitcoin",
            "ETH": "ethereum"
        }
        
        self.fiat_currencies = {
            "USD", "EUR", "GBP", "NGN", "KES", "GHS", "ZAR", "XOF", "XAF"
        }
        
        # Cache settings
        self.cache_duration = timedelta(minutes=5)  # 5-minute cache
        self.stale_threshold = timedelta(minutes=15)  # 15-minute stale threshold
    
    # ========================================================================
    # Public API Methods
    # ========================================================================
    
    async def get_exchange_rate(
        self,
        base_currency: str,
        quote_currency: str,
        session: Optional[AsyncSession] = None
    ) -> Optional[ExchangeRateSchema]:
        """
        Get exchange rate between two currencies.
        
        Args:
            base_currency: Base currency code
            quote_currency: Quote currency code
            session: Database session
            
        Returns:
            ExchangeRateSchema: Exchange rate or None if not available
        """
        async def _get_rate(db_session: AsyncSession) -> Optional[ExchangeRateSchema]:
            # Try to get cached rate first
            cached_rate = await self._get_cached_rate(base_currency, quote_currency, db_session)
            
            if cached_rate and not self._is_rate_stale(cached_rate):
                return ExchangeRateSchema.model_validate(cached_rate)
            
            # Fetch fresh rate if cache is stale or missing
            try:
                fresh_rate = await self._fetch_and_store_rate(
                    base_currency, quote_currency, db_session
                )
                if fresh_rate:
                    return ExchangeRateSchema.model_validate(fresh_rate)
            except Exception as e:
                self.logger.error(f"Failed to fetch fresh rate for {base_currency}/{quote_currency}: {e}")
                
                # Return stale rate if available
                if cached_rate:
                    self.logger.warning(f"Using stale rate for {base_currency}/{quote_currency}")
                    return ExchangeRateSchema.model_validate(cached_rate)
            
            return None
        
        if session:
            return await _get_rate(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_rate(db_session)
    
    async def get_multiple_rates(
        self,
        base_currency: str,
        quote_currencies: List[str],
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Optional[ExchangeRateSchema]]:
        """
        Get exchange rates for multiple currency pairs.
        
        Args:
            base_currency: Base currency code
            quote_currencies: List of quote currency codes
            session: Database session
            
        Returns:
            Dict[str, Optional[ExchangeRateSchema]]: Exchange rates by quote currency
        """
        async def _get_multiple_rates(db_session: AsyncSession) -> Dict[str, Optional[ExchangeRateSchema]]:
            rates = {}
            
            # Use asyncio.gather for concurrent rate fetching
            tasks = [
                self.get_exchange_rate(base_currency, quote_currency, db_session)
                for quote_currency in quote_currencies
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for quote_currency, result in zip(quote_currencies, results):
                if isinstance(result, Exception):
                    self.logger.error(f"Failed to get rate for {base_currency}/{quote_currency}: {result}")
                    rates[quote_currency] = None
                else:
                    rates[quote_currency] = result
            
            return rates
        
        if session:
            return await _get_multiple_rates(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_multiple_rates(db_session)
    
    async def convert_amount(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        session: Optional[AsyncSession] = None
    ) -> Optional[Decimal]:
        """
        Convert amount between currencies.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            session: Database session
            
        Returns:
            Decimal: Converted amount or None if rate unavailable
        """
        if from_currency == to_currency:
            return amount
        
        rate = await self.get_exchange_rate(from_currency, to_currency, session)
        
        if rate:
            return amount * rate.rate
        
        return None
    
    async def get_supported_currencies(
        self,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, List[str]]:
        """
        Get list of supported currencies.
        
        Args:
            session: Database session
            
        Returns:
            Dict[str, List[str]]: Supported currencies by type
        """
        async def _get_supported(db_session: AsyncSession) -> Dict[str, List[str]]:
            # Get currencies from database
            result = await db_session.execute(
                select(ExchangeRate.base_currency, ExchangeRate.quote_currency)
                .where(ExchangeRate.is_active == True)
                .distinct()
            )
            
            db_currencies = set()
            for base, quote in result.fetchall():
                db_currencies.add(base)
                db_currencies.add(quote)
            
            # Combine with known currencies
            all_currencies = db_currencies | self.fiat_currencies | set(self.crypto_currencies.keys())
            
            return {
                "fiat": sorted(list(self.fiat_currencies & all_currencies)),
                "crypto": sorted(list(set(self.crypto_currencies.keys()) & all_currencies)),
                "all": sorted(list(all_currencies))
            }
        
        if session:
            return await _get_supported(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_supported(db_session)
    
    # ========================================================================
    # Rate Fetching and Management
    # ========================================================================
    
    async def refresh_all_rates(
        self,
        session: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Refresh all exchange rates from providers.
        
        Args:
            session: Database session
            
        Returns:
            Dict[str, Any]: Refresh results
        """
        async def _refresh_all(db_session: AsyncSession) -> Dict[str, Any]:
            results = {
                "success": 0,
                "failed": 0,
                "errors": [],
                "updated_pairs": []
            }
            
            # Define currency pairs to refresh
            currency_pairs = [
                # Crypto to USD
                ("ALGO", "USD"), ("USDC", "USD"), ("BTC", "USD"), ("ETH", "USD"),
                # USD to African currencies
                ("USD", "NGN"), ("USD", "KES"), ("USD", "GHS"), ("USD", "ZAR"),
                # EUR to African currencies
                ("EUR", "NGN"), ("EUR", "KES"), ("EUR", "GHS"), ("EUR", "ZAR"),
                # Cross rates
                ("EUR", "USD"), ("GBP", "USD"),
            ]
            
            # Refresh rates concurrently
            tasks = [
                self._fetch_and_store_rate(base, quote, db_session)
                for base, quote in currency_pairs
            ]
            
            rate_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for (base, quote), result in zip(currency_pairs, rate_results):
                if isinstance(result, Exception):
                    results["failed"] += 1
                    results["errors"].append(f"{base}/{quote}: {str(result)}")
                elif result:
                    results["success"] += 1
                    results["updated_pairs"].append(f"{base}/{quote}")
                else:
                    results["failed"] += 1
                    results["errors"].append(f"{base}/{quote}: No rate returned")
            
            self.logger.info(f"Rate refresh completed: {results['success']} success, {results['failed']} failed")
            return results
        
        if session:
            return await _refresh_all(session)
        else:
            async with get_async_session_context() as db_session:
                return await _refresh_all(db_session)
    
    async def cleanup_old_rates(
        self,
        days_to_keep: int = 30,
        session: Optional[AsyncSession] = None
    ) -> int:
        """
        Clean up old exchange rate records.
        
        Args:
            days_to_keep: Number of days to keep
            session: Database session
            
        Returns:
            int: Number of records deleted
        """
        async def _cleanup(db_session: AsyncSession) -> int:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Keep the latest rate for each pair, delete older ones
            result = await db_session.execute(
                select(ExchangeRate.id)
                .where(ExchangeRate.created_at < cutoff_date)
            )
            
            old_rate_ids = [row[0] for row in result.fetchall()]
            
            if old_rate_ids:
                # Delete old rates
                await db_session.execute(
                    update(ExchangeRate)
                    .where(ExchangeRate.id.in_(old_rate_ids))
                    .values(is_active=False)
                )
                await db_session.commit()
            
            self.logger.info(f"Cleaned up {len(old_rate_ids)} old exchange rate records")
            return len(old_rate_ids)
        
        if session:
            return await _cleanup(session)
        else:
            async with get_async_session_context() as db_session:
                return await _cleanup(db_session)
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _get_cached_rate(
        self,
        base_currency: str,
        quote_currency: str,
        session: AsyncSession
    ) -> Optional[ExchangeRate]:
        """Get cached exchange rate from database."""
        result = await session.execute(
            select(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.base_currency == base_currency,
                    ExchangeRate.quote_currency == quote_currency,
                    ExchangeRate.is_active == True
                )
            )
            .order_by(desc(ExchangeRate.created_at))
            .limit(1)
        )
        
        return result.scalar_one_or_none()
    
    def _is_rate_stale(self, rate: ExchangeRate) -> bool:
        """Check if exchange rate is stale."""
        age = datetime.utcnow() - rate.created_at
        return age > self.cache_duration
    
    async def _fetch_and_store_rate(
        self,
        base_currency: str,
        quote_currency: str,
        session: AsyncSession
    ) -> Optional[ExchangeRate]:
        """Fetch rate from providers and store in database."""
        try:
            # Determine the best approach based on currency types
            if base_currency in self.crypto_currencies and quote_currency in self.fiat_currencies:
                # Crypto to fiat
                rate_data = await self._fetch_crypto_to_fiat_rate(base_currency, quote_currency)
            elif base_currency in self.fiat_currencies and quote_currency in self.fiat_currencies:
                # Fiat to fiat
                rate_data = await self._fetch_fiat_to_fiat_rate(base_currency, quote_currency)
            elif base_currency in self.fiat_currencies and quote_currency in self.crypto_currencies:
                # Fiat to crypto (inverse of crypto to fiat)
                inverse_rate = await self._fetch_crypto_to_fiat_rate(quote_currency, base_currency)
                if inverse_rate:
                    rate_data = {
                        "rate": 1 / inverse_rate["rate"],
                        "source": inverse_rate["source"],
                        "bid_rate": 1 / inverse_rate["ask_rate"] if inverse_rate.get("ask_rate") else None,
                        "ask_rate": 1 / inverse_rate["bid_rate"] if inverse_rate.get("bid_rate") else None,
                    }
                else:
                    rate_data = None
            else:
                # Crypto to crypto or unsupported
                rate_data = await self._fetch_crypto_to_crypto_rate(base_currency, quote_currency)
            
            if not rate_data:
                return None
            
            # Store rate in database
            exchange_rate = ExchangeRate(
                base_currency=base_currency,
                quote_currency=quote_currency,
                rate=Decimal(str(rate_data["rate"])),
                source=rate_data["source"],
                bid_rate=Decimal(str(rate_data["bid_rate"])) if rate_data.get("bid_rate") else None,
                ask_rate=Decimal(str(rate_data["ask_rate"])) if rate_data.get("ask_rate") else None,
                spread=Decimal(str(rate_data["spread"])) if rate_data.get("spread") else None,
                volume_24h=Decimal(str(rate_data["volume_24h"])) if rate_data.get("volume_24h") else None,
                valid_from=datetime.utcnow(),
                valid_until=datetime.utcnow() + self.cache_duration,
                is_active=True
            )
            
            session.add(exchange_rate)
            await session.commit()
            await session.refresh(exchange_rate)
            
            return exchange_rate
            
        except Exception as e:
            self.logger.error(f"Failed to fetch and store rate for {base_currency}/{quote_currency}: {e}")
            return None
    
    async def _fetch_crypto_to_fiat_rate(
        self,
        crypto_currency: str,
        fiat_currency: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch crypto to fiat exchange rate."""
        try:
            # Try CoinGecko first
            coingecko_id = self.crypto_currencies.get(crypto_currency)
            if coingecko_id:
                url = f"{self.providers['coingecko']['base_url']}/simple/price"
                params = {
                    "ids": coingecko_id,
                    "vs_currencies": fiat_currency.lower(),
                    "include_24hr_vol": "true"
                }
                
                response = await self.http_client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if coingecko_id in data and fiat_currency.lower() in data[coingecko_id]:
                    rate = data[coingecko_id][fiat_currency.lower()]
                    volume_key = f"{fiat_currency.lower()}_24h_vol"
                    volume = data[coingecko_id].get(volume_key)
                    
                    return {
                        "rate": rate,
                        "source": "coingecko",
                        "volume_24h": volume
                    }
            
            # Fallback to Coinbase
            if fiat_currency == "USD":
                url = f"{self.providers['coinbase']['base_url']}"
                params = {"currency": crypto_currency}
                
                response = await self.http_client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if "data" in data and "rates" in data["data"]:
                    rates = data["data"]["rates"]
                    if "USD" in rates:
                        return {
                            "rate": float(rates["USD"]),
                            "source": "coinbase"
                        }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to fetch crypto rate {crypto_currency}/{fiat_currency}: {e}")
            return None
    
    async def _fetch_fiat_to_fiat_rate(
        self,
        base_currency: str,
        quote_currency: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch fiat to fiat exchange rate."""
        try:
            # Try ExchangeRate-API
            url = f"{self.providers['exchangerate_api']['base_url']}/{base_currency}"
            
            response = await self.http_client.get(url)
            response.raise_for_status()
            
            data = response.json()
            if "rates" in data and quote_currency in data["rates"]:
                return {
                    "rate": data["rates"][quote_currency],
                    "source": "exchangerate_api"
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to fetch fiat rate {base_currency}/{quote_currency}: {e}")
            return None
    
    async def _fetch_crypto_to_crypto_rate(
        self,
        base_currency: str,
        quote_currency: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch crypto to crypto exchange rate via USD."""
        try:
            # Get both currencies in USD, then calculate cross rate
            base_usd_rate = await self._fetch_crypto_to_fiat_rate(base_currency, "USD")
            quote_usd_rate = await self._fetch_crypto_to_fiat_rate(quote_currency, "USD")
            
            if base_usd_rate and quote_usd_rate:
                cross_rate = base_usd_rate["rate"] / quote_usd_rate["rate"]
                return {
                    "rate": cross_rate,
                    "source": f"{base_usd_rate['source']}_cross"
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to fetch crypto cross rate {base_currency}/{quote_currency}: {e}")
            return None
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    async def get_rate_history(
        self,
        base_currency: str,
        quote_currency: str,
        days: int = 30,
        session: Optional[AsyncSession] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical exchange rates.
        
        Args:
            base_currency: Base currency
            quote_currency: Quote currency
            days: Number of days of history
            session: Database session
            
        Returns:
            List[Dict[str, Any]]: Historical rates
        """
        async def _get_history(db_session: AsyncSession) -> List[Dict[str, Any]]:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            result = await db_session.execute(
                select(ExchangeRate)
                .where(
                    and_(
                        ExchangeRate.base_currency == base_currency,
                        ExchangeRate.quote_currency == quote_currency,
                        ExchangeRate.created_at >= start_date
                    )
                )
                .order_by(ExchangeRate.created_at)
            )
            
            rates = result.scalars().all()
            
            return [
                {
                    "timestamp": rate.created_at.isoformat(),
                    "rate": float(rate.rate),
                    "source": rate.source,
                    "volume_24h": float(rate.volume_24h) if rate.volume_24h else None
                }
                for rate in rates
            ]
        
        if session:
            return await _get_history(session)
        else:
            async with get_async_session_context() as db_session:
                return await _get_history(db_session)
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()

