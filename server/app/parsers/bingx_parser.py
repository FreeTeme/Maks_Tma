from .base_parser import BaseParser
import requests
import logging

class BingXParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            response = self._make_api_request()
            if not response.ok:
                self.logger.error(f"BingX API error: {response.status_code}")
                return {}

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
        Запрос к актуальному API BingX для стейкинга.
        """
        

        cookies = {
            'locale': 'en',
            'uuid': '2cd47536900844939eeb1b389c883ad0',
            '_gid': 'GA1.2.450072761.1745753377',
            '_fbp': 'fb.1.1745753384756.80230797195555829',
            '__cf_bm': '..p7W23SYXztneMGZuiKtrRxL67cb.r5hZBPGGpCaeQ-1745763032-1.0.1.1-DmOpLWHsF.glZAgqPPVw1H6By1MYzLiZUemusmqKCJ49vP7dm6pW3LYVxFmHQNCKVOCY2g5wh7sHNMDlXDf9FL1xhAUJGffqeW6kQtVcIPQ',
            '_ga': 'GA1.1.1078388942.1745753377',
            '_uetsid': 'eb106640235a11f0a67e09aaeba947e3',
            '_uetvid': 'eb1083c0235a11f0bb712ba311fb8d9e',
            '_ga_GH1NE7LJK0': 'GS1.1.1745763028.2.1.1745763047.0.0.0',
            '_ga_F8FPFG5ZCL': 'GS1.1.1745763029.2.1.1745763047.0.0.0',
            'network_delay': '102',
        }

        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
            'app_version': '5.1.90',
            'appid': '30004',
            'appsiteid': '0',
            'channel': 'official',
            'device_brand': 'Windows 10_Chrome_135.0.0.0',
            'device_id': '2cd47536900844939eeb1b389c883ad0',
            'lang': 'en',
            'mainappid': '10009',
            'platformid': '30',
            'priority': 'u=1, i',
            'referer': 'https://bingx.com/en/wealth/earn/',
            'reg_channel': 'official',
            'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sign': '8FD054526C2846945C39FF8D4263165171B106846F6B943907ADB105EC1A109F',
            'timestamp': '1745763119854',
            'timezone': '3',
            'traceid': '46636f879ed448809b03f8feae71ff94',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
            # 'cookie': 'locale=en; uuid=2cd47536900844939eeb1b389c883ad0; _gid=GA1.2.450072761.1745753377; _fbp=fb.1.1745753384756.80230797195555829; __cf_bm=..p7W23SYXztneMGZuiKtrRxL67cb.r5hZBPGGpCaeQ-1745763032-1.0.1.1-DmOpLWHsF.glZAgqPPVw1H6By1MYzLiZUemusmqKCJ49vP7dm6pW3LYVxFmHQNCKVOCY2g5wh7sHNMDlXDf9FL1xhAUJGffqeW6kQtVcIPQ; _ga=GA1.1.1078388942.1745753377; _uetsid=eb106640235a11f0a67e09aaeba947e3; _uetvid=eb1083c0235a11f0bb712ba311fb8d9e; _ga_GH1NE7LJK0=GS1.1.1745763028.2.1.1745763047.0.0.0; _ga_F8FPFG5ZCL=GS1.1.1745763029.2.1.1745763047.0.0.0; network_delay=102',
        }

        params = {
            'searchType': '',
            'dataType': '',
            'assetName': '',
            'orderBy': '',
        }

        response = requests.get(
            'https://bingx.com/api/wealth-sales-trading/v1/product/list?searchType=&dataType=&assetName=&orderBy=',
            params=params,
            cookies=cookies,
            headers=headers,
        )
        self.logger.debug(f"API request to BingX, status code: {response.status_code}")
        return response

    def parse_response(self, data: list, coin: str) -> dict:
        result = {
            "exchange": "BingX",
            "coin": coin,
            "holdPosList": [],
            "lockPosList": [],
            "cost": "0%"
        }

        all_apy = []

        for item in data:
            if item.get("assetName") != coin:
                continue

            products = item.get("products", [])
            for product in products:
                try:
                    apy = round(float(product.get("apy", "0")), 2)
                    duration = int(product.get("duration", -1))
                    product_type = int(product.get("productType", 0))
                except (ValueError, TypeError):
                    continue

                entry = {
                    "days": 0 if duration == -1 else duration,
                    "apy": apy,
                    "min_amount": 0,
                    "max_amount": 0
                }

                if duration == -1 or product_type == 2:
                    result["holdPosList"].append(entry)
                elif duration > 0 or product_type == 1:
                    result["lockPosList"].append(entry)

                all_apy.append(apy)

        if all_apy:
            min_apy = round(min(all_apy), 2)
            max_apy = round(max(all_apy), 2)
            result["cost"] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"

        return result
