from .base_parser import BaseParser
import requests
import logging

class GateIoParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin)

            cookies = {
                'afUserId': '4bda6998-d3e9-44cd-b17f-e8bc0d122342-p',
                'AF_SYNC': '1742545429116',
                '_ga': 'GA1.2.1364120040.1742545440',
                '_gid': 'GA1.2.859918303.1742545440',
                '_dx_uzZo5y': 'e98b47807b8a9af8d24c7cda8665cdd1254cf5958dc18aa7ad3746a0fa4df2e87bc10500',
                'finger_print': '67dd2220h0k0TwLkPqOsMebV6vmUQsIMuqo8NJC1',
                'lang': 'ru',
                'lasturl': '%2Fstaking%2Flist',
                '_gat_UA-1833997-40': '1',
                '_ga_JNHPQJS9Q4': 'GS1.2.1742569795.2.0.1742569795.60.0.0',
                'login_notice_check': '%2F',
                'AWSALB': 'ainYVjmFLndxl3ofURdeUYOeUdmyDfvcjoIf87pXho+eEPmOCh9roPg49jjMI5n6cQjl2WsnoLZ8CQsc+vvH28qFV98H7k4X8eiCfkuLbm3m67R27fyd5axBp4pX',
                'AWSALBCORS': 'ainYVjmFLndxl3ofURdeUYOeUdmyDfvcjoIf87pXho+eEPmOCh9roPg49jjMI5n6cQjl2WsnoLZ8CQsc+vvH28qFV98H7k4X8eiCfkuLbm3m67R27fyd5axBp4pX',
            }

            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
                'baggage': 'sentry-environment=production,sentry-release=bmX7-kFrnGN2QHKxsMHw9,sentry-public_key=49348d5eaee2418db953db695c5c9c57,sentry-trace_id=830282dfd3a14307bb908e53b2df3f61,sentry-sample_rate=0.1,sentry-transaction=%2Fstaking%2Flist,sentry-sampled=false',
                'csrftoken': '1',
                'priority': 'u=1, i',
                'referer': 'https://www.gate.io/ru/staking/list',
                'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'sentry-trace': '830282dfd3a14307bb908e53b2df3f61-81ec438adb6bc0b6-0',
                'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
            }

            params = {
                'page': '1',
                'limit': '8',
                'hide_zero_available': '0',
            }

            response = requests.get(
                'https://www.gate.io/apiw/v2/earn/staking/coins-list',
                params=params,
                cookies=cookies,
                headers=headers
            )

            if not response.ok:
                self.logger.error(f"Gate.io API error: {response.status_code}")
                return {}

            # Обрабатываем данные, начиная с ключа 'data'
            return self.parse_response(response.json().get('data', {}), normalized_coin)
        except Exception as e:
            self.logger.error(f"Gate.io parser error: {str(e)}")
            return {}

    def parse_response(self, data: dict, coin: str) -> dict:
        result = {
            'exchange': 'Gate.io',
            'coin': coin,
            'holdPosList': [],  # Гибкий стейкинг
            'lockPosList': [],  # Фиксированный стейкинг
            'cost': '0%'  # По умолчанию
        }

        all_apy = []

        # Обрабатываем данные о монетах
        for item in data.get('coins', []):
            if item.get('coin') != coin:
                continue

            # Обработка гибкого стейкинга (type = 0)
            if item.get('type') == 0:
                apy = float(item.get('rate', 0))
                if apy > 0:
                    result['holdPosList'].append({
                        'days': 0,  # Гибкий стейкинг не имеет срока
                        'apy': round(apy, 2),  # Округляем до сотых
                        'min_amount': 0,  # Минимальная сумма не указана
                        'max_amount': float('inf')  # Без ограничений
                    })
                    all_apy.append(apy)

            # Обработка фиксированного стейкинга (type = 1)
            elif item.get('type') == 1:
                apy = float(item.get('rate', 0))
                if apy > 0:
                    result['lockPosList'].append({
                        'days': self._get_lock_duration(item),  # Срок блокировки
                        'apy': round(apy, 2),  # Округляем до сотых
                        'min_amount': float(item.get('min_mortgage_amount', 0)),
                        'max_amount': float(item.get('day_max_mortgage_amount', 'inf'))
                    })
                    all_apy.append(apy)

                # Если есть дополнительные ставки (rates), добавляем их
                rates = item.get('rates', [])
                for rate in rates:
                    if rate:  # Проверяем, что rate не пустой
                        rate_apy = float(rate)
                        if rate_apy > 0:
                            all_apy.append(rate_apy)

        # Формируем строку cost
        if all_apy:
            min_apy = round(min(all_apy), 2)
            max_apy = round(max(all_apy), 2)
            result['cost'] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"

        return result

    def _get_lock_duration(self, item: dict) -> int:
        """ Получаем срок блокировки из данных """
        extra = item.get('extra', {})
        redeem_minday = int(extra.get('redeem_minday', 0))
        redeem_maxday = int(extra.get('redeem_maxday', 0))

        # Возвращаем средний срок, если указаны min и max
        if redeem_minday and redeem_maxday:
            return (redeem_minday + redeem_maxday) // 2
        return redeem_minday or redeem_maxday or 0