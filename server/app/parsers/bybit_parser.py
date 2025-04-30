from .base_parser import BaseParser
import requests
import logging

class BybitParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            result = {
                "exchange": "Bybit",
                "coin": normalized_coin,
                "holdPosList": [],
                "lockPosList": [],
                "cost": "0%"
            }
            all_apy = []

            # Парсим стандартный стейкинг
            staking_data = self._make_staking_request(normalized_coin)
            if staking_data:
                self.logger.debug(f"Parsing staking data for {normalized_coin}")
                staking_result, staking_apy = self.parse_staking(staking_data, normalized_coin)
                result["holdPosList"].extend(staking_result["holdPosList"])
                result["lockPosList"].extend(staking_result["lockPosList"])
                all_apy.extend(staking_apy)

            # Парсим Launchpool
            launchpool_data = self._make_launchpool_request()
            if launchpool_data:
                self.logger.debug(f"Parsing launchpool data for {normalized_coin}")
                launchpool_result, launchpool_apy = self.parse_launchpool(launchpool_data, normalized_coin)
                result["holdPosList"].extend(launchpool_result["holdPosList"])
                all_apy.extend(launchpool_apy)

            # Парсим Flexible Savings
            flexible_data = self._make_flexible_request(normalized_coin)
            if flexible_data:
                self.logger.debug(f"Parsing flexible savings data for {normalized_coin}")
                flexible_result, flexible_apy = self.parse_flexible(flexible_data, normalized_coin)
                result["holdPosList"].extend(flexible_result["holdPosList"])
                all_apy.extend(flexible_apy)

            # Выставляем итоговый cost
            if all_apy:
                min_apy = round(min(all_apy), 2)
                max_apy = round(max(all_apy), 2)
                result["cost"] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"

            return result

        except Exception as e:
            self.logger.error(f"Bybit parser error: {str(e)}")
            return {}

    def _make_staking_request(self, coin: str):
        url = 'https://api.bybit.com/asset/v3/public/staking/product/union'
        params = {
            'coin': coin,
            'status': 'ALL'
        }
        headers = {'accept': 'application/json'}
        response = requests.get(url, params=params, headers=headers)
        self.logger.debug(f"Staking request status: {response.status_code}")
        if response.ok:
            return response.json().get('result', [])
        return None

    def _make_launchpool_request(self):
        url = 'https://api.bybit.com/spot/v3/public/launchpad'
        headers = {'accept': 'application/json'}
        response = requests.get(url, headers=headers)
        self.logger.debug(f"Launchpool request status: {response.status_code}")
        if response.ok:
            return response.json().get('result', {}).get('list', [])
        return None

    def _make_flexible_request(self, coin: str):
        url = 'https://api.bybit.com/asset/v3/public/deposit-savings/product/list'
        params = {'coin': coin}
        headers = {'accept': 'application/json'}
        response = requests.get(url, params=params, headers=headers)
        self.logger.debug(f"Flexible savings request status: {response.status_code}")
        if response.ok:
            return response.json().get('result', [])
        return None

    def parse_staking(self, data: list, coin: str):
        result = {
            "holdPosList": [],
            "lockPosList": [],
        }
        apys = []

        for item in data:
            if item.get("coin") != coin:
                continue

            apy = float(item.get("apy", 0))
            period = int(item.get("period", 0))

            if period == 0:
                result["holdPosList"].append({
                    "days": 0,
                    "apy": round(apy, 2),
                    "min_amount": 0,
                    "max_amount": 0
                })
            else:
                result["lockPosList"].append({
                    "days": period,
                    "apy": round(apy, 2),
                    "min_amount": 0,
                    "max_amount": 0
                })

            apys.append(apy)

        return result, apys

    def parse_launchpool(self, data: list, coin: str):
        result = {
            "holdPosList": [],
        }
        apys = []

        for item in data:
            if item.get("launchpoolTokenInfo", {}).get("tokenName") == coin:
                apy = float(item.get("launchpoolTokenInfo", {}).get("apy", 0))
                result["holdPosList"].append({
                    "days": 0,
                    "apy": round(apy, 2),
                    "min_amount": 0,
                    "max_amount": 0
                })
                apys.append(apy)

        return result, apys

    def parse_flexible(self, data: list, coin: str):
        result = {
            "holdPosList": [],
        }
        apys = []

        for item in data:
            if item.get("coin") != coin:
                continue

            apy = float(item.get("estApy", 0))
            result["holdPosList"].append({
                "days": 0,
                "apy": round(apy, 2),
                "min_amount": 0,
                "max_amount": 0
            })
            apys.append(apy)

        return result, apys
