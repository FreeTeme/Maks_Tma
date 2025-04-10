from .base_parser import BaseParser
import requests
import logging

class BitgetParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        """
        Получает информацию о стейкинге для указанной монеты.
        Возвращает данные в формате, аналогичном Gate.io.
        """
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            # Запрос к API Bitget
            response = self._make_api_request()
            if not response.ok:
                self.logger.error(f"Bitget API error: {response.status_code}")
                return {}

            # Обрабатываем данные
            data = response.json()
            self.logger.debug(f"Raw API response: {data}")

            if "data" not in data:
                self.logger.error("Key 'data' not found in API response")
                return {}

            return self.parse_response(data["data"], normalized_coin)
        except Exception as e:
            self.logger.error(f"Bitget parser error: {str(e)}")
            return {}

    def _make_api_request(self):
        cookies = {
            'afUserId': '30347cb5-2a3d-42e2-9815-5a4fbd08ef12-p',
            'cf_clearance': '8_qQn4VR72eLnBijfaLv9I4hkaY3plO1NH1ljXm3WvA-1742814565-1.2.1.1-09GmwDn9BFU0pui5568wPGvHS4PXuCCXqCSo_7PLqbucEHrenVMKDrFqKCVLHeKfDjotVbvTvQH6d5_Se42Q8Ya64jL4J2XPVsJgNCKif.6nzBfGqQwCg6tANqq2WMtTBhTcKoukthyQDqn_XfXuMLTG_ZDb87RvtX9wgi1IsIkIyCZRT8S_ZUbS29WHYcHmtUP7cgkdHpxgEVLvxQx_rqZRm41nPeX7mR_OWDaq.MH7u5SWCjFVegOGYatYASpIduoE2Xdn0UHBM8wYSaQNLLxIaMpEdKKWDCe4MSD36U1mbznDXNvvfShLTTq1nHKr2jI42Ox5h_JAktLjttxGDKAsLxCan3hCJDwmFBzPqSOCW34tVmnIef3oxuqDenY_CTZaBMCLrSNdmqPiVjMmRnoOJdhWueZfvjsKmt9lwxw',
            '_cfuvid': 'm4miLGs.F_qcap2EGiscj69qBe7KK..PwH74bEtjDc8-1742814565989-0.0.1.1-604800000',
            'theme': 'white',
            'fingerprint-1742814602227-35951.29999999888-0.08677358664262758': 'true',
            'terminalCode-1742814602229-35953-0.4770093689235748': 'true',
            'BITGET_LOCAL_COOKIE': '{%22bitget_lang%22:%22ru%22%2C%22bitget_unit%22:%22USD%22%2C%22bitget_showasset%22:false%2C%22bitget_theme%22:%22dark%22%2C%22bitget_valuationunit_new%22:1%2C%22bitget_layout%22:%22right%22}',
            '_dx_kvani5r': 'ff2938641d22d1684d2059a361659d7780edacb6744536dea1236a08492126b449b3652f',
            '__adroll_fpc': '1d9ea902b381c4792562bafcc3ecb667-1742814639473',
            '_ym_uid': '1742814641730193558',
            '_ym_d': '1742814641',
            '_ym_isad': '2',
            '_ym_visorc': 'b',
            '_ga': 'GA1.1.918121276.1742814645',
            'OptanonAlertBoxClosed': 'Mon%20Mar%2024%202025%2014:10:59%20GMT+0300%20(%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C%20%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%BE%D0%B5%20%D0%B2%D1%80%D0%B5%D0%BC%D1%8F)',
            'OptanonConsent': 'isMarketing=1&isStatistic=1',
            '__cf_bm': 'dt7xy6LDJW92q1zPPGtwpklHT4.83tQ_7QFxLzTpOVw-1742816421-1.0.1.1-a_pLegn_Od4ClimhLlrFAj4L9tD4zpDdr6UboyV4m8w0y9c_EEEi_y5XmCUnykDKDs_hWMoXvRiCpQgatkmunhG9aPsNl4DE_zqhuQtA7SQ',
            'dy_token': '67e144b06B0c9rJN5WANBfxM7GEUDBfNAPI3FoP1',
            '__ar_v4': 'R3652JF77NH6ZC5OBZHWIH%3A20250323%3A4%7C2WBEMJJKHFG5PLSUZ7B5OY%3A20250323%3A4',
            '_ga_Z8Q93KHR0F': 'GS1.1.1742814645.1.1.1742816559.60.0.0',
        }

        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
            'baggage': 'sentry-environment=online,sentry-release=git%20rev-parse%20HEAD,sentry-public_key=d8b5c66bfb5c4f11a4aa8a755525bc70,sentry-trace_id=0da780fef3a74a96b07d1a26caa0674e,sentry-sample_rate=0,sentry-transaction=%2Fearning%2Fsavings,sentry-sampled=false',
            'content-type': 'application/json;charset=UTF-8',
            'deviceid': '04ce02c2b11dd04729d1afab65f6e8f7',
            'dy-token': '67e144b06B0c9rJN5WANBfxM7GEUDBfNAPI3FoP1',
            'language': 'ru_RU',
            'locale': 'ru_RU',
            'origin': 'https://www.bitget.com',
            'priority': 'u=1, i',
            'referer': 'https://www.bitget.com/ru/earning/savings',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-arch': '"x86"',
            'sec-ch-ua-bitness': '"64"',
            'sec-ch-ua-full-version': '"134.0.6998.118"',
            'sec-ch-ua-full-version-list': '"Chromium";v="134.0.6998.118", "Not:A-Brand";v="24.0.0.0", "Google Chrome";v="134.0.6998.118"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"10.0.0"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sentry-trace': '0da780fef3a74a96b07d1a26caa0674e-815474ad4cac6c24-0',
            'terminalcode': '3520211860fcf1af16ebc3000f385514',
            'terminaltype': '1',
            'tm': '1742816563525',
            'uhti': 'w1742816563525c9833dba080',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            # 'cookie': 'afUserId=30347cb5-2a3d-42e2-9815-5a4fbd08ef12-p; cf_clearance=8_qQn4VR72eLnBijfaLv9I4hkaY3plO1NH1ljXm3WvA-1742814565-1.2.1.1-09GmwDn9BFU0pui5568wPGvHS4PXuCCXqCSo_7PLqbucEHrenVMKDrFqKCVLHeKfDjotVbvTvQH6d5_Se42Q8Ya64jL4J2XPVsJgNCKif.6nzBfGqQwCg6tANqq2WMtTBhTcKoukthyQDqn_XfXuMLTG_ZDb87RvtX9wgi1IsIkIyCZRT8S_ZUbS29WHYcHmtUP7cgkdHpxgEVLvxQx_rqZRm41nPeX7mR_OWDaq.MH7u5SWCjFVegOGYatYASpIduoE2Xdn0UHBM8wYSaQNLLxIaMpEdKKWDCe4MSD36U1mbznDXNvvfShLTTq1nHKr2jI42Ox5h_JAktLjttxGDKAsLxCan3hCJDwmFBzPqSOCW34tVmnIef3oxuqDenY_CTZaBMCLrSNdmqPiVjMmRnoOJdhWueZfvjsKmt9lwxw; _cfuvid=m4miLGs.F_qcap2EGiscj69qBe7KK..PwH74bEtjDc8-1742814565989-0.0.1.1-604800000; theme=white; fingerprint-1742814602227-35951.29999999888-0.08677358664262758=true; terminalCode-1742814602229-35953-0.4770093689235748=true; BITGET_LOCAL_COOKIE={%22bitget_lang%22:%22ru%22%2C%22bitget_unit%22:%22USD%22%2C%22bitget_showasset%22:false%2C%22bitget_theme%22:%22dark%22%2C%22bitget_valuationunit_new%22:1%2C%22bitget_layout%22:%22right%22}; _dx_kvani5r=ff2938641d22d1684d2059a361659d7780edacb6744536dea1236a08492126b449b3652f; __adroll_fpc=1d9ea902b381c4792562bafcc3ecb667-1742814639473; _ym_uid=1742814641730193558; _ym_d=1742814641; _ym_isad=2; _ym_visorc=b; _ga=GA1.1.918121276.1742814645; OptanonAlertBoxClosed=Mon%20Mar%2024%202025%2014:10:59%20GMT+0300%20(%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C%20%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%BE%D0%B5%20%D0%B2%D1%80%D0%B5%D0%BC%D1%8F); OptanonConsent=isMarketing=1&isStatistic=1; __cf_bm=dt7xy6LDJW92q1zPPGtwpklHT4.83tQ_7QFxLzTpOVw-1742816421-1.0.1.1-a_pLegn_Od4ClimhLlrFAj4L9tD4zpDdr6UboyV4m8w0y9c_EEEi_y5XmCUnykDKDs_hWMoXvRiCpQgatkmunhG9aPsNl4DE_zqhuQtA7SQ; dy_token=67e144b06B0c9rJN5WANBfxM7GEUDBfNAPI3FoP1; __ar_v4=R3652JF77NH6ZC5OBZHWIH%3A20250323%3A4%7C2WBEMJJKHFG5PLSUZ7B5OY%3A20250323%3A4; _ga_Z8Q93KHR0F=GS1.1.1742814645.1.1.1742816559.60.0.0',
        }

        json_data = {
            'matchUserAssets': False,
            'matchVipProduct': False,
            'savingsReq': True,
            'searchObj': {},
            'locale': 'ru',
        }

        response = requests.post(
            'https://www.bitget.com/v1/finance/savings/product/list',
            cookies=cookies,
            headers=headers,
            json=json_data,
        )
        self.logger.debug(f"API request to Bitget, status code: {response.status_code}")
        return response

    def parse_response(self, data: list, coin: str) -> dict:
        """
        Парсит данные от Bitget и возвращает их в нужном формате.
        """
        result = {
            "exchange": "Bitget",
            "coin": coin,
            "holdPosList": [],  # Гибкий стейкинг
            "lockPosList": [],  # Фиксированный стейкинг
            "cost": "0%"
        }

        all_apy = []

        # Обрабатываем данные о монетах
        for item in data:
            if not item.get("bizLineProductList"):
                continue

            for product_group in item["bizLineProductList"]:
                if not product_group.get("productList"):
                    continue

                for product in product_group["productList"]:
                    # Проверяем, что продукт относится к нужной монете
                    if product.get("coinName") != coin:
                        continue

                    # Получаем APY
                    apy = self._get_product_apy(product)
                    if not apy:
                        continue

                    # Определяем тип стейкинга
                    period = product.get("period", 0)
                    if period == 0:  # Гибкий стейкинг
                        result["holdPosList"].append({
                            "days": 0,
                            "apy": round(float(apy), 2),
                            "min_amount": 0,
                            "max_amount": 0
                        })
                    else:  # Фиксированный стейкинг
                        result["lockPosList"].append({
                            "days": period,
                            "apy": round(float(apy), 2),
                            "min_amount": 0,
                            "max_amount": 0
                        })
                    all_apy.append(float(apy))

        # Формируем строку cost
        if all_apy:
            min_apy = round(min(all_apy), 2)
            max_apy = round(max(all_apy), 2)
            result["cost"] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"

        return result

    def _get_product_apy(self, product: dict) -> str:
        """
        Извлекает APY из продукта.
        """
        # Сначала пробуем получить из apyList
        if product.get("apyList") and len(product["apyList"]) > 0:
            return product["apyList"][0].get("apy", "0")
        
        # Затем пробуем получить из maxApy/minApy
        if product.get("maxApy"):
            return product["maxApy"]
        if product.get("minApy"):
            return product["minApy"]
        
        return "0"