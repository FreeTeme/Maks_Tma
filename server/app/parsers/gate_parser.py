import requests
import logging
from typing import Dict, List

class GateIOParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    #     self.proxies = { 'http': 'http://52.194.186.70:1080',
    # 'https': 'http://52.194.186.70:1080',}

    def normalize_coin_name(self, coin: str) -> str:
        return coin.upper()

    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            response = self._make_api_request(normalized_coin)
            if not response.ok:
                self.logger.error(f"Gate.io API error: {response.status_code}")
                return {}

            data = response.json()
            self.logger.debug(f"Raw API response: {data}")

            if data.get("code") != 0:
                self.logger.error(f"Gate.io API returned error: {data.get('message')}")
                return {}

            return self.parse_response(data.get("data", {}), normalized_coin)

        except Exception as e:
            self.logger.error(f"Gate.io parser error: {str(e)}", exc_info=True)
            return {}

    def _make_api_request(self, coin: str):
        url = "https://www.gate.io/apiw/v2/uni-loan/earn/market/list"
        params = {
            'page': '1',
            'limit': '20',
            'search_coin': coin,
            'have_balance': '0',
            'have_award': '0',
            'is_subscribed': '0',
            'available': 'false'
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json'
        }

        return requests.get(
            url,
            params=params,
            headers=headers,
            # proxies=self.proxies,
            verify=False,
            timeout=15
        )

    def parse_response(self, data: dict, coin: str) -> dict:
        result = {
            "exchange": "Gate.io",
            "coin": coin,
            "holdPosList": [],
            "lockPosList": [],
            "cost": "0%",
        }

        apy_values = []

        for item in data.get("list", []):
            if item.get("asset", "").upper() != coin:
                continue

            # Гибкий стейкинг
            try:
                flexible_apy = float(item.get("year_rate", 0)) * 100
                if flexible_apy > 0:
                    result["holdPosList"].append({
                        "days": 0,
                        "apy": round(flexible_apy, 2),
                        "min_amount": 0,
                        "max_amount": 0
                    })
                    apy_values.append(flexible_apy)
            except Exception as e:
                self.logger.warning(f"Error parsing flexible APY: {str(e)}")

            # Фиксированный стейкинг
            for fixed in item.get("fixed_list", []):
                try:
                    year_rate = float(fixed.get("year_rate") or 0)

                    # Считаем ladder APR, если он есть
                    ladder_aprs = fixed.get("ladder_apr")
                    max_apr = 0.0
                    if isinstance(ladder_aprs, list):
                        for ladder in ladder_aprs:
                            try:
                                apr_val = float(ladder.get("apr", 0))
                                max_apr = max(max_apr, apr_val)
                            except Exception:
                                continue

                    # Финальный APY = ставка + бонус
                    fixed_apy = (year_rate + max_apr) * 100

                    # Fallback если всё по нулям — пробуем item-level max_year_rate
                    if fixed_apy == 0:
                        fixed_apy = float(item.get("max_year_rate", 0) or 0) * 100

                    duration = int(fixed.get("lock_up_period", 0))

                    # Лог отладки
                    self.logger.debug(f"[{coin}] fixed lock {duration}d: year_rate={year_rate}, ladder_apr={max_apr}, total={fixed_apy}")

                    # Добавляем в список, если всё в порядке
                    if fixed_apy > 0:
                        result["lockPosList"].append({
                            "days": duration,
                            "apy": round(fixed_apy, 2),
                            "min_amount": 0,
                            "max_amount": 0
                        })
                        apy_values.append(fixed_apy)

                except Exception as e:
                    self.logger.warning(f"Error parsing fixed APY: {str(e)}")

        if apy_values:
            min_apy = round(min(apy_values), 2)
            max_apy = round(max(apy_values), 2)
            result["cost"] = f"{min_apy}%" if min_apy == max_apy else f"{min_apy}%–{max_apy}%"

        return result
