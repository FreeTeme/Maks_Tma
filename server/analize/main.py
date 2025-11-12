# strategy_tester.py
from flask import Blueprint, request, jsonify
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

strategy_bp = Blueprint('strategy', __name__, url_prefix='/api/strategy')

class TradingStrategyTester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:5010"
    
    def fetch_ohlcv_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Загрузка данных через локальное API"""
        try:
            response = requests.get(
                f'{self.base_url}/api/pattern/ohlcv',
                params={
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'from': start_date,
                    'to': end_date
                },
                timeout=30
            )
            
            print(f"📡 Запрос данных: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Ответ API: {data.get('success')}, свечей: {len(data.get('candles', []))}")
                
                if data.get('success') and data.get('candles'):
                    candles = data['candles']
                    df_data = []
                    for candle in candles:
                        df_data.append({
                            'date': pd.to_datetime(candle['open_time']),
                            'open': candle['open_price'],
                            'high': candle['high'],
                            'low': candle['low'],
                            'close': candle['close_price'],
                            'volume': candle['volume']
                        })
                    
                    df = pd.DataFrame(df_data).sort_values('date').reset_index(drop=True)
                    print(f"✅ Загружено {len(df)} свечей")
                    return df
            
            print("❌ Не удалось загрузить данные")
            return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ Ошибка загрузки данных: {e}")
            return pd.DataFrame()
    
    def calculate_sma(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        """Расчет простой скользящей средней"""
        return data['close'].rolling(window=period).mean()
    
    def simulate_trade(self, entry_price: float, trade_type: str, 
                      entry_index: int, data: pd.DataFrame, 
                      tp_percent: float = 4, sl_percent: float = 2,
                      max_candles: int = 4) -> Dict:
        """
        Симуляция одной сделки
        """
        entry_idx = entry_index
        
        # Анализируем следующие max_candles свечей
        for j in range(1, max_candles + 1):
            if entry_idx + j >= len(data):
                break
                
            current_price = data.iloc[entry_idx + j]['close']
            
            if trade_type == 'BUY':
                pnl_pct = (current_price - entry_price) / entry_price * 100
                
                if pnl_pct >= tp_percent:  # Тейк-профит сработал
                    return {
                        'status': 'TP', 
                        'candles_held': j, 
                        'pnl_pct': tp_percent,
                        'exit_price': entry_price * (1 + tp_percent/100),
                        'exit_type': 'take_profit'
                    }
                elif pnl_pct <= -sl_percent:  # Стоп-лосс сработал
                    return {
                        'status': 'SL', 
                        'candles_held': j, 
                        'pnl_pct': -sl_percent,
                        'exit_price': entry_price * (1 - sl_percent/100),
                        'exit_type': 'stop_loss'
                    }
                    
            else:  # SELL (шорт)
                pnl_pct = (entry_price - current_price) / entry_price * 100
                
                if pnl_pct >= tp_percent:  # Тейк-профит сработал
                    return {
                        'status': 'TP', 
                        'candles_held': j, 
                        'pnl_pct': tp_percent,
                        'exit_price': entry_price * (1 - tp_percent/100),
                        'exit_type': 'take_profit'
                    }
                elif pnl_pct <= -sl_percent:  # Стоп-лосс сработал
                    return {
                        'status': 'SL', 
                        'candles_held': j, 
                        'pnl_pct': -sl_percent,
                        'exit_price': entry_price * (1 + sl_percent/100),
                        'exit_type': 'stop_loss'
                    }
        
        # Если не сработали TP/SL за max_candles свечей
        final_price = data.iloc[entry_idx + max_candles]['close']
        if trade_type == 'BUY':
            pnl_pct = (final_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - final_price) / entry_price * 100
            
        return {
            'status': 'TIME_EXIT', 
            'candles_held': max_candles, 
            'pnl_pct': pnl_pct,
            'exit_price': final_price,
            'exit_type': 'time_exit'
        }
    
    def find_trading_opportunities(self, data: pd.DataFrame, sma_period: int = 20) -> List[Dict]:
        """Поиск торговых возможностей по стратегии SMA(20)"""
        opportunities = []
        
        # Расчет SMA
        data['SMA_20'] = self.calculate_sma(data, sma_period)
        
        # Ищем точки входа начиная с 20-й свечи
        for i in range(sma_period, len(data) - 4):
            current_close = data.iloc[i]['close']
            sma_20 = data.iloc[i]['SMA_20']
            
            if pd.isna(sma_20):
                continue
            
            # Предыдущая цена закрытия
            prev_close = data.iloc[i-1]['close']
            
            # Проверяем пересечение снизу вверх (BUY)
            if prev_close <= sma_20 and current_close > sma_20:
                opportunities.append({
                    'index': i,
                    'timestamp': data.iloc[i]['date'],
                    'type': 'BUY',
                    'entry_price': current_close,
                    'sma_value': sma_20,
                    'price_vs_sma': ((current_close - sma_20) / sma_20 * 100)
                })
            # Проверяем пересечение сверху вниз (SELL)
            elif prev_close >= sma_20 and current_close < sma_20:
                opportunities.append({
                    'index': i,
                    'timestamp': data.iloc[i]['date'],
                    'type': 'SELL',
                    'entry_price': current_close,
                    'sma_value': sma_20,
                    'price_vs_sma': ((current_close - sma_20) / sma_20 * 100)
                })
                
        return opportunities
    
    def run_backtest(self, data: pd.DataFrame, initial_deposit: float = 100000, 
                    tp_percent: float = 4, sl_percent: float = 2) -> Dict:
        """Запуск полного бэктеста стратегии"""
        if len(data) < 50:
            return {'error': 'Недостаточно данных для тестирования'}
        
        opportunities = self.find_trading_opportunities(data)
        trades = []
        deposit = initial_deposit
        equity_curve = [deposit]
        in_trade = False
        current_trade_end = 0
        
        print(f"Найдено торговых возможностей: {len(opportunities)}")
        
        for i, opp in enumerate(opportunities):
            # Пропускаем если уже в сделке
            if in_trade and opp['index'] < current_trade_end:
                continue
            
            trade_result = self.simulate_trade(
                opp['entry_price'], 
                opp['type'], 
                opp['index'], 
                data, 
                tp_percent, 
                sl_percent
            )
            
            # Расчет P&L в деньгах
            pnl_amount = (deposit * trade_result['pnl_pct']) / 100
            deposit += pnl_amount
            equity_curve.append(deposit)
            
            # Устанавливаем конец текущей сделки
            in_trade = False
            current_trade_end = opp['index'] + trade_result['candles_held']
            
            trade_info = {
                'trade_id': i + 1,
                'timestamp': opp['timestamp'],
                'type': opp['type'],
                'entry_price': opp['entry_price'],
                'exit_price': trade_result['exit_price'],
                'pnl_pct': trade_result['pnl_pct'],
                'pnl_amount': pnl_amount,
                'status': trade_result['status'],
                'candles_held': trade_result['candles_held'],
                'exit_type': trade_result['exit_type'],
                'deposit_after': deposit,
                'sma_value': opp['sma_value'],
                'price_vs_sma': opp['price_vs_sma']
            }
            
            trades.append(trade_info)
        
        # Расчет статистики
        stats = self.calculate_statistics(trades, equity_curve, initial_deposit, data)
        
        return {
            'trades': trades,
            'statistics': stats,
            'equity_curve': equity_curve,
            'opportunities_count': len(opportunities),
            'initial_deposit': initial_deposit,
            'final_deposit': deposit
        }
    
    def calculate_statistics(self, trades: List[Dict], equity_curve: List[float], 
                           initial_deposit: float, data: pd.DataFrame) -> Dict:
        """Расчет статистики по результатам тестирования"""
        if not trades:
            return {
                'total_trades': 0,
                'profitable_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_return_per_trade': 0,
                'total_return_percent': 0,
                'total_profit': 0,
                'max_drawdown': 0,
                'buy_hold_return': 0,
                'buy_hold_value': initial_deposit,
                'max_buy_hold_drawdown': 0,
                'comparison_vs_bh': 0,
                'buy_trades_count': 0,
                'sell_trades_count': 0,
                'buy_win_rate': 0,
                'sell_win_rate': 0,
                'avg_holding_time_candles': 0,
                'initial_deposit': initial_deposit,
                'final_deposit': initial_deposit
            }
        
        df_trades = pd.DataFrame(trades)
        
        # Базовая статистика
        total_trades = len(trades)
        profitable_trades = len(df_trades[df_trades['pnl_pct'] > 0])
        losing_trades = len(df_trades[df_trades['pnl_pct'] <= 0])
        win_rate = profitable_trades / total_trades * 100
        
        # P&L статистика
        avg_return = df_trades['pnl_pct'].mean()
        total_return_pct = (equity_curve[-1] - initial_deposit) / initial_deposit * 100
        total_profit = equity_curve[-1] - initial_deposit
        
        # Максимальная просадка
        rolling_max = pd.Series(equity_curve).expanding().max()
        drawdowns = (pd.Series(equity_curve) - rolling_max) / rolling_max * 100
        max_drawdown = drawdowns.min() if not drawdowns.empty else 0
        
        # Сравнение с бенчмарком (Buy & Hold)
        first_price = data.iloc[20]['close'] if len(data) > 20 else data.iloc[0]['close']
        last_price = data.iloc[-1]['close']
        buy_hold_return = (last_price - first_price) / first_price * 100
        buy_hold_value = initial_deposit * (1 + buy_hold_return/100)
        
        # Максимальная просадка для бенчмарка
        data['rolling_max'] = data['close'].expanding().max()
        bh_drawdowns = (data['close'] - data['rolling_max']) / data['rolling_max'] * 100
        max_bh_drawdown = bh_drawdowns.min() if not bh_drawdowns.empty else 0
        
        # Статистика по типам сделок
        buy_trades = df_trades[df_trades['type'] == 'BUY']
        sell_trades = df_trades[df_trades['type'] == 'SELL']
        
        buy_win_rate = len(buy_trades[buy_trades['pnl_pct'] > 0]) / len(buy_trades) * 100 if len(buy_trades) > 0 else 0
        sell_win_rate = len(sell_trades[sell_trades['pnl_pct'] > 0]) / len(sell_trades) * 100 if len(sell_trades) > 0 else 0
        
        # Статистика по времени удержания
        avg_holding_time = df_trades['candles_held'].mean()
        
        return {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'avg_return_per_trade': round(avg_return, 2),
            'total_return_percent': round(total_return_pct, 2),
            'total_profit': round(total_profit, 2),
            'max_drawdown': round(max_drawdown, 2),
            'buy_hold_return': round(buy_hold_return, 2),
            'buy_hold_value': round(buy_hold_value, 2),
            'max_buy_hold_drawdown': round(max_bh_drawdown, 2),
            'comparison_vs_bh': round(total_return_pct - buy_hold_return, 2),
            'buy_trades_count': len(buy_trades),
            'sell_trades_count': len(sell_trades),
            'buy_win_rate': round(buy_win_rate, 2),
            'sell_win_rate': round(sell_win_rate, 2),
            'avg_holding_time_candles': round(avg_holding_time, 1),
            'initial_deposit': initial_deposit,
            'final_deposit': round(equity_curve[-1], 2)
        }

# Глобальный экземпляр тестера
tester = TradingStrategyTester()

@strategy_bp.route('/test', methods=['POST'])
def test_strategy():
    """Основной эндпоинт для тестирования стратегии"""
    try:
        data = request.get_json()
        print(f"📨 Получен запрос на тестирование: {data}")
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        symbol = data.get('symbol', 'BTCUSDT')
        timeframe = data.get('timeframe', '1h')
        start_date = data.get('start_date', '2022-02-28')
        end_date = data.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        initial_deposit = data.get('initial_deposit', 100000)
        tp_percent = data.get('tp_percent', 4)
        sl_percent = data.get('sl_percent', 2)
        max_candles = data.get('max_candles', 4)
        
        print(f"🔧 Параметры теста: {symbol} {timeframe} {start_date} - {end_date}")
        print(f"💰 Депозит: ${initial_deposit}, TP: {tp_percent}%, SL: {sl_percent}%")
        
        # Загружаем данные
        ohlcv_data = tester.fetch_ohlcv_data(symbol, timeframe, start_date, end_date)
        
        if ohlcv_data.empty:
            return jsonify({
                'success': False, 
                'message': 'Не удалось загрузить данные для тестирования'
            }), 400
        
        print(f"✅ Загружено {len(ohlcv_data)} свечей для тестирования")
        
        # Запускаем тестирование
        result = tester.run_backtest(ohlcv_data, initial_deposit, tp_percent, sl_percent)
        
        if 'error' in result:
            return jsonify({'success': False, 'message': result['error']}), 400
        
        result['success'] = True
        result['symbol'] = symbol
        result['timeframe'] = timeframe
        result['test_period'] = {
            'start': start_date,
            'end': end_date,
            'total_candles': len(ohlcv_data)
        }
        
        print(f"🎯 Тестирование завершено: {result['statistics']['total_trades']} сделок")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Ошибка тестирования стратегии: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False, 
            'message': f'Ошибка тестирования: {str(e)}'
        }), 500

@strategy_bp.route('/opportunities', methods=['GET'])
def get_trading_opportunities():
    """Получение торговых возможностей для визуализации"""
    try:
        symbol = request.args.get('symbol', 'BTCUSDT')
        timeframe = request.args.get('timeframe', '1h')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # Загружаем данные
        ohlcv_data = tester.fetch_ohlcv_data(symbol, timeframe, start_date, end_date)
        
        if ohlcv_data.empty:
            return jsonify({'success': False, 'message': 'Не удалось загрузить данные'}), 400
        
        # Находим торговые возможности
        opportunities = tester.find_trading_opportunities(ohlcv_data)
        
        # Форматируем для фронтенда
        formatted_opps = []
        for opp in opportunities:
            formatted_opps.append({
                'timestamp': opp['timestamp'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                'type': opp['type'],
                'entry_price': opp['entry_price'],
                'sma_value': opp['sma_value'],
                'price_vs_sma': round(opp['price_vs_sma'], 2),
                'index': opp['index']
            })
        
        return jsonify({
            'success': True,
            'opportunities': formatted_opps,
            'total_opportunities': len(formatted_opps),
            'symbol': symbol,
            'timeframe': timeframe
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Ошибка получения возможностей: {str(e)}'
        }), 500

@strategy_bp.route('/trade_details', methods=['GET'])
def get_trade_details():
    """Получение детальной информации о конкретной сделке"""
    try:
        symbol = request.args.get('symbol', 'BTCUSDT')
        timeframe = request.args.get('timeframe', '1h')
        entry_index = int(request.args.get('entry_index', 0))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        # Загружаем данные
        ohlcv_data = tester.fetch_ohlcv_data(symbol, timeframe, start_date, end_date)
        
        if ohlcv_data.empty or entry_index >= len(ohlcv_data):
            return jsonify({'success': False, 'message': 'Неверные параметры'}), 400
        
        # Определяем тип сделки по SMA
        sma_20 = tester.calculate_sma(ohlcv_data, 20)
        current_close = ohlcv_data.iloc[entry_index]['close']
        current_sma = sma_20.iloc[entry_index] if entry_index < len(sma_20) else 0
        
        if pd.isna(current_sma):
            return jsonify({'success': False, 'message': 'Недостаточно данных для SMA'}), 400
        
        # Предыдущая цена для определения направления пересечения
        prev_close = ohlcv_data.iloc[entry_index-1]['close'] if entry_index > 0 else current_close
        
        if prev_close <= current_sma and current_close > current_sma:
            trade_type = 'BUY'
        elif prev_close >= current_sma and current_close < current_sma:
            trade_type = 'SELL'
        else:
            return jsonify({'success': False, 'message': 'Не точка входа по стратегии'}), 400
        
        # Симулируем сделку
        trade_result = tester.simulate_trade(
            current_close, 
            trade_type, 
            entry_index, 
            ohlcv_data
        )
        
        return jsonify({
            'success': True,
            'trade_details': {
                'entry_index': entry_index,
                'entry_timestamp': ohlcv_data.iloc[entry_index]['date'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                'entry_price': current_close,
                'trade_type': trade_type,
                'sma_value': current_sma,
                'exit_timestamp': ohlcv_data.iloc[entry_index + trade_result['candles_held']]['date'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                'exit_price': trade_result['exit_price'],
                'pnl_percent': round(trade_result['pnl_pct'], 2),
                'candles_held': trade_result['candles_held'],
                'status': trade_result['status'],
                'exit_type': trade_result['exit_type']
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Ошибка получения деталей сделки: {str(e)}'
        }), 500

@strategy_bp.route('/status', methods=['GET'])
def status_check():
    """Проверка работы блюпринта"""
    return jsonify({
        'success': True,
        'message': 'Strategy blueprint is working!',
        'endpoints': {
            'POST /api/strategy/test': 'Run strategy test',
            'GET /api/strategy/opportunities': 'Get trading opportunities', 
            'GET /api/strategy/trade_details': 'Get trade details',
            'GET /api/strategy/status': 'Check status'
        }
    })