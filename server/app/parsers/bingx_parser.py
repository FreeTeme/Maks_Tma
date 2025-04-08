from .base_parser import BaseParser
import requests
import logging

class BingXParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
    
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            # Запрос к API BingX
            response = self._make_api_request()
            if not response.ok:
                self.logger.error(f"BingX API error: {response.status_code}")
                return {}

            # Обрабатываем данные, начиная с ключа 'data'
            data = response.json()
            self.logger.debug(f"Raw API response: {data}")

            if "data" not in data or "result" not in data["data"]:
                self.logger.error("Key 'data' or 'result' not found in API response")
                return {}

            return self.parse_response(data["data"]["result"], normalized_coin)
        except Exception as e:
            self.logger.error(f"BingX parser error: {str(e)}")
            return {}

    def _make_api_request(self):
        """
        Запрос к API BingX.
        """
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
            'app_version': '5.1.85',
            'appid': '30004',
            'appsiteid': '0',
            'channel': 'official',
            'device_brand': 'Windows 10_Chrome_134.0.0.0',
            'device_id': 'cc0534161158478aa11e3c9484d2e282',
            'lang': 'en',
            'mainappid': '10009',
            'origin': 'https://bingx.com',
            'platformid': '30',
            'priority': 'u=1, i',
            'referer': 'https://bingx.com/',
            'reg_channel': 'official',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-storage-access': 'active',
            'sign': '66FD38866BCAD6A2DDA684FE8EFC00563A31B3E17272119602D72494C1C7CB0E',
            'timestamp': '1742730682315',
            'timezone': '3',
            'traceid': 'f7ea13ead7f148bcafb249ebfe410e40',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }

        params = {
            'searchType': '',
            'dataType': '',
            'assetName': '',
            'orderBy': '',
        }

        response = requests.get('https://api-app.we-api.com/api/wealth-sales-trading/v1/product/list', params=params, headers=headers)
        self.logger.debug(f"API request to BingX, status code: {response.status_code}")
        return response

    def parse_response(self, data: list, coin: str) -> dict:
        """
        Парсит данные от BingX и возвращает их в формате, аналогичном Gate.io.
        """
        result = {
            "exchange": "BingX",
            "coin": coin,
            "holdPosList": [],  # Гибкий стейкинг
            "lockPosList": [],  # Фиксированный стейкинг
            "cost": "0%"
        }

        all_apy = []

        # Обрабатываем данные о монетах
        for item in data:
            if item.get("assetName") != coin:
                continue

            # Обрабатываем продукты для текущей монеты
            for product in item.get("products", []):
                apy = float(product.get("apy", 0))
                duration = int(product.get("duration", 0))

                # Гибкий стейкинг (productType = 2)
                if product.get("productType") == 2:
                    result["holdPosList"].append({
                        "days": 0,  # Гибкий стейкинг не имеет срока
                        "apy": round(apy, 2),  # Округляем до сотых
                        "min_amount": 0,  # Минимальная сумма не указана
                        "max_amount": float("inf")  # Без ограничений
                    })
                    all_apy.append(apy)

                # Фиксированный стейкинг (productType = 1)
                elif product.get("productType") == 1:
                    result["lockPosList"].append({
                        "days": duration,  # Срок блокировки
                        "apy": round(apy, 2),  # Округляем до сотых
                        "min_amount": 0,  # Минимальная сумма не указана
                        "max_amount": float("inf")  # Без ограничений
                    })
                    all_apy.append(apy)

        # Формируем строку cost
        if all_apy:
            min_apy = round(min(all_apy), 2)
            max_apy = round(max(all_apy), 2)
            result["cost"] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"

        return result