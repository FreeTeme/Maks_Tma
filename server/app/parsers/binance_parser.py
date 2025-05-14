import requests
import logging
from typing import Dict, List

class BinanceParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def normalize_coin_name(self, coin: str) -> str:
        return coin.upper()

    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            response = self._make_api_request(normalized_coin)
            if not response.ok:
                self.logger.error(f"Binance API error: {response.status_code}")
                return {}

            data = response.json()
            self.logger.debug(f"Raw API response: {data}")

            if not data.get('success') or data.get('code') != "000000":
                self.logger.error(f"API error: {data.get('message')}")
                return {}

            return self.parse_response(data['data'], normalized_coin)

        except Exception as e:
            self.logger.error(f"Binance parser error: {str(e)}", exc_info=True)
            return {}

    def _make_api_request(self, coin: str):
        params = {
            'requestSource': 'WEB',
            'pageIndex': '1',
            'pageSize': '10',
            'asset': coin.upper(),
            'simpleEarnType': 'ALL',
        }

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Referer': f'https://www.binance.com/en/earn/{coin.upper()}',
        }

        return requests.get(
            'https://www.binance.com/bapi/earn/v1/friendly/finance-earn/simple-earn/homepage/details',
            params=params,
            headers=headers,
            timeout=15
        )

    def parse_response(self, data: dict, coin: str) -> dict:
        result = {
            "exchange": "Binance",
            "coin": coin,
            "holdPosList": [],
            "lockPosList": [],
            "cost": "0%",
        }

        try:
            products = data.get('list', [])
            apy_values = []

            for product in products:
                if product.get('asset') != coin.upper():
                    continue

                for detail in product.get('productDetailList', []):
                    duration = int(detail.get('duration', 0))
                    apy = self._parse_detail_apy(detail)
                    max_amount = float(detail.get('maxPurchaseAmountPerUser', 0))

                    if apy <= 0:
                        continue

                    entry = {
                        "days": duration,
                        "apy": round(apy, 2),
                        "min_amount": 0,
                        "max_amount": max_amount
                    }

                    apy_values.append(apy)
                    if duration == 0:
                        result["holdPosList"].append(entry)
                    else:
                        result["lockPosList"].append(entry)

            if apy_values:
                min_apy = round(min(apy_values), 2)
                max_apy = round(max(apy_values), 2)
                result["cost"] = f"{min_apy}%" if min_apy == max_apy else f"{min_apy}%–{max_apy}%"

            return result

        except Exception as e:
            self.logger.error(f"Error parsing Binance data: {str(e)}", exc_info=True)
            return result

    def _parse_detail_apy(self, detail: dict) -> float:
        try:
            if detail.get('apy'):
                return float(detail['apy']) * 100
            if detail.get('flexibleApy'):
                return float(detail['flexibleApy']) * 100
            return 0.0
        except Exception as e:
            self.logger.warning(f"Detail APY parse error: {str(e)}")
            return 0.0
