from .base_parser import BaseParser
import requests

class OkxParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin).upper()
            
            response = self._make_api_request()
            if not response:
                return self._empty_response(normalized_coin)

            return self.parse_response(response.json(), normalized_coin)

        except Exception as e:
            self.logger.error(f"OKX parser error: {str(e)}")
            return self._empty_response(normalized_coin)

    def _make_api_request(self):
        """Выполняет запрос к API OKX"""

        cookies = {
            'devId': '94727b25-a43b-495e-94c2-f407d658a415',
            'ok_prefer_udColor': '0',
            'ok_prefer_udTimeZone': '0',
            'first_ref': 'https%3A%2F%2Fwww.google.com%2F',
            'intercom-id-ny9cf50h': 'e60cce08-48a7-465b-ad22-ae15b3fa393a',
            'intercom-device-id-ny9cf50h': '0fd35e06-bdf1-478f-aa01-0e0cbd281dfa',
            'OptanonAlertBoxClosed': '2025-04-26T15:03:41.738Z',
            '_ym_uid': '1745679850238349445',
            '_ym_d': '1745679850',
            'locale': 'en_US',
            'fingerprint_id': '94727b25-a43b-495e-94c2-f407d658a415',
            'amp_21c676': 'Mwo8aRevxTlKyY4PE_x_Og...1iqm02rj2.1iqm0cd4r.5.1.6',
            'ok_prefer_currency': '%7B%22currencyId%22%3A0%2C%22isDefault%22%3A1%2C%22isPremium%22%3Afalse%2C%22isoCode%22%3A%22USD%22%2C%22precision%22%3A2%2C%22symbol%22%3A%22%24%22%2C%22usdToThisRate%22%3A1%2C%22usdToThisRatePremium%22%3A1%2C%22displayName%22%3A%22USD%22%7D',
            'OptanonConsent': 'isGpcEnabled=0&datestamp=Sun+May+11+2025+15%3A31%3A47+GMT%2B0300+(%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C+%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%BE%D0%B5+%D0%B2%D1%80%D0%B5%D0%BC%D1%8F)&version=202405.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&landingPath=NotLandingPage&groups=C0004%3A0%2CC0002%3A0%2CC0003%3A0%2CC0001%3A1&geolocation=US%3BIL&AwaitingReconsent=false',
            'intercom-session-ny9cf50h': '',
            'ok_site_info': '=0HOxojI5RXa05WZiwiIMFkQPx0Rfh1SPJiOiUGZvNmIsISWCJiOi42bpdWZyJye',
            'ok-exp-time': '1747165393751',
            '_gid': 'GA1.2.2097282193.1747165397',
            'tmx_session_id': 'x6nvqp9dpz_1747165399811',
            '_ym_isad': '2',
            '_ym_visorc': 'b',
            'fp_s': '0',
            'okg.currentMedia': 'sm',
            'traceId': '2120371655586120002',
            '_ga': 'GA1.1.22056138.1745679845',
            '_ga_G0EKWWQGTZ': 'GS2.1.s1747165397$o7$g1$t1747165566$j55$l0$h0',
            '_monitor_extras': '{"deviceId":"fjTAxZjPoFUmt9veuDx-gc","eventId":29,"sequenceNumber":29}',
            '__cf_bm': 'tinko.waewOx1OWh2YWJGgXj9SucM.acAXCKJapM98I-1747166297-1.0.1.1-sl4dfG3kL8GE1xNcPxEGdaT5j0o0aIlZtooKkApfc1_pobVjSN8d8vQ0ISny6s_rzrnkW4Op2D9c1pvlV.G8UOSJa7hGfZSUZgfUhBev5fY',
            'ok-ses-id': '1uuQcMuTqTSFSxt5w6nKfHd6e2InHlrjQ5pp+qd6BpEa4DIs2SVilMgGfI/v+GfIv7S+oWH/Dn6B19FvPqC+ssO9mfk0hYkw0Cen9+kuxpdUgaJkY0C1uvrHl4VO3KKa',
        }

        headers = {
            'accept': 'application/json',
            'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
            'app-type': 'web',
            'devid': '94727b25-a43b-495e-94c2-f407d658a415',
            'priority': 'u=1, i',
            'referer': 'https://www.okx.com/earn/simple-earn',
            'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            'x-cdn': 'https://www.okx.com',
            'x-fptoken': 'eyJraWQiOiIxNjgzMzgiLCJhbGciOiJFUzI1NiJ9.eyJpYXQiOjE3NDcxNjU0MDUsImVmcCI6InJmRldUclI1U1oxWnB0ZWhPcytrejUySlZLWUFaTERTSVFvMUdRczJWYVdFejRBenBzR0JQN2FXaXhsbjBFaW4iLCJkaWQiOiIiLCJjcGsiOiJNRmt3RXdZSEtvWkl6ajBDQVFZSUtvWkl6ajBEQVFjRFFnQUVpL1A1M3k4ekJ4QUphUWMrTjRJWXZUbFVJeTZEYnZESGVNcG5XcjUvZU02dXU0Z2FoN1ZnTTlmSEJrUHFWa0N6VU1LbEpQZmtLMC9nOGhMMmd4eWpZQT09In0.jG12xSYUV5xx5s_bj9JMOpbr7hZXJShNVVT2-ApSjQYEUqLLXRn8zkFtoTI8EoHog4SMw1KyQv-sAaAR0yJUSg',
            'x-fptoken-signature': '{P1363}Kgw59E4LcwvatVRi6u76af19er/JiPH+CSLvXtfhrhTsBPbqU217wcaFasFR0IuUTCLtBn3jtIrJ6JTvvgsFKA==',
            'x-id-group': '2120371655586120002-c-17',
            'x-locale': 'en_US',
            'x-request-timestamp': '1747166347314',
            'x-simulated-trading': 'undefined',
            'x-site-info': '=0HOxojI5RXa05WZiwiIMFkQPx0Rfh1SPJiOiUGZvNmIsISWCJiOi42bpdWZyJye',
            'x-utc': '3',
            'x-zkdex-env': '0',
            # 'cookie': 'devId=94727b25-a43b-495e-94c2-f407d658a415; ok_prefer_udColor=0; ok_prefer_udTimeZone=0; first_ref=https%3A%2F%2Fwww.google.com%2F; intercom-id-ny9cf50h=e60cce08-48a7-465b-ad22-ae15b3fa393a; intercom-device-id-ny9cf50h=0fd35e06-bdf1-478f-aa01-0e0cbd281dfa; OptanonAlertBoxClosed=2025-04-26T15:03:41.738Z; _ym_uid=1745679850238349445; _ym_d=1745679850; locale=en_US; fingerprint_id=94727b25-a43b-495e-94c2-f407d658a415; amp_21c676=Mwo8aRevxTlKyY4PE_x_Og...1iqm02rj2.1iqm0cd4r.5.1.6; ok_prefer_currency=%7B%22currencyId%22%3A0%2C%22isDefault%22%3A1%2C%22isPremium%22%3Afalse%2C%22isoCode%22%3A%22USD%22%2C%22precision%22%3A2%2C%22symbol%22%3A%22%24%22%2C%22usdToThisRate%22%3A1%2C%22usdToThisRatePremium%22%3A1%2C%22displayName%22%3A%22USD%22%7D; OptanonConsent=isGpcEnabled=0&datestamp=Sun+May+11+2025+15%3A31%3A47+GMT%2B0300+(%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C+%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%BE%D0%B5+%D0%B2%D1%80%D0%B5%D0%BC%D1%8F)&version=202405.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&landingPath=NotLandingPage&groups=C0004%3A0%2CC0002%3A0%2CC0003%3A0%2CC0001%3A1&geolocation=US%3BIL&AwaitingReconsent=false; intercom-session-ny9cf50h=; ok_site_info==0HOxojI5RXa05WZiwiIMFkQPx0Rfh1SPJiOiUGZvNmIsISWCJiOi42bpdWZyJye; ok-exp-time=1747165393751; _gid=GA1.2.2097282193.1747165397; tmx_session_id=x6nvqp9dpz_1747165399811; _ym_isad=2; _ym_visorc=b; fp_s=0; okg.currentMedia=sm; traceId=2120371655586120002; _ga=GA1.1.22056138.1745679845; _ga_G0EKWWQGTZ=GS2.1.s1747165397$o7$g1$t1747165566$j55$l0$h0; _monitor_extras={"deviceId":"fjTAxZjPoFUmt9veuDx-gc","eventId":29,"sequenceNumber":29}; __cf_bm=tinko.waewOx1OWh2YWJGgXj9SucM.acAXCKJapM98I-1747166297-1.0.1.1-sl4dfG3kL8GE1xNcPxEGdaT5j0o0aIlZtooKkApfc1_pobVjSN8d8vQ0ISny6s_rzrnkW4Op2D9c1pvlV.G8UOSJa7hGfZSUZgfUhBev5fY; ok-ses-id=1uuQcMuTqTSFSxt5w6nKfHd6e2InHlrjQ5pp+qd6BpEa4DIs2SVilMgGfI/v+GfIv7S+oWH/Dn6B19FvPqC+ssO9mfk0hYkw0Cen9+kuxpdUgaJkY0C1uvrHl4VO3KKa',
        }

        params = {
            'type': 'all',
            't': '1747166347314',
        }

        response = requests.get(
            'https://www.okx.com/priapi/v1/earn/simple-earn/all-products',
            params=params,
            cookies=cookies,
            headers=headers,
        )
            
        if not response.ok:
            self.logger.error(f"OKX API error: {response.status_code}")
            return None
            
        return response
    
    def parse_response(self, data: dict, coin: str) -> dict:
        """Парсит ответ API OKX"""
        result = self._empty_response(coin)
        apy_values = []
        
        for currency in data.get('data', {}).get('allProducts', {}).get('currencies', []):
            if self._is_target_currency(currency, coin):
                self._process_currency_products(currency, result, apy_values, coin)
                
        self._calculate_apy_range(result, apy_values)
        return result

    def _is_target_currency(self, currency: dict, target_coin: str) -> bool:
        """Проверяет совпадение валюты"""
        interest_currency = currency.get('investCurrency', {})
        return interest_currency.get('currencyName', '').upper() == target_coin

    def _process_currency_products(self, currency: dict, result: dict, apy_values: list, coin: str):
        """Обрабатывает продукты для конкретной валюты"""
        for product in currency.get('products', []):
            try:
                apy = self._parse_apy(product.get('rate', {}))
                days, is_flexible = self._get_days_and_type(product)
                
                pos = {
                    'days': days,
                    'apy': apy,
                    'min_amount': 0,
                    'max_amount': 0
                }
                
                if is_flexible:
                    result['holdPosList'].append(pos)
                    self.logger.debug(f"[OKX:{coin}] Flexible product: {pos}")
                else:
                    result['lockPosList'].append(pos)
                    self.logger.debug(f"[OKX:{coin}] Locked product: {pos}")
                    
                apy_values.append(apy)
                
            except Exception as e:
                self.logger.warning(f"[OKX:{coin}] Error processing product: {str(e)}")

    def _get_days_and_type(self, product: dict) -> tuple:
        """Определяет срок и тип продукта"""
        term = product.get('term', {})
        term_value = term.get('value', -1)
        term_type = term.get('type', '')
        
        # Гибкие продукты имеют term.value = -1 или productsType = 1
        if term_value == -1 or product.get('productsType') == 1:
            return 0, True  # 0 дней для гибких продуктов
        
        # Фиксированные продукты с реальным сроком
        if term_type == 'DAY' and term_value > 0:
            return term_value, False
        
        # По умолчанию считаем гибким
        return 0, True

    def _parse_apy(self, rate_data: dict) -> float:
        """Извлекает APY из структуры rate"""
        try:
            rate_values = rate_data.get('rateNum', {}).get('value', ['0'])[0]
            return float(rate_values.replace('%', ''))
        except:
            return 0.0

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
        """Возвращает пустой ответ"""
        return {
            'exchange': 'OKX',
            'coin': coin,
            'holdPosList': [],
            'lockPosList': [],
            'cost': '0%'
        }