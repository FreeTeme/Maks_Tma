from .base_parser import BaseParser
import requests
import logging

class BinanceParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        """
        Получает информацию о стейкинге для указанной монеты.
        Возвращает данные в формате, аналогичном Gate.io.
        """
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            # Запрос к API Binance
            response = self._make_api_request()
            if not response.ok:
                self.logger.error(f"Binance API error: {response.status_code}")
                return {}

            # Обрабатываем данные, начиная с ключа 'data'
            data = response.json()
            self.logger.debug(f"Raw API response: {data}")

            if "data" not in data or "list" not in data["data"]:
                self.logger.error("Key 'data' or 'list' not found in API response")
                return {}

            return self.parse_response(data["data"]["list"], normalized_coin)
        except Exception as e:
            self.logger.error(f"Binance parser error: {str(e)}")
            return {}

    def _make_api_request(self):
        cookies = {
            'aws-waf-token': '09d93944-9364-4b26-90f3-2befec788406:CgoAYSpWcdE1AAAA:/LHjv2tdCeCOi/qtBpgB/caTpoxs/dhTXCkGnDvoQCqmbRixJBHaAbyUl6AyTz25FOvS9rf+bMezl4MnPr5R4KvY5QqAcK6pOdH433Km2G4aRlGVeVdEUNMlTgG/mkXeSbXlT3//Y3DINq93tPeMvDHw4TruIR45LIIjoYb4zfzRe6r4jaNlPOc9mMIoGJwOjP4=',
            'theme': 'dark',
            'bnc-uuid': '2972d15b-7c8f-44a5-9cda-659d16fa6a1b',
            'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%22195c2f55cc434c-007ca9f6dea3a4b4-26011d51-1049088-195c2f55cc5539%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk1YzJmNTVjYzQzNGMtMDA3Y2E5ZjZkZWEzYTRiNC0yNjAxMWQ1MS0xMDQ5MDg4LTE5NWMyZjU1Y2M1NTM5In0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%7D',
            'sajssdk_2015_cross_new_user': '1',
            '_gid': 'GA1.2.1647196951.1742732623',
            'BNC_FV_KEY': '33e0a3ec130aa58682ff0d554f055e323ad4ad23',
            'BNC_FV_KEY_T': '101-5jrrjXXOZPETkowFuMBygEUDnc4yLgQlgcafEHvIu6sQqO0B9n2ymKwMuF%2BN6kM1g3xGEQtkQjCLGxf7Ev15ag%3D%3D-zrn4EqVju0%2Fi1PdvgCe80g%3D%3D-65',
            'BNC_FV_KEY_EXPIRE': '1742754223909',
            '_ga': 'GA1.1.766309792.1742732623',
            '_gat': '1',
            'OptanonConsent': 'isGpcEnabled=0&datestamp=Sun+Mar+23+2025+15%3A25%3A20+GMT%2B0300+(%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C+%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%BE%D0%B5+%D0%B2%D1%80%D0%B5%D0%BC%D1%8F)&version=202411.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=12a12b92-e447-4266-a23c-b717e79cdfdc&interactionCount=1&isAnonUser=1&landingPath=https%3A%2F%2Fwww.binance.com%2Fen%2Fearn&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1',
            '_ga_3WP50LGEEC': 'GS1.1.1742732624.1.1.1742732723.57.0.0',
        }

        headers = {
            'accept': '*/*',
            'accept-language': 'ru-RU,ru;q=0.9,en-DE;q=0.8,en;q=0.7,en-US;q=0.6',
            'bnc-currency': 'USD',
            'bnc-location': '',
            'bnc-time-zone': 'Europe/Minsk',
            'bnc-uuid': '2972d15b-7c8f-44a5-9cda-659d16fa6a1b',
            'clienttype': 'web',
            'content-type': 'application/json',
            'csrftoken': 'd41d8cd98f00b204e9800998ecf8427e',
            'device-info': 'eyJzY3JlZW5fcmVzb2x1dGlvbiI6Ijc2OCwxMzY2IiwiYXZhaWxhYmxlX3NjcmVlbl9yZXNvbHV0aW9uIjoiNzI4LDEzNjYiLCJzeXN0ZW1fdmVyc2lvbiI6IldpbmRvd3MgMTAiLCJicmFuZF9tb2RlbCI6InVua25vd24iLCJzeXN0ZW1fbGFuZyI6InJ1LVJVIiwidGltZXpvbmUiOiJHTVQrMDM6MDAiLCJ0aW1lem9uZU9mZnNldCI6LTE4MCwidXNlcl9hZ2VudCI6Ik1vemlsbGEvNS4wIChXaW5kb3dzIE5UIDEwLjA7IFdpbjY0OyB4NjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIENocm9tZS8xMzQuMC4wLjAgU2FmYXJpLzUzNy4zNiIsImxpc3RfcGx1Z2luIjoiUERGIFZpZXdlcixDaHJvbWUgUERGIFZpZXdlcixDaHJvbWl1bSBQREYgVmlld2VyLE1pY3Jvc29mdCBFZGdlIFBERiBWaWV3ZXIsV2ViS2l0IGJ1aWx0LWluIFBERiIsImNhbnZhc19jb2RlIjoiZTU0Y2QwMzMiLCJ3ZWJnbF92ZW5kb3IiOiJHb29nbGUgSW5jLiAoSW50ZWwpIiwid2ViZ2xfcmVuZGVyZXIiOiJBTkdMRSAoSW50ZWwsIEludGVsKFIpIEhEIEdyYXBoaWNzIDU1MDAgKDB4MDAwMDE2MTYpIERpcmVjdDNEMTEgdnNfNV8wIHBzXzVfMCwgRDNEMTEpIiwiYXVkaW8iOiIxMjQuMDQzNDc1Mjc1MTYwNzQiLCJwbGF0Zm9ybSI6IldpbjMyIiwid2ViX3RpbWV6b25lIjoiRXVyb3BlL01pbnNrIiwiZGV2aWNlX25hbWUiOiJDaHJvbWUgVjEzNC4wLjAuMCAoV2luZG93cykiLCJmaW5nZXJwcmludCI6ImI0M2IwMmUwYzk4MTkzNWI0MGMwNTliODA5OTY5NTRmIiwiZGV2aWNlX2lkIjoiIiwicmVsYXRlZF9kZXZpY2VfaWRzIjoiIn0=',
            'fvideo-id': '33e0a3ec130aa58682ff0d554f055e323ad4ad23',
            'fvideo-token': '6wY9Amx/LAkAXPck6AmLlIjpkYDhbnAVWbOoVb8x2xcIXOCC1gM9Mqic/6UDPfOxqQWU4t25F7ILdH0JmsDppMrZydgG6Y7Cn3GRcIZzE+k8kGIHWN7ycly5r1UAJ/fpF1m9FTOU9mp5S2WYFAOjF1pzSiWvpKe1cifenRVw0yNEBmKjsIPVdD1qVDTlui5Mw=58',
            'if-none-match': 'W/"036f132fab1fa2aee54542a7dfb4f8ead"',
            'lang': 'en',
            'priority': 'u=1, i',
            'referer': 'https://www.binance.com/en/earn',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'x-passthrough-token': '',
            'x-trace-id': 'afcf5b93-aade-48fa-a544-53667b5ea86b',
            'x-ui-request-trace': 'afcf5b93-aade-48fa-a544-53667b5ea86b',
            # 'cookie': 'aws-waf-token=09d93944-9364-4b26-90f3-2befec788406:CgoAYSpWcdE1AAAA:/LHjv2tdCeCOi/qtBpgB/caTpoxs/dhTXCkGnDvoQCqmbRixJBHaAbyUl6AyTz25FOvS9rf+bMezl4MnPr5R4KvY5QqAcK6pOdH433Km2G4aRlGVeVdEUNMlTgG/mkXeSbXlT3//Y3DINq93tPeMvDHw4TruIR45LIIjoYb4zfzRe6r4jaNlPOc9mMIoGJwOjP4=; theme=dark; bnc-uuid=2972d15b-7c8f-44a5-9cda-659d16fa6a1b; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22195c2f55cc434c-007ca9f6dea3a4b4-26011d51-1049088-195c2f55cc5539%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk1YzJmNTVjYzQzNGMtMDA3Y2E5ZjZkZWEzYTRiNC0yNjAxMWQ1MS0xMDQ5MDg4LTE5NWMyZjU1Y2M1NTM5In0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%7D; sajssdk_2015_cross_new_user=1; _gid=GA1.2.1647196951.1742732623; BNC_FV_KEY=33e0a3ec130aa58682ff0d554f055e323ad4ad23; BNC_FV_KEY_T=101-5jrrjXXOZPETkowFuMBygEUDnc4yLgQlgcafEHvIu6sQqO0B9n2ymKwMuF%2BN6kM1g3xGEQtkQjCLGxf7Ev15ag%3D%3D-zrn4EqVju0%2Fi1PdvgCe80g%3D%3D-65; BNC_FV_KEY_EXPIRE=1742754223909; _ga=GA1.1.766309792.1742732623; _gat=1; OptanonConsent=isGpcEnabled=0&datestamp=Sun+Mar+23+2025+15%3A25%3A20+GMT%2B0300+(%D0%9C%D0%BE%D1%81%D0%BA%D0%B2%D0%B0%2C+%D1%81%D1%82%D0%B0%D0%BD%D0%B4%D0%B0%D1%80%D1%82%D0%BD%D0%BE%D0%B5+%D0%B2%D1%80%D0%B5%D0%BC%D1%8F)&version=202411.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=12a12b92-e447-4266-a23c-b717e79cdfdc&interactionCount=1&isAnonUser=1&landingPath=https%3A%2F%2Fwww.binance.com%2Fen%2Fearn&groups=C0001%3A1%2CC0003%3A1%2CC0004%3A1%2CC0002%3A1; _ga_3WP50LGEEC=GS1.1.1742732624.1.1.1742732723.57.0.0',
        }

        params = {
            'pageSize': '100',
        }

        response = requests.get(
            'https://www.binance.com/bapi/earn/v1/friendly/finance-earn/homepage/overview',
            params=params,
            cookies=cookies,
            headers=headers,
        )
        self.logger.debug(f"API request to Binance, status code: {response.status_code}")
        return response

    def parse_response(self, data: list, coin: str) -> dict:
        """
        Парсит данные от Binance и возвращает их в формате, аналогичном Gate.io.
        """
        result = {
            "exchange": "Binance",
            "coin": coin,
            "holdPosList": [],  # Гибкий стейкинг
            "lockPosList": [],  # Фиксированный стейкинг
            "cost": "0%"
        }

        all_apy = []

        # Обрабатываем данные о монетах
        for item in data:
            if item.get("asset") != coin:
                continue

            # Обрабатываем продукты для текущей монеты
            for product in item.get("productSummary", []):
                max_apr = float(product.get("maxApr", 0))
                min_apr = float(product.get("minApr", 0))
                duration = product.get("duration", [])

                # Гибкий стейкинг (FLEXIBLE)
                if "FLEXIBLE" in duration:
                    result["holdPosList"].append({
                        "days": 0,  # Гибкий стейкинг не имеет срока
                        "apy": round(max_apr * 100, 2),  # Преобразуем APR в APY
                        "min_amount": 0,  # Минимальная сумма не указана
                        "max_amount": float("inf")  # Без ограничений
                    })
                    all_apy.append(max_apr * 100)

                # Фиксированный стейкинг (FIXED)
                if "FIXED" in duration:
                    # Устанавливаем значение по умолчанию для projectDuration, если оно отсутствует
                    project_duration = product.get("projectDuration")
                    if project_duration is None:
                        project_duration = 0  # Значение по умолчанию
                    else:
                        project_duration = int(project_duration)

                    result["lockPosList"].append({
                        "days": project_duration,  # Срок блокировки
                        "apy": round(max_apr * 100, 2),  # Преобразуем APR в APY
                        "min_amount": 0,  # Минимальная сумма не указана
                        "max_amount": float("inf")  # Без ограничений
                    })
                    all_apy.append(max_apr * 100)

        # Формируем строку cost
        if all_apy:
            min_apy = round(min(all_apy), 2)
            max_apy = round(max(all_apy), 2)
            result["cost"] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"

        return result