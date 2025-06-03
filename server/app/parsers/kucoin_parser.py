from .base_parser import BaseParser
import requests

class KucoinParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin).upper()
            
            response = self._make_api_request(normalized_coin)
            if not response:
                return self._empty_response(normalized_coin)

            return self.parse_response(response.json(), normalized_coin)

        except Exception as e:
            self.logger.error(f"KuCoin parser error: {str(e)}")
            return self._empty_response(normalized_coin)

    def _make_api_request(self, coin: str):
        """Выполняет запрос к API KuCoin"""

        cookies = {
            'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%2219676fecb055ec-04d4ce7c5010db4-26011c51-1049088-19676fecb066df%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E8%87%AA%E7%84%B6%E6%90%9C%E7%B4%A2%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk2NzZmZWNiMDU1ZWMtMDRkNGNlN2M1MDEwZGI0LTI2MDExYzUxLTEwNDkwODgtMTk2NzZmZWNiMDY2ZGYifQ%3D%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%7D',
            'X_GRAY_TEMP_UUID': '9e74e7c8-a66d-49fd-b568-8e969e2a21d1',
            'smidV2': '20250504151639a4e12491183ac04f83686b95dc1591c800b27bb8c588e7930',
            '.thumbcache_c294bfec3668b22bff5f6aa9bb528f6a': 'fHQ3H8PVRHt3HHgalsQxTBA5npMRpMleU6JTsFr3glgZn8/Y7uE4xp4xS44ZzaeOwpi9/+KgZ3fHVoswQ5/a+g%3D%3D',
            '_fbp': 'fb.1.1746797565002.206327132',
            'WEBGRAY': 'beta_web:kucoin_convert_rn',
            '__cf_bm': '2PIva.ixD6_1qI4gmYhy3PnVnJ5PnwyAeASeKOBuvXw-1747254466-1.0.1.1-a20.BY2c2KPttP2lyfSDPn_rjeMYLktI69SGDEjX3o.P_Xb7zao.P.HMkaApz6tNoCsx_bY9kUl_u9BdasEBSCjFZ5xusqDsTcTnxkQNhWk',
            '_cfuvid': 'WllUZ1o8_QN9hLOADPj2XLJD1tBsJnLz5McwglFgtpM-1747254466454-0.0.1.1-604800000',
            'cf_clearance': 'W5vsVlgjR.Rnwg14kosBSILcU7hdud8HilwRplx6KC0-1747254467-1.2.1.1-9dC4K_N5rd_9aFqaQdd3giBRgBDO_qdnpgI21eJOyZET7DDiedicqq9n1eTY2MJCnavedQkvy26i46CKg9aKR941aq_Xx9sF_xPcvm5mA.7qJkqOBQRqTQV9bOfQD6aUpYMsGXoGR3YweMul_KHhbTfNoK8BIZEGpcuLlnbUXMrVj2kV4_eb6T3E12WNVmtAtjNJwNp7A6kaUZLR5vuythUUhQHKQZWwAWY8KG3FMlyiyS3riJbYdBmUO__dM86VSxKOxLbHZ3BzicP44OLrzO_6UBsBRqMj8fiEixmIqRI318x6KfJBH5ZqIBU_P_5y_fDDOkHYClGhALB.DlchqtEghMdUsZk0jfukAGKA99M',
            '_gid': 'GA1.2.1524377882.1747254468',
            'X-GRAY': 'xgray-kcmg-20250508&xgray-toc&xgray-defaultpricerange',
            'X_GRAY_TMP': '1747227941258',
            '_gat_UA-46608064-1': '1',
            '_ga_YHWW24NNH9': 'GS2.1.s1747254467$o6$g1$t1747255281$j60$l0$h0',
            '_ga': 'GA1.1.2113175255.1745753131',
            '_uetsid': '5f86cb80310311f0b192fb7d9970c342',
            '_uetvid': '16d768602cda11f081738b06f396d2ee',
            'AWSALB': '/THinphZ+dEuM9AZD72PIwPOXlYKHPTmLZoDLnvbe6TplVLQX+Ef1fahEHpB2DAp91SP5gu1LgHoUv9R1LUmPmLuxgwyF9YfJUz28420yoqcqd/63qcEgGo7Qf8B',
            'AWSALBCORS': '/THinphZ+dEuM9AZD72PIwPOXlYKHPTmLZoDLnvbe6TplVLQX+Ef1fahEHpB2DAp91SP5gu1LgHoUv9R1LUmPmLuxgwyF9YfJUz28420yoqcqd/63qcEgGo7Qf8B',
        }

        headers = {
            'accept': 'application/json',
            'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
            'priority': 'u=1, i',
            'referer': 'https://www.kucoin.com/ru/earn',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            # 'cookie': 'sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%2219676fecb055ec-04d4ce7c5010db4-26011c51-1049088-19676fecb066df%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E8%87%AA%E7%84%B6%E6%90%9C%E7%B4%A2%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk2NzZmZWNiMDU1ZWMtMDRkNGNlN2M1MDEwZGI0LTI2MDExYzUxLTEwNDkwODgtMTk2NzZmZWNiMDY2ZGYifQ%3D%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%7D; X_GRAY_TEMP_UUID=9e74e7c8-a66d-49fd-b568-8e969e2a21d1; smidV2=20250504151639a4e12491183ac04f83686b95dc1591c800b27bb8c588e7930; .thumbcache_c294bfec3668b22bff5f6aa9bb528f6a=fHQ3H8PVRHt3HHgalsQxTBA5npMRpMleU6JTsFr3glgZn8/Y7uE4xp4xS44ZzaeOwpi9/+KgZ3fHVoswQ5/a+g%3D%3D; _fbp=fb.1.1746797565002.206327132; WEBGRAY=beta_web:kucoin_convert_rn; __cf_bm=2PIva.ixD6_1qI4gmYhy3PnVnJ5PnwyAeASeKOBuvXw-1747254466-1.0.1.1-a20.BY2c2KPttP2lyfSDPn_rjeMYLktI69SGDEjX3o.P_Xb7zao.P.HMkaApz6tNoCsx_bY9kUl_u9BdasEBSCjFZ5xusqDsTcTnxkQNhWk; _cfuvid=WllUZ1o8_QN9hLOADPj2XLJD1tBsJnLz5McwglFgtpM-1747254466454-0.0.1.1-604800000; cf_clearance=W5vsVlgjR.Rnwg14kosBSILcU7hdud8HilwRplx6KC0-1747254467-1.2.1.1-9dC4K_N5rd_9aFqaQdd3giBRgBDO_qdnpgI21eJOyZET7DDiedicqq9n1eTY2MJCnavedQkvy26i46CKg9aKR941aq_Xx9sF_xPcvm5mA.7qJkqOBQRqTQV9bOfQD6aUpYMsGXoGR3YweMul_KHhbTfNoK8BIZEGpcuLlnbUXMrVj2kV4_eb6T3E12WNVmtAtjNJwNp7A6kaUZLR5vuythUUhQHKQZWwAWY8KG3FMlyiyS3riJbYdBmUO__dM86VSxKOxLbHZ3BzicP44OLrzO_6UBsBRqMj8fiEixmIqRI318x6KfJBH5ZqIBU_P_5y_fDDOkHYClGhALB.DlchqtEghMdUsZk0jfukAGKA99M; _gid=GA1.2.1524377882.1747254468; X-GRAY=xgray-kcmg-20250508&xgray-toc&xgray-defaultpricerange; X_GRAY_TMP=1747227941258; _gat_UA-46608064-1=1; _ga_YHWW24NNH9=GS2.1.s1747254467$o6$g1$t1747255281$j60$l0$h0; _ga=GA1.1.2113175255.1745753131; _uetsid=5f86cb80310311f0b192fb7d9970c342; _uetvid=16d768602cda11f081738b06f396d2ee; AWSALB=/THinphZ+dEuM9AZD72PIwPOXlYKHPTmLZoDLnvbe6TplVLQX+Ef1fahEHpB2DAp91SP5gu1LgHoUv9R1LUmPmLuxgwyF9YfJUz28420yoqcqd/63qcEgGo7Qf8B; AWSALBCORS=/THinphZ+dEuM9AZD72PIwPOXlYKHPTmLZoDLnvbe6TplVLQX+Ef1fahEHpB2DAp91SP5gu1LgHoUv9R1LUmPmLuxgwyF9YfJUz28420yoqcqd/63qcEgGo7Qf8B',
        }

        params = {
            'keyword': coin,
            'filter_low_return': '0',
            'lang': 'ru_RU',
        }

        response = requests.get(
            'https://www.kucoin.com/_pxapi/pool-staking/v4/low-risk/currencies-products',
            params=params,
            cookies=cookies,
            headers=headers,
        )
        
        if not response.ok:
            self.logger.error(f"KuCoin API error: {response.status_code}")
            return None
            
        return response

    def parse_response(self, data: dict, coin: str) -> dict:
        """Парсит ответ API KuCoin"""
        result = self._empty_response(coin)
        apy_values = []
        
        for currency_data in data.get('data', []):
            if currency_data.get('currency') == coin:
                for product in currency_data.get('products', []):
                    if self._should_include_product(product):
                        self._process_product(product, result, apy_values, coin)
                
        self._calculate_apy_range(result, apy_values)
        return result

    def _should_include_product(self, product: dict) -> bool:
        """Определяет, нужно ли включать продукт в результат"""
        # Исключаем продукты типа SHARKFIN
        return product.get('category') != 'SHARKFIN'

    def _process_product(self, product: dict, result: dict, apy_values: list, coin: str):
        """Обрабатывает отдельный продукт"""
        try:
            apr = float(product.get('apr', '0'))
            duration = int(product.get('duration', 0))
            product_type = product.get('type')
            
            pos = {
                'days': duration,
                'apy': round(apr, 2),
                'min_amount': 0,
                'max_amount': 0
            }
            
            # Определяем тип продукта (гибкий/фиксированный)
            if product_type in ['DEMAND', 'SAVING'] or duration == 0:
                result['holdPosList'].append(pos)
                self.logger.debug(f"[KuCoin:{coin}] Flexible product: {pos}")
            else:
                result['lockPosList'].append(pos)
                self.logger.debug(f"[KuCoin:{coin}] Locked product: {pos}")
                
            apy_values.append(apr)
            
        except Exception as e:
            self.logger.warning(f"[KuCoin:{coin}] Error processing product: {str(e)}")

    def _calculate_apy_range(self, result: dict, apy_values: list):
        """Рассчитывает диапазон APY"""
        if apy_values:
            min_apy = min(apy_values)
            max_apy = max(apy_values)
            result['cost'] = (
                f"{min_apy:.2f}%–{max_apy:.2f}%" 
                if min_apy != max_apy 
                else f"{max_apy:.2f}%"
            )

    def _empty_response(self, coin: str) -> dict:
        """Возвращает пустой ответ для монеты"""
        return {
            'exchange': 'KuCoin',
            'coin': coin,
            'holdPosList': [],
            'lockPosList': [],
            'cost': '0%'
        }