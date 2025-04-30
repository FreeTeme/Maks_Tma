from .base_parser import BaseParser
import requests
import logging

class BitmartParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            response = self._make_api_request()
            if not response.ok:
                self.logger.error(f"Bitmart API error: {response.status_code}")
                return {}

            data = response.json()
            self.logger.debug(f"Raw API response: {data}")

            if "data" not in data or "res" not in data["data"]:
                self.logger.error("Key 'data' or 'res' not found in API response")
                return {}

            return self.parse_response(data["data"]["res"], normalized_coin)
        except Exception as e:
            self.logger.error(f"Bitmart parser error: {str(e)}")
            return {}

    def _make_api_request(self):
        """
        Запрос к API Bitmart для получения продуктов стейкинга.
        """
        headers = {
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
        }
        url = 'https://www.bitmart.com/gw-api/newearn/staking/web/unlogin/product/stakeList'
        response = requests.get(url, headers=headers)
        self.logger.debug(f"API request to Bitmart, status code: {response.status_code}")
        return response

    def parse_response(self, res_list: list, coin: str) -> dict:
        result = {
            "exchange": "Bitmart",
            "coin": coin,
            "holdPosList": [],
            "lockPosList": [],
            "cost": "0%"
        }

        all_apy = []

        for item in res_list:
            if item.get("coinName") != coin:
                continue

            add_info = item.get("addInfo", [])
            for product in add_info:
                apy_str = product.get("annualProfitPec", "0%").replace("%", "")
                try:
                    apy = round(float(apy_str), 2)
                except ValueError:
                    apy = 0.0

                lock_day = int(product.get("lockDay", 0))
                min_amount = float(product.get("minSubcription", 0))

                entry = {
                    "days": lock_day,
                    "apy": apy,
                    "min_amount": min_amount,
                    "max_amount": 0
                }

                if product.get("productType") == "agility":
                    result["holdPosList"].append(entry)
                elif product.get("productType") == "locked":
                    result["lockPosList"].append(entry)

                all_apy.append(apy)

        if all_apy:
            min_apy = round(min(all_apy), 2)
            max_apy = round(max(all_apy), 2)
            result["cost"] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"

        return result
