from .base_parser import BaseParser
import requests
import json

class MexcParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin)
            
            # Минимальные заголовки
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'en-US,en;q=0.9',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
                'referer': 'https://www.mexc.com/staking',
                'origin': 'https://www.mexc.com',
            }

            response = requests.get(
                'https://www.mexc.com/api/operateactivity/staking',
                headers=headers,
                timeout=15
            )

            if response.status_code == 403:
                self.logger.error("Mexc API: Access forbidden. Trying alternative endpoint...")
                return self._try_alternative_method(coin)
                
            if not response.ok:
                self.logger.error(f"Mexc API error: {response.status_code} - {response.text}")
                return {}

            data = response.json()
            return self.parse_response(data, normalized_coin)
            
        except Exception as e:
            self.logger.error(f"Mexc parser error: {str(e)}")
            return {}

    def _try_alternative_method(self, coin: str) -> dict:
        """Альтернативный метод через публичный API"""
        try:
            # Попробуем получить информацию через другие публичные endpoints
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            # Endpoint для получения списка всех стейкинг продуктов
            response = requests.get(
                'https://www.mexc.com/api/operateactivity/staking/list',
                headers=headers,
                timeout=10
            )
            
            if response.ok:
                return self.parse_response(response.json(), coin)
                
        except Exception as e:
            self.logger.error(f"Mexc alternative method failed: {str(e)}")
            
        return self._get_fallback_data(coin)

    def _get_fallback_data(self, coin: str) -> dict:
        """Возвращает fallback данные если API недоступно"""
        return {
            'exchange': 'Mexc',
            'coin': coin,
            'holdPosList': [],
            'lockPosList': [],
            'cost': '0%',
            'error': 'API temporarily unavailable'
        }

    def parse_response(self, data: dict, coin: str) -> dict:
        # ... существующий код parse_response ...
        result = {
            'exchange': 'Mexc',
            'coin': coin,
            'holdPosList': [],
            'lockPosList': [],
            'cost': '0%'
        }
        
        all_apy = []
        
        for item in data.get('data', []):
            if item.get('currency') != coin:
                continue

            if item.get('holdPosList'):
                result['holdPosList'], hold_apy = self._process_positions(
                    item['holdPosList'], 
                    staking_type='hold'
                )
                all_apy.extend(hold_apy)

            if item.get('lockPosList'):
                result['lockPosList'], lock_apy = self._process_positions(
                    item['lockPosList'], 
                    staking_type='lock'
                )
                all_apy.extend(lock_apy)

        if all_apy:
            min_apy = round(min(all_apy) * 100, 2)
            max_apy = round(max(all_apy) * 100, 2)
            result['cost'] = f"{min_apy}%-{max_apy}%" if min_apy != max_apy else f"{min_apy}%"
            
        return result

    def _process_positions(self, positions: list, staking_type: str) -> tuple:
        # ... существующий код _process_positions ...
        processed = []
        apy_values = []
        
        for pos in positions:
            apy = self._get_apy(pos, staking_type)
            if apy <= 0:
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
        # ... существующий код _get_apy ...
        if staking_type == 'hold':
            if float(pos.get('profitRate', 0)) > 0:
                return float(pos.get('profitRate'))
            step_rate_list = pos.get('stepRateList', [])
            if step_rate_list:
                return max(float(step.get('stepRate', 0)) for step in step_rate_list)
            return 0
        else:
            return float(pos.get('profitRate', 0))