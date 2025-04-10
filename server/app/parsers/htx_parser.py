from .base_parser import BaseParser
import requests
import logging

class HTXParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        """
        Получает информацию о стейкинге для указанной монеты.
        Возвращает данные в формате, аналогичном Gate.io.
        """
        try:
            normalized_coin = self.normalize_coin_name(coin)
            self.logger.debug(f"Normalized coin: {normalized_coin}")

            response = self._make_api_request()
            if not response.ok:
                self.logger.error(f"HTX API error: {response.status_code}")
                return {}

            data = response.json()
            self.logger.debug(f"Raw API response: {data}")

            if "data" not in data:
                self.logger.error("Key 'data' not found in API response")
                return {}

            return self._parse_htx_data(data["data"], normalized_coin)
        except Exception as e:
            self.logger.error(f"HTX parser error: {str(e)}")
            return {}

    def _make_api_request(self):
        cookies = {
            'HB-VULCAN-UUID': 'fef51c8f-faf4-48fe-b866-28eea4b81d2d',
            'WEBK': 'YUPVtb094y0s5c0wo6RZ9ZQMCDnNF/dvFloePrNTkk7GutTQ0VUp5ASdTyVMWIhPQ4T3WfpL/cbco0OECEd8hewOwkD3v3ChuPDvetfgvJiaVDjXMfOcHQAtM2IpYOkCbbHyceMMw3MLM6ICQBaULpUYhtWWV8gGpO8adxpIlntjCs+3YuFcImbgyUSA5uozHpHAhgJlzMgyekroa9Qgbg0b6fBJcP8x5TC823wZ3htIh4oue82hShZggaDZBI3tom9CQLlcBeJlSwI3MAL8zA==',
            '_ga': 'GA1.2.1191811100.1742731856',
            '_gid': 'GA1.2.700255732.1742731856',
            'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%22195c2e9cad51d-0aa11d6d7e597a-26011d51-1049088-195c2e9cad81ea%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E8%87%AA%E7%84%B6%E6%90%9C%E7%B4%A2%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk1YzJlOWNhZDUxZC0wYWExMWQ2ZDdlNTk3YS0yNjAxMWQ1MS0xMDQ5MDg4LTE5NWMyZTljYWQ4MWVhIn0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%2C%22%24device_id%22%3A%22195c2e9cad51d-0aa11d6d7e597a-26011d51-1049088-195c2e9cad81ea%22%7D',
            'local': 'en-us',
            '_ha_session': '1742817771299',
            '_ha_session_id': 'edecd558-659f-3124-a512-99448f77',
            '_gat': '1',
        }

        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US',
            'apptype': '',
            'appversion': '',
            'data-source': '3',
            'hb-country-id': '',
            'huobi-app-client': '',
            'huobi-app-version': '',
            'huobi-app-version-code': '',
            'priority': 'u=1, i',
            'referer': 'https://www.htx.com/en-us/financial/earn/?type=limit',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'vtoken': '008cecc8f2efb4dd2914b568e4a1df5f',
            'webmark': 'v10003',
            # 'cookie': 'HB-VULCAN-UUID=fef51c8f-faf4-48fe-b866-28eea4b81d2d; WEBK=YUPVtb094y0s5c0wo6RZ9ZQMCDnNF/dvFloePrNTkk7GutTQ0VUp5ASdTyVMWIhPQ4T3WfpL/cbco0OECEd8hewOwkD3v3ChuPDvetfgvJiaVDjXMfOcHQAtM2IpYOkCbbHyceMMw3MLM6ICQBaULpUYhtWWV8gGpO8adxpIlntjCs+3YuFcImbgyUSA5uozHpHAhgJlzMgyekroa9Qgbg0b6fBJcP8x5TC823wZ3htIh4oue82hShZggaDZBI3tom9CQLlcBeJlSwI3MAL8zA==; _ga=GA1.2.1191811100.1742731856; _gid=GA1.2.700255732.1742731856; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22195c2e9cad51d-0aa11d6d7e597a-26011d51-1049088-195c2e9cad81ea%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E8%87%AA%E7%84%B6%E6%90%9C%E7%B4%A2%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fwww.google.com%2F%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk1YzJlOWNhZDUxZC0wYWExMWQ2ZDdlNTk3YS0yNjAxMWQ1MS0xMDQ5MDg4LTE5NWMyZTljYWQ4MWVhIn0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%2C%22%24device_id%22%3A%22195c2e9cad51d-0aa11d6d7e597a-26011d51-1049088-195c2e9cad81ea%22%7D; local=en-us; _ha_session=1742817771299; _ha_session_id=edecd558-659f-3124-a512-99448f77; _gat=1',
        }

        params = {
            'r': 'caddyr',
        }

        response = requests.get('https://www.htx.com/-/x/hbg/v4/saving/mining/home', params=params, cookies=cookies, headers=headers)
        return response
        
    def _parse_htx_data(self, data: dict, coin: str) -> dict:
        """Основной метод парсинга данных HTX."""
        result = {
            "exchange": "HTX",
            "coin": coin,
            "holdPosList": [],
            "lockPosList": [],
            "cost": "0%"
        }
        all_apy = []

        # 1. Обработка recommendProject
        if "recommendProject" in data and isinstance(data["recommendProject"], list):
            for project in data["recommendProject"]:
                if project.get("currency") == coin:
                    self._process_project(project, result, all_apy)

        # 2. Обработка projectNewRecommend
        if "projectNewRecommend" in data and isinstance(data["projectNewRecommend"], dict):
            if data["projectNewRecommend"].get("currency") == coin:
                self._process_project(data["projectNewRecommend"], result, all_apy)

        # 3. Обработка projectItem
        if "projectItem" in data and isinstance(data["projectItem"], list):
            for project in data["projectItem"]:
                if project.get("currency") == coin:
                    self._process_project(project, result, all_apy)

        # Формируем строку cost
        if all_apy:
            min_apy = round(min(all_apy), 2)
            max_apy = round(max(all_apy), 2)
            result["cost"] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"

        return result

    def _process_project(self, project: dict, result: dict, all_apy: list):
        """Обрабатывает отдельный проект и добавляет данные в результат."""
        # Обработка основного проекта
        view_year_rate = project.get("viewYearRate")
        term = project.get("term", 0)
        
        if view_year_rate is not None:
            try:
                apy = float(view_year_rate) * 100
                self._add_to_result(term, apy, result, all_apy)
            except (TypeError, ValueError) as e:
                self.logger.warning(f"Failed to parse viewYearRate: {e}")

        # Обработка max/min rates
        max_rate = project.get("maxViewYearRate")
        min_rate = project.get("minViewYearRate")
        
        for rate in [max_rate, min_rate]:
            if rate is not None:
                try:
                    apy = float(rate) * 100
                    self._add_to_result(term, apy, result, all_apy)
                except (TypeError, ValueError) as e:
                    self.logger.warning(f"Failed to parse max/min rate: {e}")

        # Обработка projectList
        if "projectList" in project and isinstance(project["projectList"], list):
            for sub_project in project["projectList"]:
                self._process_project(sub_project, result, all_apy)

    def _add_to_result(self, term: int, apy: float, result: dict, all_apy: list):
        """Добавляет проект в соответствующий список (гибкий/фиксированный)."""
        if term == 0:  # Гибкий стейкинг
            result["holdPosList"].append({
                "days": 0,
                "apy": round(apy, 2),
                "min_amount": 0,
                "max_amount": 0
            })
        else:  # Фиксированный стейкинг
            result["lockPosList"].append({
                "days": int(term) if term else 30,  # По умолчанию 30 дней, если term не указан
                "apy": round(apy, 2),
                "min_amount": 0,
                "max_amount": 0
            })
        all_apy.append(apy)