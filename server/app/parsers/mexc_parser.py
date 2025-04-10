from .base_parser import BaseParser
import requests
import json

class MexcParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin)
            cookies = {
                'mxc_theme_main': 'dark',
                'NEXT_LOCALE': 'ru-RU',
                '_ga': 'GA1.1.114621918.1741610140',
                '_fbp': 'fb.1.1741610142411.58479904686401305',
                '_vid_t': 'p3R11Mteg36/mLjcrftnASqMzfjOUgpFFlpE76amu4PFKaLlr1bC7oqxI+7AwdizDvyRkmPvcKJYxwgHf3Mh1AtChTtJQklWXjOOD/E=',
                'mexc_fingerprint_visitorId': 'IadwNjHNNlB07SiJtB9a',
                'mexc_fingerprint_requestId': '1742127479664.8CcR1M',
                '_abck': '66230BA37813DDFAF90A5AC157A6AAE5~0~YAAQrvlVaFiZ/aWVAQAAOgYesg3dkEVQTwWO9Ih0vVWWoHqrzu0XW2hgaWI5dukgmuGNnZnGpxCd8WOQfWQ31VQjC+/tuw30NTEarzVmBr/c2SQtz/WGlvDBfVHs3cbmaXuWYnOAg1gd7a0NCczZ/OyoE6nwYU56tspemm7oLRpIf3dQtKNDLCY0uWaudSEk4Vw0kacDzYDCU9IiqFaUHJB8C5vCLqlIDr0e4Xw4J4iKHispEZENcLHjAVh1NHXi0K0Tz9qgcdAEmnL/AOpPyhROI2WMZmIPwws1flGNfE5QmlznFEHGKwcevBkb0MtFFHV5n6IcxnPyJu2xYXUUnLKW7S6rPoRw3pg5Pg63uMO0yDsLvuJ50y35/JdUFDbi+Dv0eiw3RcCLhdOK1Rdbfj5sp5wby8pnx970iO86Oqg8Tm98yA1pyvt4H1msSw24cPMdcF2Ixsx+Kweb9gBVRwVxT4sUz3DAsDd7cebYYlpSHgyMh2zU0fuAxiXwaPBsA9hHvaGqAfB2L7fLjYDiA9/9w0HjAoH75jk=~-1~-1~-1',
                'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%22195800db12828f-03a7ff702993fb4-26011a51-1049088-195800db12998f%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_landing_page%22%3A%22https%3A%2F%2Fwww.mexc.com%2Fru-RU%2Fstaking%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk1ODAwZGIxMjgyOGYtMDNhN2ZmNzAyOTkzZmI0LTI2MDExYTUxLTEwNDkwODgtMTk1ODAwZGIxMjk5OGYifQ%3D%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%2C%22%24device_id%22%3A%22195800db12828f-03a7ff702993fb4-26011a51-1049088-195800db12998f%22%7D',
                'bm_mi': 'E48D8EF3A4113BEBFE7D21A50EE2867E~YAAQ7m9kX+Iu5IeVAQAA2T8eshuMnXuhLZriD06k31bxxQJHD3JKd2xI59p2YE3ztXrfSKWL9o0xWdQ9LCdRajXrXjp7HaEYse6s+hn1NpNdRWWvNy/TVqJG8B+EZpYw9XVizY2GAtqHoPsbwGzXAn6IzOz/kJ6L0rKHtBNt4sY9P9Y/c4W5/BibDoURLfo6ZT0Ye2doeOJKLnkPLYIcEEE1t1sapt3++oOhRVnHUn0Vp2xXUuJk870TDNPVCfNpLuXdSYmc/lZZHK00XgNK7mVXRnI6Gi91XdOtV9FSfQfSovphpGuVFdACj4sVsnuPfbctHe+bPRiU~1',
                'bm_sv': '0FB26668D9EA67128B41E9C0B9469ACA~YAAQ7m9kX+Mu5IeVAQAA2T8eshvho79PGLLuSo8Hqw3ZdequRv2xf8HPEa70OwLU2kEOnIWlv8Hsz1mebIXuTHrS16LCnEYTBY3wk1BNkc4s66FvCE+kDzH0G2USZh0KYFB2EhhUcB68eRUC87p6iKk1ZZvNwl2OosHDSSCe0RaayNr16oPkcZTk0CF8dv/D8o9APOz4TkJ+BJN/vP1c6c9fbJ2xf6WNzTcxrr8Z25TMbsW0ieZ/wMd3As8Tl/Q=~1',
                'bm_sz': '0317FCEE4FAD3C00557D8DA87B2DA906~YAAQ7m9kX+Qu5IeVAQAA2T8eshtayaHpWnuyT/8IrakxvjvFkNLwZPlm3id47h/p7KH2J0CqWUt577CSccAq0ofvrSgf5Az60JQiiGCmW4GLEXRZIgtlcczuwEU9/0+QOf5vM//c9PyanFeWkZZqXizOmcLCcJHwpMIR0QBBwrCEZFeGxYgNR++ShFgpSdFKfrDt8e+lxOkovX3Eo3SoVCUbLOvjxArBCnEQmvZ8Mm9iQDKLtXhJ9cfAwCuZcRPRRbqM7gypxPy9bSFzgMkNdyLhUdGhp9vWw4G7hjHCU1O4Nc6L9Qvgo06pPT25pss5Okv3yqz1NW4/8JJg8d+l1B9p2Ks5kURWv9c9wShmFoo6hchAf9vR2H23pLDMa5EWxHtqril2bnITpHc9MiWPcxE=~3162689~4404021',
                'RT': '"sl=0&ss=m8gxs3ef&tt=0&bcn=%2F%2F684dd313.akstat.io%2F&z=1&dm=www.mexc.com&si=c4777891-790a-4de5-b1d6-1f5ebe9e84c3&ld=2jpwsc&ul=bx2&hd=c59"',
                '_ga_L6XJCQTK75': 'GS1.1.1742450070.6.0.1742450081.49.0.0',
                'ak_bmsc': '785FBD3F8922EF21F381358289F0FB3F~000000000000000000000000000000~YAAQ7m9kX+ou5IeVAQAAVkUeshutHq9SZCXLOyjeaaLeKLPS7gbF5LHI7W0J0LdbjlPo/KFC3Faws2C2pO0+Id0mbazEbSwe6bpFWA5cHNzbToChQy90kA3G2qvMhrKfimhrJBN2/h0E5Li03nmilPrjckrbeMvvAjaB3Oqz1SkBF4EnQee22LW8+a+uPqzaHX1vRZMA8c5IRDbHbXqAHHE+nxc8+gP5Jz20EC7jTuC8fhIZ+LvU09qwQtLtlnnR1PEeVFIoOtw1C8oqUsC/lB4MAu0dBctwLbpUGAzms955wNtE8aGgOZqjPp/3bYrcqWz8sXGMI3I76dztmgQq+aRJhMEfFwrFWTekPNB2739yvSmPzQe2MH7LgS/K2z3oJU/saKkxAOMI0g8FqXKsjK9b9CEKuKw/PMWOEgmZHpJbmVKyxIfN8oJ5C6gzReL3gTfcmIB/InOVZcr/DFXuNeXiZWkzFsmui1rFQdqNDw==',
            }

            headers = {
                'accept': '*/*',
                'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
                'baggage': 'sentry-environment=prd,sentry-release=production%20-%20v1.17.10%20-%20dffca04,sentry-public_key=6274435629fc4fd0aad4f5232b5c16aa,sentry-trace_id=29155a40cd294fbe98070aab4e5c0679,sentry-sample_rate=0.1,sentry-transaction=%2Fstaking,sentry-sampled=false',
                'language': 'ru-RU',
                'pragma': 'akamai-x-cache-on',
                'priority': 'u=1, i',
                'referer': 'https://www.mexc.com/ru-RU/staking',
                'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'sentry-trace': '29155a40cd294fbe98070aab4e5c0679-a7d73c0bf2f7b59a-0',
                'trochilus-trace-id': '0736fbcc-18ae-4727-bc10-92db176e71fb-0005',
                'trochilus-uid': '',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
                # 'cookie': 'mxc_theme_main=dark; NEXT_LOCALE=ru-RU; _ga=GA1.1.114621918.1741610140; _fbp=fb.1.1741610142411.58479904686401305; _vid_t=p3R11Mteg36/mLjcrftnASqMzfjOUgpFFlpE76amu4PFKaLlr1bC7oqxI+7AwdizDvyRkmPvcKJYxwgHf3Mh1AtChTtJQklWXjOOD/E=; mexc_fingerprint_visitorId=IadwNjHNNlB07SiJtB9a; mexc_fingerprint_requestId=1742127479664.8CcR1M; _abck=66230BA37813DDFAF90A5AC157A6AAE5~0~YAAQrvlVaFiZ/aWVAQAAOgYesg3dkEVQTwWO9Ih0vVWWoHqrzu0XW2hgaWI5dukgmuGNnZnGpxCd8WOQfWQ31VQjC+/tuw30NTEarzVmBr/c2SQtz/WGlvDBfVHs3cbmaXuWYnOAg1gd7a0NCczZ/OyoE6nwYU56tspemm7oLRpIf3dQtKNDLCY0uWaudSEk4Vw0kacDzYDCU9IiqFaUHJB8C5vCLqlIDr0e4Xw4J4iKHispEZENcLHjAVh1NHXi0K0Tz9qgcdAEmnL/AOpPyhROI2WMZmIPwws1flGNfE5QmlznFEHGKwcevBkb0MtFFHV5n6IcxnPyJu2xYXUUnLKW7S6rPoRw3pg5Pg63uMO0yDsLvuJ50y35/JdUFDbi+Dv0eiw3RcCLhdOK1Rdbfj5sp5wby8pnx970iO86Oqg8Tm98yA1pyvt4H1msSw24cPMdcF2Ixsx+Kweb9gBVRwVxT4sUz3DAsDd7cebYYlpSHgyMh2zU0fuAxiXwaPBsA9hHvaGqAfB2L7fLjYDiA9/9w0HjAoH75jk=~-1~-1~-1; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22195800db12828f-03a7ff702993fb4-26011a51-1049088-195800db12998f%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_landing_page%22%3A%22https%3A%2F%2Fwww.mexc.com%2Fru-RU%2Fstaking%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk1ODAwZGIxMjgyOGYtMDNhN2ZmNzAyOTkzZmI0LTI2MDExYTUxLTEwNDkwODgtMTk1ODAwZGIxMjk5OGYifQ%3D%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%2C%22%24device_id%22%3A%22195800db12828f-03a7ff702993fb4-26011a51-1049088-195800db12998f%22%7D; bm_mi=E48D8EF3A4113BEBFE7D21A50EE2867E~YAAQ7m9kX+Iu5IeVAQAA2T8eshuMnXuhLZriD06k31bxxQJHD3JKd2xI59p2YE3ztXrfSKWL9o0xWdQ9LCdRajXrXjp7HaEYse6s+hn1NpNdRWWvNy/TVqJG8B+EZpYw9XVizY2GAtqHoPsbwGzXAn6IzOz/kJ6L0rKHtBNt4sY9P9Y/c4W5/BibDoURLfo6ZT0Ye2doeOJKLnkPLYIcEEE1t1sapt3++oOhRVnHUn0Vp2xXUuJk870TDNPVCfNpLuXdSYmc/lZZHK00XgNK7mVXRnI6Gi91XdOtV9FSfQfSovphpGuVFdACj4sVsnuPfbctHe+bPRiU~1; bm_sv=0FB26668D9EA67128B41E9C0B9469ACA~YAAQ7m9kX+Mu5IeVAQAA2T8eshvho79PGLLuSo8Hqw3ZdequRv2xf8HPEa70OwLU2kEOnIWlv8Hsz1mebIXuTHrS16LCnEYTBY3wk1BNkc4s66FvCE+kDzH0G2USZh0KYFB2EhhUcB68eRUC87p6iKk1ZZvNwl2OosHDSSCe0RaayNr16oPkcZTk0CF8dv/D8o9APOz4TkJ+BJN/vP1c6c9fbJ2xf6WNzTcxrr8Z25TMbsW0ieZ/wMd3As8Tl/Q=~1; bm_sz=0317FCEE4FAD3C00557D8DA87B2DA906~YAAQ7m9kX+Qu5IeVAQAA2T8eshtayaHpWnuyT/8IrakxvjvFkNLwZPlm3id47h/p7KH2J0CqWUt577CSccAq0ofvrSgf5Az60JQiiGCmW4GLEXRZIgtlcczuwEU9/0+QOf5vM//c9PyanFeWkZZqXizOmcLCcJHwpMIR0QBBwrCEZFeGxYgNR++ShFgpSdFKfrDt8e+lxOkovX3Eo3SoVCUbLOvjxArBCnEQmvZ8Mm9iQDKLtXhJ9cfAwCuZcRPRRbqM7gypxPy9bSFzgMkNdyLhUdGhp9vWw4G7hjHCU1O4Nc6L9Qvgo06pPT25pss5Okv3yqz1NW4/8JJg8d+l1B9p2Ks5kURWv9c9wShmFoo6hchAf9vR2H23pLDMa5EWxHtqril2bnITpHc9MiWPcxE=~3162689~4404021; RT="sl=0&ss=m8gxs3ef&tt=0&bcn=%2F%2F684dd313.akstat.io%2F&z=1&dm=www.mexc.com&si=c4777891-790a-4de5-b1d6-1f5ebe9e84c3&ld=2jpwsc&ul=bx2&hd=c59"; _ga_L6XJCQTK75=GS1.1.1742450070.6.0.1742450081.49.0.0; ak_bmsc=785FBD3F8922EF21F381358289F0FB3F~000000000000000000000000000000~YAAQ7m9kX+ou5IeVAQAAVkUeshutHq9SZCXLOyjeaaLeKLPS7gbF5LHI7W0J0LdbjlPo/KFC3Faws2C2pO0+Id0mbazEbSwe6bpFWA5cHNzbToChQy90kA3G2qvMhrKfimhrJBN2/h0E5Li03nmilPrjckrbeMvvAjaB3Oqz1SkBF4EnQee22LW8+a+uPqzaHX1vRZMA8c5IRDbHbXqAHHE+nxc8+gP5Jz20EC7jTuC8fhIZ+LvU09qwQtLtlnnR1PEeVFIoOtw1C8oqUsC/lB4MAu0dBctwLbpUGAzms955wNtE8aGgOZqjPp/3bYrcqWz8sXGMI3I76dztmgQq+aRJhMEfFwrFWTekPNB2739yvSmPzQe2MH7LgS/K2z3oJU/saKkxAOMI0g8FqXKsjK9b9CEKuKw/PMWOEgmZHpJbmVKyxIfN8oJ5C6gzReL3gTfcmIB/InOVZcr/DFXuNeXiZWkzFsmui1rFQdqNDw==',
            }

            params = ''
            response = requests.get(
                'https://www.mexc.com/api/operateactivity/staking',
                cookies=cookies,
                headers=headers,
                params=params,
                timeout=10
            )

            if not response.ok:
                self.logger.error(f"Mexc API error: {response.status_code}")
                return {}

            return self.parse_response(response.json(), normalized_coin)
            
        except Exception as e:
            self.logger.error(f"Mexc parser error: {str(e)}")
            return {}

    def parse_response(self, data: dict, coin: str) -> dict:
        result = {
            'exchange': 'Mexc',
            'coin': coin,
            'holdPosList': [],
            'lockPosList': [],
            'cost': '0%'  # По умолчанию
        }
        
        all_apy = []
        
        for item in data.get('data', []):
            if item.get('currency') != coin:
                continue

            # Обработка гибкого стейкинга (HOLD_POS)
            if item.get('holdPosList'):
                result['holdPosList'], hold_apy = self._process_positions(
                    item['holdPosList'], 
                    staking_type='hold'
                )
                all_apy.extend(hold_apy)

            # Обработка фиксированного стейкинга (LOCK_POS)
            if item.get('lockPosList'):
                result['lockPosList'], lock_apy = self._process_positions(
                    item['lockPosList'], 
                    staking_type='lock'
                )
                all_apy.extend(lock_apy)

        # Формируем строку cost с округлением
        if all_apy:
            min_apy = round(min(all_apy) * 100, 2)  # Округляем до сотых
            max_apy = round(max(all_apy) * 100, 2)  # Округляем до сотых
            result['cost'] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"
            
        return result

    def _process_positions(self, positions: list, staking_type: str) -> tuple:
        processed = []
        apy_values = []
        
        for pos in positions:
            apy = self._get_apy(pos, staking_type)
            if apy <= 0:  # Игнорируем нулевые ставки
                continue
                
            processed.append({
                'days': pos.get('minLockDays', 0) if staking_type == 'lock' else 0,
                'apy': round(apy * 100, 2),  
                'min_amount': 0,  
                'max_amount': float(pos.get('limitMax', 0))  
                                        })
            apy_values.append(apy)
            
        return processed, apy_values

    def _get_apy(self, pos: dict, staking_type: str) -> float:
        if staking_type == 'hold':

            if float(pos.get('profitRate', 0)) > 0:
                return float(pos.get('profitRate'))

            step_rate_list = pos.get('stepRateList', [])
            if step_rate_list:
                return max(float(step.get('stepRate', 0)) for step in step_rate_list)
            return 0
        else:

            return float(pos.get('profitRate', 0))