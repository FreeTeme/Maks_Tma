from .base_parser import BaseParser
import requests
import logging

class XTParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            response = self._make_api_request()
            if not response.ok:
                self.logger.error(f"XT.com API error: {response.status_code}")
                return {}

            data = response.json()
            self.logger.debug(f"Raw API response: {data}")

            if "result" not in data or "items" not in data["result"]:
                self.logger.error("Key 'result' or 'items' not found in API response")
                return {}

            return self.parse_response(data["result"]["items"], normalized_coin)
        except Exception as e:
            self.logger.error(f"XT.com parser error: {str(e)}")
            return {}

    def _make_api_request(self):
        cookies = {
            'lang': 'en',
            'clientCode': '1745753823509aFphheJrJ4impm2PZjS',
            '_ga': 'GA1.1.775095991.1745753825',
            'captcha_v4_user': '72f0aec31676460bbaf5aa147cbab0af',
            '_vid_t': 'Ao7u0Fwdhdl87CtT2La/o3Ta7FmU9OCPGWjuqeKOLc35Y0dpZ4LiiZVEHe323Np+0xW1sRdC+Oz++MoVloBPTYhBc/mkKBDgcIGuRNY=',
            '_ga_CY0DPVC3GS': 'GS1.1.1745759806.2.1.1745761546.0.0.0',
            '_ga_MK8XKWK7DV': 'GS1.1.1745759807.2.1.1745761546.0.0.0',
        }

        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
            'api-version': '4',
            'client-code': '1745753823509aFphheJrJ4impm2PZjS',
            'client-device-name': 'Chrome V135.0.0.0 (Win10)',
            'device': 'web',
            'lang': 'en',
            'priority': 'u=1, i',
            'referer': 'https://www.xt.com/en/finance/earn-overview',
            'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'xt-host': 'www.xt.com',
            # 'cookie': 'lang=en; clientCode=1745753823509aFphheJrJ4impm2PZjS; _ga=GA1.1.775095991.1745753825; captcha_v4_user=72f0aec31676460bbaf5aa147cbab0af; _vid_t=Ao7u0Fwdhdl87CtT2La/o3Ta7FmU9OCPGWjuqeKOLc35Y0dpZ4LiiZVEHe323Np+0xW1sRdC+Oz++MoVloBPTYhBc/mkKBDgcIGuRNY=; _ga_CY0DPVC3GS=GS1.1.1745759806.2.1.1745761546.0.0.0; _ga_MK8XKWK7DV=GS1.1.1745759807.2.1.1745761546.0.0.0',
        }

        params = {
            'categories': 'SIMPLE_EARN',
            'duration': 'ALL',
            'limit': '-1',
            'fromPage': '1',
        }

        response = requests.get(
            'https://www.xt.com/sapi/v4/balance/public/finance/product',
            params=params,
            cookies=cookies,
            headers=headers,
        )
        self.logger.debug(f"API request to XT.com finance, status code: {response.status_code}")
        return response

    def parse_response(self, items: list, coin: str) -> dict:
        result = {
            "exchange": "XT.com",
            "coin": coin,
            "holdPosList": [],
            "lockPosList": [],
            "cost": "0%"
        }

        all_apy = []

        for group in items:
            for collection in group.get("productCollections", []):
                for product in collection.get("financialProducts", []):
                    product_currency = product.get("currency", "").lower()
                    if product_currency != coin.lower():
                        continue

                    apy_list = product.get("apyList", [])
                    if not apy_list:
                        continue

                    apy = round(float(apy_list[0].get("annualized", 0)), 2)
                    duration = product.get("duration", 0)
                    min_amount = float(product.get("singleMin", 0))
                    max_amount = float(product.get("singleMax", 0))

                    position = {
                        "days": duration,
                        "apy": apy,
                        "min_amount": min_amount,
                        "max_amount": max_amount,
                    }

                    product_type = product.get("productType", "")
                    if product_type == "DEMAND_SAVING":
                        result["holdPosList"].append(position)
                    elif product_type == "TIME_SAVING":
                        result["lockPosList"].append(position)

                    all_apy.append(apy)

        if all_apy:
            min_apy = round(min(all_apy), 2)
            max_apy = round(max(all_apy), 2)
            result["cost"] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"

        return result
