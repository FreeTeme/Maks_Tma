from .base_parser import BaseParser
import requests

class BybitParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin).upper()

            response = self._make_api_request(normalized_coin)
            if not response:
                return self._empty_response(normalized_coin)

            return self.parse_response(response.json(), normalized_coin)

        except Exception as e:
            self.logger.error(f"Bybit parser error: {str(e)}")
            return self._empty_response(normalized_coin)

    def _make_api_request(self, coin: str):
        """Выполняет запрос к API Bybit"""
        headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0',
            'origin': 'https://www.bybit.com',
            'referer': 'https://www.bybit.com/',
            'platform': 'pc',
            'lang': 'en',
        }

        json_data = {
            'product_area': [0],
            'page': 1,
            'limit': 10,
            'product_type': 0,
            'coin_name': coin,
            'sort_apr': 0,
            'show_available': False,
            'fixed_saving_version': 1,
        }

        response = requests.post(
            'https://api2.bybit.com/s1/byfi/get-saving-homepage-product-cards',
            headers=headers,
            json=json_data,
            
        )

        if not response.ok:
            self.logger.error(f"Bybit API error: {response.status_code}")
            return None

        return response

    def parse_response(self, data: dict, coin: str) -> dict:
        """Парсит сырой ответ API в структурированный формат"""
        result = self._empty_response(coin)

        apy_values = []
        products = self._extract_products(data)

        for product in products:
            self._process_product(product, result, apy_values, coin)

        self._calculate_apy_range(result, apy_values)
        return result

    def _extract_products(self, data: dict) -> list:
        """Извлекает все продукты из структуры ответа"""
        products = []
        for coin_product in data.get("result", {}).get("coin_products", []):
            products.extend(coin_product.get("saving_products", []))
        return products

    def _process_product(self, product: dict, result: dict, apy_values: list, coin: str):
        """Обрабатывает отдельный продукт"""
        try:
            apy = self._parse_apy(product.get("apy", "0%"))
            is_fixed = product.get("is_fixed_term_loan_coin_product", False)
            days = int(product.get("staking_term", 0)) if is_fixed else 0

            pos = {
                "days": days,
                "apy": round(apy, 2),
                "min_amount": 0,
                "max_amount": 0
            }

            if is_fixed:
                result["lockPosList"].append(pos)
                self.logger.debug(f"[Bybit:{coin}] Locked product: {pos}")
            else:
                result["holdPosList"].append(pos)
                self.logger.debug(f"[Bybit:{coin}] Flexible product: {pos}")

            apy_values.append(apy)

        except Exception as e:
            self.logger.warning(f"[Bybit:{coin}] Product error: {str(e)}")

    def _parse_apy(self, apy_str: str) -> float:
        """Конвертирует строку APY в число"""
        return float(apy_str.replace("%", "").strip() or "0")

    def _calculate_apy_range(self, result: dict, apy_values: list):
        """Рассчитывает диапазон APY"""
        if apy_values:
            min_apy = min(apy_values)
            max_apy = max(apy_values)
            result["cost"] = (
                f"{min_apy:.2f}%–{max_apy:.2f}%" 
                if min_apy != max_apy 
                else f"{max_apy:.2f}%"
            )

    def _empty_response(self, coin: str) -> dict:
        """Возвращает пустой ответ для монеты"""
        return {
            'exchange': 'Bybit',
            'coin': coin,
            'holdPosList': [],
            'lockPosList': [],
            'cost': '0%'
        }