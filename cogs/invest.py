import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List
from guild_config import MY_GUILD

class Investment(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.UPDATE_CHANNEL_ID = 1301273876558512253
        self.data_path = Path(__file__).parent.parent / 'data' / 'crypto_prices.json'
        self.last_message = None  # Armazenar última mensagem
        
        # Binance API endpoints
        self.BINANCE_BASE_URL = "https://api.binance.com/api/v3"
        
        # símbolos das criptomoedas
        self.CRYPTO_SYMBOLS = {
            'BTCUSDT': 'bitcoin',
            'ETHUSDT': 'ethereum',
            'LTCUSDT': 'litecoin'  # Trocado de BNBUSDT para LTCUSDT
        }
        
        # cores para cada cripto
        self.CRYPTO_COLORS = {
            'BTCUSDT': 0xF7931A,    # laranja bitcoin
            'ETHUSDT': 0x627EEA,    # azul ethereum
            'LTCUSDT': 0x345D9D     # azul litecoin
        }
        
        self.MAX_MESSAGES = 10  # Maximum number of messages to keep in channel
        
        # Start background tasks
        self.price_update_loop.start()
        
    def cog_unload(self):
        self.price_update_loop.cancel()

    def ensure_data_file(self):
        """Create data file if it doesn't exist"""
        try:
            self.data_path.parent.mkdir(exist_ok=True)
            if not self.data_path.exists():
                # Initialize with empty prices list
                with open(self.data_path, 'w') as f:
                    json.dump({"prices": []}, f, indent=2)
            else:
                # Validate existing file
                try:
                    with open(self.data_path, 'r') as f:
                        data = json.load(f)
                        if not isinstance(data, dict) or "prices" not in data:
                            raise ValueError("Invalid data structure")
                except (json.JSONDecodeError, ValueError):
                    # If file is corrupt, recreate it
                    with open(self.data_path, 'w') as f:
                        json.dump({"prices": []}, f, indent=2)
        except Exception as e:
            print(f"Error ensuring data file: {e}")

    def load_price_data(self) -> List:
        """Load price data from JSON file"""
        try:
            with open(self.data_path, 'r') as f:
                data = json.load(f)
                if not isinstance(data, dict) or "prices" not in data:
                    return []
                return data["prices"]
        except json.JSONDecodeError:
            print("Error: Invalid JSON in price data file")
            return []
        except Exception as e:
            print(f"Error loading price data: {e}")
            return []

    def store_price(self, symbol: str, price: float):
        """Store price in JSON file with optimized storage"""
        try:
            prices = self.load_price_data()
            
            # Create timestamp for current entry
            current_time = datetime.now()
            
            # Filter existing prices to keep only last 24h
            # and remove entries of same symbol within 1-minute window
            valid_prices = []
            cutoff = (current_time - timedelta(hours=24)).isoformat()
            seen_timestamps = {}
            
            for p in prices:
                # Skip if entry is older than 24h
                if p["timestamp"] < cutoff:
                    continue
                    
                # For each symbol, keep only one entry per minute
                entry_time = datetime.fromisoformat(p["timestamp"])
                minute_key = f"{p['symbol']}_{entry_time.strftime('%Y%m%d%H%M')}"
                
                if minute_key not in seen_timestamps:
                    seen_timestamps[minute_key] = True
                    valid_prices.append(p)
            
            # Add new price entry
            new_price = {
                "symbol": symbol,
                "price": price,
                "timestamp": current_time.isoformat()
            }
            
            valid_prices.append(new_price)
            valid_prices.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Keep only necessary entries
            final_prices = []
            entries_per_symbol = {}
            
            for p in valid_prices:
                symbol = p["symbol"]
                if symbol not in entries_per_symbol:
                    entries_per_symbol[symbol] = 0
                
                if entries_per_symbol[symbol] < 25:
                    final_prices.append(p)
                    entries_per_symbol[symbol] += 1
            
            # Corrigido: usando "prices" em vez de "precos"
            with open(self.data_path, 'w') as f:
                json.dump({"prices": final_prices}, f, indent=2)
                
        except Exception as e:
            print(f"erro ao salvar preço: {e}")

    async def fetch_crypto_prices(self) -> Dict[str, float]:
        """Fetch current crypto prices from Binance public API"""
        async with aiohttp.ClientSession() as session:
            try:
                # Using 24hr ticker endpoint - doesn't require API key
                url = f"{self.BINANCE_BASE_URL}/ticker/24hr"
                prices = {}
                
                async with session.get(url) as response:
                    if response.status == 200:
                        all_tickers = await response.json()
                        # Filter only our symbols
                        for ticker in all_tickers:
                            symbol = ticker['symbol']
                            if symbol in self.CRYPTO_SYMBOLS:
                                prices[symbol] = float(ticker['lastPrice'])
                    return prices
            except Exception as e:
                print(f"Error ao coletar os precos: {e}")
                return {}

    async def fetch_historical_data(self, symbol: str, interval: str = '1h', limit: int = 24) -> List[Dict]:
        """Fetch historical kline/candlestick data from Binance public API"""
        async with aiohttp.ClientSession() as session:
            try:
                # Using public klines endpoint
                url = f"{self.BINANCE_BASE_URL}/klines"
                params = {
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return [
                            {
                                'timestamp': datetime.fromtimestamp(k[0] / 1000),
                                'price': float(k[4]),  # closing price
                                'volume': float(k[5]), # volume
                                'high': float(k[2]),   # high price
                                'low': float(k[3])     # low price
                            } for k in data
                        ]
                    return []
            except Exception as e:
                print(f"Error fetching historical data: {e}")
                return []

    async def calculate_indicators(self, symbol: str) -> Dict:
        """Calculate technical indicators using public data"""
        try:
            # Aguardar os dados históricos
            historical_data = await self.fetch_historical_data(symbol)
            if not historical_data:
                return {}

            # Criar DataFrame apenas se houver dados
            if len(historical_data) > 0:
                df = pd.DataFrame(historical_data)
                current_price = df['price'].iloc[-1]
                hour_ago_price = df['price'].iloc[-2] if len(df) > 1 else current_price
                day_ago_price = df['price'].iloc[0]
                
                indicators = {
                    '1h_change': ((current_price - hour_ago_price) / hour_ago_price) * 100,
                    '24h_change': ((current_price - day_ago_price) / day_ago_price) * 100,
                    '24h_high': df['high'].max(),
                    '24h_low': df['low'].min()
                }
                return indicators
            return {}
            
        except Exception as e:
            print(f"erro ao calcular indicadores para {symbol}: {e}")
            return {}

    def create_price_embed(self, prices: Dict[str, float], indicators: Dict[str, Dict]) -> discord.Embed:
        """Cria um embed mais atraente com informações de preço"""
        embed = discord.Embed(
            title="💹 Atualização do Mercado Cripto",
            description="Preços em tempo real da Binance",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Adicionar imagem em miniatura (thumbnail)
        embed.set_thumbnail(url='https://example.com/crypto_thumbnail.png')
        
        for symbol, name in self.CRYPTO_SYMBOLS.items():
            if symbol not in prices:
                continue
                
            current_price = prices[symbol]
            indicator_data = indicators.get(symbol, {})
            
            change_24h = indicator_data.get('24h_change', 0)
            emoji = "📈" if change_24h > 0 else "📉"
            
            crypto_emoji = "₿" if "BTC" in symbol else "Ξ" if "ETH" in symbol else "Ł"  # Trocado BNB para Ł (Litecoin)
            
            value = (
                f"**Preço:** `${current_price:,.2f}` USD\n"
                f"**Variação 24h:** `{change_24h:+.2f}%` {emoji}\n"
                f"**Máxima 24h:** `${indicator_data.get('24h_high', 0):,.2f}`\n"
                f"**Mínima 24h:** `${indicator_data.get('24h_low', 0):,.2f}`\n"
            )
            
            embed.add_field(
                name=f"{crypto_emoji} {name.upper()}",
                value=value,
                inline=False
            )
        
        # Definir rodapé com ícone
        embed.set_footer(text="Dados fornecidos pela Binance")
        
        return embed

    @tasks.loop(hours=5)
    async def price_update_loop(self):
        try:
            channel = self.bot.get_channel(self.UPDATE_CHANNEL_ID)
            if not channel:
                return

            prices = await self.fetch_crypto_prices()
            if not prices:
                return

            indicators = {}
            for symbol, price in prices.items():
                self.store_price(symbol, price)
                indicators[symbol] = await self.calculate_indicators(symbol)

            embed = self.create_price_embed(prices, indicators)
            
            if self.last_message:
                # Editar a mensagem existente
                await self.last_message.edit(embed=embed)
            else:
                # Enviar nova mensagem e armazenar referência
                self.last_message = await channel.send(embed=embed)

        except Exception as e:
            print(f"erro no loop de atualização: {e}")

    @price_update_loop.before_loop
    async def before_price_update(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Investment(bot))
