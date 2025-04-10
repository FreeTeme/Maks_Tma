from .base_parser import BaseParser
import requests
import logging
import json

class BitmartParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        """
        Получает информацию о стейкинге для указанной монеты.
        Возвращает данные в формате, аналогичном Gate.io.
        """
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            # Запрос к API Bitmart
            response = self._make_api_request()
            if not response.ok:
                self.logger.error(f"Bitmart API error: {response.status_code}")
                return {}

            data = response.json()
            self.logger.debug(f"Raw API response: {data}")

            if "data" not in data:
                self.logger.error("Key 'data' not found in API response")
                return {}

            return self.parse_response(data["data"], normalized_coin)
        except Exception as e:
            self.logger.error(f"Bitmart parser error: {str(e)}")
            return {}

    def _make_api_request(self):
        cookies = {
            '_gcl_au': '1.1.1467836457.1742817489',
            'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%22195c8048e8848e-094de37c3e160d8-26011d51-1049088-195c8048e892cb%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E8%87%AA%E7%84%B6%E6%90%9C%E7%B4%A2%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk1YzgwNDhlODg0OGUtMDk0ZGUzN2MzZTE2MGQ4LTI2MDExZDUxLTEwNDkwODgtMTk1YzgwNDhlODkyY2IifQ%3D%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%2C%22%24device_id%22%3A%22195c8048e8848e-094de37c3e160d8-26011d51-1049088-195c8048e892cb%22%7D',
            '_ym_uid': '1742817497223099698',
            '_ym_d': '1742817497',
            '_ym_isad': '2',
            'afUserId': '4bda6998-d3e9-44cd-b17f-e8bc0d122342-p',
            'AF_SYNC': '1742817497745',
            '_ga': 'GA1.1.1619162155.1742817499',
            '__adroll_fpc': '02a37e647e1606c49435694cd0ed2c67-1742817510541',
            '__cf_bm': 'mnL_OVy66IV7BKpMVzsCB80Pim9UTk.kRYuziosWQ.0-1742885281-1.0.1.1-W5FnXHgHpLY9u5zuARpJO.Q5CSatpMbinwoxF01MexLcbVMQIbLXLTmIoVE2pFs2L.zRRX2mrvsXLLunUW.YR75.HDyir4H738TGPAIlQNw',
            '_cfuvid': 'dWWHiqW4X9hO.KE0We0GG0KS_RUnNa.6.LU47uYSYgo-1742885281364-0.0.1.1-604800000',
            '_ym_visorc': 'b',
            'zendeskExternalId': 'temp-ixhna3hi5',
            'golang': 'en',
            'currentCurrency': 'USD',
            '_ga_7BWH3BJ925': 'GS1.1.1742885284.2.1.1742885377.0.0.0',
            '_ga_PJBF32MZ6E': 'GS1.1.1742885284.2.1.1742885377.43.0.0',
            '__ar_v4': 'DG4F44XG2BFTPCKNR4LF2B%3A20250323%3A5%7CA7Q5K5D3MZE5TMGLZ7UG4J%3A20250323%3A5',
        }

        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
            'baggage': 'sentry-environment=production,sentry-release=0b39c21,sentry-public_key=0bccf35de72ece635f5af3c82acd1839,sentry-trace_id=ebc3d1573e514144bc6fe7c0570f8518,sentry-sample_rate=0.15,sentry-sampled=false',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'expires': '0',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.bitmart.com/earn/en-US',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sentry-trace': 'ebc3d1573e514144bc6fe7c0570f8518-a46b026710a5399e-0',
            'sw8': '1-Y2M0YjhkZjctNjg0ZC00YzhmLTk0MjEtMDUwNTgyYjFlNWRl-Njc2YWFkYzMtYmY2Mi00MDQ1LThhMmQtOGM1Mzg0OTI1ZDA0-0-Yml0bWFydC1mcm9udC1lbmQtY2xpZW50-djEuMC4w-L2Vhcm4vZW4tVVM=-d3d3LmJpdG1hcnQuY29t',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'x-bm-client': 'WEB',
            'x-bm-contract': '2',
            'x-bm-device': '3d6d58f9eba29fd300adb42cc25a1787',
            'x-bm-sec': '1',
            'x-bm-sensors-distinct-id': '195c8048e8848e-094de37c3e160d8-26011d51-1049088-195c8048e892cb',
            'x-bm-timezone': 'Europe/Minsk',
            'x-bm-timezone-offset': '-180',
            'x-bm-ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'x-bm-version': '0b39c21',
            # 'cookie': '_gcl_au=1.1.1467836457.1742817489; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22195c8048e8848e-094de37c3e160d8-26011d51-1049088-195c8048e892cb%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E8%87%AA%E7%84%B6%E6%90%9C%E7%B4%A2%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk1YzgwNDhlODg0OGUtMDk0ZGUzN2MzZTE2MGQ4LTI2MDExZDUxLTEwNDkwODgtMTk1YzgwNDhlODkyY2IifQ%3D%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%2C%22%24device_id%22%3A%22195c8048e8848e-094de37c3e160d8-26011d51-1049088-195c8048e892cb%22%7D; _ym_uid=1742817497223099698; _ym_d=1742817497; _ym_isad=2; afUserId=4bda6998-d3e9-44cd-b17f-e8bc0d122342-p; AF_SYNC=1742817497745; _ga=GA1.1.1619162155.1742817499; __adroll_fpc=02a37e647e1606c49435694cd0ed2c67-1742817510541; __cf_bm=mnL_OVy66IV7BKpMVzsCB80Pim9UTk.kRYuziosWQ.0-1742885281-1.0.1.1-W5FnXHgHpLY9u5zuARpJO.Q5CSatpMbinwoxF01MexLcbVMQIbLXLTmIoVE2pFs2L.zRRX2mrvsXLLunUW.YR75.HDyir4H738TGPAIlQNw; _cfuvid=dWWHiqW4X9hO.KE0We0GG0KS_RUnNa.6.LU47uYSYgo-1742885281364-0.0.1.1-604800000; _ym_visorc=b; zendeskExternalId=temp-ixhna3hi5; golang=en; currentCurrency=USD; _ga_7BWH3BJ925=GS1.1.1742885284.2.1.1742885377.0.0.0; _ga_PJBF32MZ6E=GS1.1.1742885284.2.1.1742885377.43.0.0; __ar_v4=DG4F44XG2BFTPCKNR4LF2B%3A20250323%3A5%7CA7Q5K5D3MZE5TMGLZ7UG4J%3A20250323%3A5',
        }

        response = requests.get(
            'https://www.bitmart.com/gw-api/newearn/saving/web/unlogin/product/list',
            cookies=cookies,
            headers=headers,
        )
        self.logger.debug(f"API request to Bitmart, status code: {response.status_code}")
        return response

    def parse_response(self, data: dict, coin: str) -> dict:
        """
        Парсит данные от Bitmart и возвращает их в нужном формате.
        """
        result = {
            "exchange": "Bitmart",
            "coin": coin,
            "holdPosList": [],  # Гибкий стейкинг
            "lockPosList": [],  # Фиксированный стейкинг
            "cost": "0%"
        }

        all_apy = []

        # Обрабатываем гибкий стейкинг (resFlexible)
        if "resFlexible" in data and isinstance(data["resFlexible"], list):
            for item in data["resFlexible"]:
                if item.get("coinName") == coin and "addInfo" in item:
                    self._process_flexible_products(item["addInfo"], result, all_apy)

        # Обрабатываем фиксированный стейкинг (resFixed)
        if "resFixed" in data and isinstance(data["resFixed"], list):
            for item in data["resFixed"]:
                if item.get("coinName") == coin and "addInfo" in item:
                    self._process_fixed_products(item["addInfo"], result, all_apy)

        # Формируем строку cost
        if all_apy:
            min_apy = round(min(all_apy), 2)
            max_apy = round(max(all_apy), 2)
            result["cost"] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"

        return result

    def _process_flexible_products(self, products: list, result: dict, all_apy: list):
        """Обрабатывает продукты гибкого стейкинга."""
        for product in products:
            try:
                apy = float(product.get("annualProfitPec", 0))
                if apy > 0:
                    result["holdPosList"].append({
                        "days": 0,
                        "apy": round(apy, 2),
                        "min_amount": float(product.get("minSubcription", 0)),
                        "max_amount": 0
                    })
                    all_apy.append(apy)
            except (TypeError, ValueError) as e:
                self.logger.warning(f"Failed to parse flexible product: {e}")

    def _process_fixed_products(self, products: list, result: dict, all_apy: list):
        """Обрабатывает продукты фиксированного стейкинга."""
        for product in products:
            try:
                apy = float(product.get("annualProfitPec", 0))
                lock_days = int(product.get("lockDay", 0))
                if apy > 0 and lock_days > 0:
                    result["lockPosList"].append({
                        "days": lock_days,
                        "apy": round(apy, 2),
                        "min_amount": float(product.get("minSubcription", 0)),
                        "max_amount": 0
                    })
                    all_apy.append(apy)
            except (TypeError, ValueError) as e:
                self.logger.warning(f"Failed to parse fixed product: {e}")