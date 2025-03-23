from .base_parser import BaseParser
import requests
import logging

class XTParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        """
        Получает информацию о стейкинге для указанной монеты.
        Возвращает данные в формате, аналогичном Gate.io.
        """
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            # Запрос к API XT.com
            response = self._make_api_request()
            if not response.ok:
                self.logger.error(f"XT.com API error: {response.status_code}")
                return {}

            # Обрабатываем данные, начиная с ключа 'result'
            data = response.json()
            self.logger.debug(f"Raw API response: {data}")

            if "result" not in data:
                self.logger.error("Key 'result' not found in API response")
                return {}

            return self.parse_response(data["result"], normalized_coin)
        except Exception as e:
            self.logger.error(f"XT.com parser error: {str(e)}")
            return {}

    def _make_api_request(self):
        """
        Запрос к API XT.com.
        """
        url = "https://www.xt.com/sapi/v4/market/public/symbol"
        cookies = {
            'lang': 'en',
            'clientCode': '1742651686449LuN3wwMURxex7JKtKzF',
            '_ga': 'GA1.1.2555900475.4695226615',
            '_ga_MK8XKWK7DV': 'GS1.1.1742651708.1.1.1742651755.0.0.0',
            '_ga_CY0DPVC3GS': 'GS1.1.1742651708.1.1.1742651758.0.0.0',
        }
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
            'api-version': '4',
            'client-code': '1742651686449LuN3wwMURxex7JKtKzF',
            'client-device-name': 'Chrome V134.0.0.0 (Unknown)',
            'device': 'web',
            'lang': 'en',
            'priority': 'u=1, i',
            'referer': 'https://www.xt.com/en/finance/earn-overview',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
            'xt-host': 'www.xt.com',
        }
        params = {
            'version': 'cd9f5245fbaba8dbc6f9e08ae3ee83b8',
        }

        response = requests.get(url, params=params, cookies=cookies, headers=headers)
        self.logger.debug(f"API request to {url}, status code: {response.status_code}")
        return response

    def parse_response(self, data: dict, coin: str) -> dict:
        """
        Парсит данные от XT.com и возвращает их в формате, аналогичном Gate.io.
        """
        result = {
            "exchange": "XT.com",
            "coin": coin,
            "holdPosList": [],  # Гибкий стейкинг
            "lockPosList": [],  # Фиксированный стейкинг
            "cost": "0%"
        }

        if "symbols" not in data:
            self.logger.error("Key 'symbols' not found in API response")
            return result

        # Нормализуем формат монеты для сравнения
        normalized_coin = coin.lower()
        self.logger.debug(f"Normalized coin for comparison: {normalized_coin}")

        # Обрабатываем данные о торговых парах
        for item in data.get("symbols", []):
            self.logger.debug(f"Processing item: {item}")

            base_currency = item.get("baseCurrency", "").lower()
            quote_currency = item.get("quoteCurrency", "").lower()
            self.logger.debug(f"Base currency: {base_currency}, Quote currency: {quote_currency}")

            # Ищем только по baseCurrency, при этом quoteCurrency должен быть 'usdt'
            if base_currency != normalized_coin or quote_currency != "usdt":
                self.logger.debug(f"Skipping item: {item['symbol']} (not related to {normalized_coin}/usdt)")
                continue

            # Используем комиссии как пример APY
            maker_fee = float(item.get("makerFeeRate", 0))
            taker_fee = float(item.get("takerFeeRate", 0))
            self.logger.debug(f"Maker fee: {maker_fee}, Taker fee: {taker_fee}")

            # Добавляем данные в holdPosList (гибкий стейкинг)
            if maker_fee > 0:
                result["holdPosList"].append({
                    "days": 0,  # Гибкий стейкинг не имеет срока
                    "apy": round(maker_fee * 100, 2),  # Преобразуем комиссию в APY
                    "min_amount": 0,  # Минимальная сумма не указана
                    "max_amount": float("inf")  # Без ограничений
                })
                self.logger.debug(f"Added to holdPosList: {result['holdPosList'][-1]}")

            # Добавляем данные в lockPosList (фиксированный стейкинг)
            if taker_fee > 0:
                result["lockPosList"].append({
                    "days": 30,  # Пример срока блокировки
                    "apy": round(taker_fee * 100, 2),  # Преобразуем комиссию в APY
                    "min_amount": 0,  # Минимальная сумма не указана
                    "max_amount": float("inf")  # Без ограничений
                })
                self.logger.debug(f"Added to lockPosList: {result['lockPosList'][-1]}")

        # Формируем строку cost на основе APY
        all_apy = [pos["apy"] for pos in result["holdPosList"] + result["lockPosList"]]
        if all_apy:
            min_apy = round(min(all_apy), 2)
            max_apy = round(max(all_apy), 2)
            result["cost"] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"
            self.logger.debug(f"Calculated cost: {result['cost']}")

        return result