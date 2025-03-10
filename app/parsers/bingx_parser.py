from .base_parser import BaseParser
import requests
import json


class BingXParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin)
            
            # cookies = {
            #     'cf_clearance': '.4uIxxfAsj6N8EkRfDl5mRi.dUV7M3oX9ph8A9SmoQ0-1741518259-1.2.1.1-ZW2KqvKleDjopWqMAVJWhHJIY_iexHN8P_Uf5cQXq0BApu4Hh3YHoN3Ree8Q07dc7HcLigeO41BdohtuNAKXTdouOM2u.8Pu3kheXtdhWLU.pNQPXXb3Hw8SFSXa_vzSPmJU3e9EJsnrkLffc2v4MvjmYJBZFrTkGOe1selPCAbibxaMa.1pPMF9S5izemUK5OiBsW7ssHJ1WUO0nHNK4mbDKuV1pepwH7_VQI2ag70yW2usl_.Nq2GaCYFW4M.iRcdKuFJae_xtoYf1g_0JUgFX1RPgULtdif.7HSX5HcW4Yeni_1jwDBUTU7oiSRjWev1hPDiq8DZoYHlzJWu_SEPHcQ5ApsDqFBu_nDtcVGRptn5O_NzZHSJ5W4haKIsRFA5XRfcNhTOC4fUh09_X1KXIafefpHjQhNKNfwa.340',
            #     'sajssdk_2015_cross_new_user': '1',
            #     'WEBGRAY': 'stable',
            #     'X-GRAY': 'xgray-claim&xgray-travel-rule-20250-03-07',
            #     'X_GRAY_TEMP_UUID': 'd8961e1d-db56-4478-988a-25d05db6ffcb',
            #     'X_GRAY_TMP': '1741399945038',
            #     '_fbp': 'fb.1.1741518264648.2012457283',
            #     '_uetsid': '41ad8890fcd611ef9773cfbe8b7ed036',
            #     '_uetvid': '41ad9c10fcd611efa90b3dad97f1fd8c',
            #     'smidV2': '20250309140424f12bba0689cf1d8d067b3a0e3ec67d4b002a17676dfaea0b0',
            #     '.thumbcache_c294bfec3668b22bff5f6aa9bb528f6a': 'Fn2mBVFQw142UPzyhQDfR58rg1C3PGSxedaLwZNKVQCpFLipxvgrImurKACAjAVEk9w5tB1fLcgLZviXOopPFQ%3D%3D',
            #     '_gid': 'GA1.2.180794502.1741518294',
            #     'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%221957a93c849185-09eb8fe866d247-26011a51-1049088-1957a93c84a696%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E8%87%AA%E7%84%B6%E6%90%9C%E7%B4%A2%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%2C%22%24latest_utm_source%22%3A%22af%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk1N2E5M2M4NDkxODUtMDllYjhmZTg2NmQyNDctMjYwMTFhNTEtMTA0OTA4OC0xOTU3YTkzYzg0YTY5NiJ9%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%2C%22%24device_id%22%3A%221957a93c849185-09eb8fe866d247-26011a51-1049088-1957a93c84a696%22%7D',
            #     '__cf_bm': '9YDwRz4pNdf.sBMj8Zv3rnIc5_.zpBoBr63Vg7Funts-1741523187-1.0.1.1-rpf0IIn87Q60zHFjuOKoC0p8rGnpexpUIL_088uXS2yTizjJbDna94v2WN.8dE4gJ.tQ315WluU_FpUATIVFQF4u0yEZxKttvqFvwjCV8k0',
            #     '_cfuvid': 'nVDwzirkUxogNQIc09ABxpgEJOcBaIWj8nCs75X1VgQ-1741523187531-0.0.1.1-604800000',
            #     '_gat_UA-46608064-1': '1',
            #     '_ga_YHWW24NNH9': 'GS1.1.1741523192.2.1.1741523209.43.0.0',
            #     '_ga': 'GA1.1.183112140.1741518294',
            #     'AWSALB': 'T4Gmb0iS+4KC/3wtEY0VVJIMYzvDpSx2KM1LFsZr3hlReuAe72oITXlYx9xfoYH/Ed1ykJEr8agk+Ua/1DSkjnqxX19D2P3clPiu4J0uNp5XiwqVaFYpiYt0IVWf',
            #     'AWSALBCORS': 'T4Gmb0iS+4KC/3wtEY0VVJIMYzvDpSx2KM1LFsZr3hlReuAe72oITXlYx9xfoYH/Ed1ykJEr8agk+Ua/1DSkjnqxX19D2P3clPiu4J0uNp5XiwqVaFYpiYt0IVWf',
            # }

            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
                'app_version': '5.1.84',
                'appid': '30004',
                'appsiteid': '0',
                'channel': 'official',
                'device_brand': 'Windows 10_Chrome_133.0.0.0',
                'device_id': '8437fcf6918f469cb12ac51b91224f22',
                'lang': 'ru-RU',
                'mainappid': '10009',
                'origin': 'https://bingx.com',
                'platformid': '30',
                'priority': 'u=1, i',
                'referer': 'https://bingx.com/',
                'reg_channel': 'official',
                'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'sec-fetch-storage-access': 'active',
                'sign': '580BAE4FB2D6C28BD3C62847B6F992BC56EA0FF21488225E4E55627785C58709',
                'timestamp': '1741529496790',
                'timezone': '3',
                'traceid': '3498fd5c19044b87b1cd7d9d0a2e12a0',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'x-requested-with': 'XMLHttpRequest',
            }

            params = {
                'searchType': '',
                'dataType': '',
                'assetName': '',
                'orderBy': '',
            }

            response = requests.get(
                'https://api-app.we-api.com/api/wealth-sales-trading/v1/product/list',
                params=params,
                # cookies=cookies,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return self.parse_response(data, normalized_coin)
            
            self.logger.error(f"BingX API error: {response.status_code}")
            return None
            
        except Exception as e:
            self.logger.error(f"BingX parser error: {str(e)}")
            return None

    def parse_response(self, data: dict, coin: str) -> tuple:
        for item in data.get('data', []):
            if item.get('assetName') == coin:
                min_apy = float(item.get('minApy', 0))
                max_apy = float(item.get('maxApy', 0))
                cost = f"{min_apy} - {max_apy}"
                return ('BingX', cost)
        return None
