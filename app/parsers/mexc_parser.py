from .base_parser import BaseParser
import requests
import json

class MexcParser(BaseParser):
    def get_staking_info(self, coin: str) -> dict:
        try:
            normalized_coin = self.normalize_coin_name(coin)
            response = requests.get(
                'https://www.mexc.com/api/operateactivity/staking',
                cookies=self._get_cookies(),
                headers=self._get_headers(),
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
                'max_amount': float(pos.get('limitMax', 'inf'))  
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