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
        self.base_url = "https://app.histobit.twc1.net"

    def fetch_ohlcv_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Загрузка OHLCV данных через внешнее API"""
        try:
            response = requests.get(
                f'{self.base_url}/api/pattern/ohlcv',
                params={
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'from': start_date,
                    'to': end_date
                },
                timeout=35
            )

            if response.status_code != 200:
                print(f"Ошибка API: {response.status_code} — {response.text[:180]}")
                return pd.DataFrame()

            data = response.json()
            if not data.get('success') or not data.get('candles'):
                print("API вернул успех=false или пустые свечи")
                return pd.DataFrame()

            candles = data['candles']
            df_data = [{
                'date': pd.to_datetime(c['open_time']),
                'open': float(c['open_price']),
                'high': float(c['high']),
                'low': float(c['low']),
                'close': float(c['close_price']),
                'volume': float(c.get('volume', 0))
            } for c in candles]

            df = pd.DataFrame(df_data).sort_values('date').reset_index(drop=True)
            print(f"Загружено {len(df)} свечей  {df['date'].iloc[0]} → {df['date'].iloc[-1]}")
            return df

        except Exception as e:
            print(f"Исключение при загрузке данных: {e}")
            return pd.DataFrame()

    def calculate_sma(self, data: pd.DataFrame, period: int = 20) -> pd.Series:
        return data['close'].rolling(window=period).mean()

    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def simulate_trade(self,
                       entry_price: float,
                       trade_type: str,
                       entry_index: int,
                       data: pd.DataFrame,
                       tp_percent: float = 4.0,
                       sl_percent: float = 2.0,
                       max_candles: int = 4,
                       commission_pct: float = 0.00075,
                       slippage_pct: float = 0.0005) -> Dict:
        """
        Симуляция одной сделки с учётом slippage и комиссии (round-trip).
        Выход проверяется начиная со следующей свечи.
        """
        if entry_index + 1 >= len(data):
            return {
                'status': 'NOT_ENOUGH_DATA',
                'candles_held': 0,
                'pnl_pct': 0.0,
                'gross_pnl_pct': 0.0,
                'exit_price': entry_price,
                'exit_type': 'NOT_ENOUGH_DATA',
                'entry_price_real': entry_price,
                'exit_time': data.iloc[entry_index]['date'].isoformat()
            }

        # Реальная цена входа с учётом проскальзывания
        real_entry = entry_price * (1 + slippage_pct) if trade_type == 'BUY' else \
                     entry_price * (1 - slippage_pct)

        exit_price = None
        exit_type = None
        candles_held = 0
        exit_idx = None

        for j in range(1, max_candles + 1):
            idx = entry_index + j
            if idx >= len(data):
                break

            current_price = data.iloc[idx]['close']
            candles_held = j
            exit_idx = idx

            if trade_type == 'BUY':
                pnl_pct = (current_price - real_entry) / real_entry * 100
                if pnl_pct >= tp_percent:
                    exit_price = current_price * (1 - slippage_pct)
                    exit_type = 'TP'
                    break
                if pnl_pct <= -sl_percent:
                    exit_price = current_price * (1 - slippage_pct)
                    exit_type = 'SL'
                    break
            else:  # SELL
                pnl_pct = (real_entry - current_price) / real_entry * 100
                if pnl_pct >= tp_percent:
                    exit_price = current_price * (1 + slippage_pct)
                    exit_type = 'TP'
                    break
                if pnl_pct <= -sl_percent:
                    exit_price = current_price * (1 + slippage_pct)
                    exit_type = 'SL'
                    break

        # Выход по времени или конец данных
        if exit_type is None:
            if exit_idx is None:
                # Даже первой проверки не было
                exit_type = 'NOT_ENOUGH_DATA'
                exit_price = real_entry
                candles_held = 0
                exit_idx = entry_index
            else:
                exit_type = 'TIME_EXIT'
                exit_price = data.iloc[exit_idx]['close']
                if trade_type == 'BUY':
                    exit_price *= (1 - slippage_pct)
                else:
                    exit_price *= (1 + slippage_pct)

        # Итоговый P&L
        if trade_type == 'BUY':
            gross_pnl_pct = (exit_price - real_entry) / real_entry * 100
        else:
            gross_pnl_pct = (real_entry - exit_price) / real_entry * 100

        commission_cost_pct = commission_pct * 2 * 100          # round-trip
        net_pnl_pct = gross_pnl_pct - commission_cost_pct

        exit_time = data.iloc[exit_idx]['date'] if exit_idx is not None else \
                    data.iloc[entry_index]['date']

        return {
            'status': exit_type,
            'candles_held': candles_held,
            'pnl_pct': round(net_pnl_pct, 4),
            'gross_pnl_pct': round(gross_pnl_pct, 4),
            'exit_price': round(exit_price, 6),
            'exit_type': exit_type,
            'entry_price_real': round(real_entry, 6),
            'exit_time': exit_time.isoformat()
        }

    def find_trading_opportunities_sma(self, data: pd.DataFrame) -> List[Dict]:
        data['SMA_20'] = self.calculate_sma(data, 20)
        opportunities = []

        for i in range(20, len(data) - max(4, 1)):
            if pd.isna(data.iloc[i]['SMA_20']):
                continue

            prev = data.iloc[i-1]
            curr = data.iloc[i]

            if prev['close'] <= prev['SMA_20'] and curr['close'] > curr['SMA_20']:
                opportunities.append({
                    'index': i,
                    'timestamp': curr['date'],
                    'type': 'BUY',
                    'entry_price': curr['close'],
                    'sma_value': curr['SMA_20'],
                    'price_vs_sma': (curr['close'] / curr['SMA_20'] - 1) * 100,
                    'strategy': 'SMA_CROSSOVER'
                })
            elif prev['close'] >= prev['SMA_20'] and curr['close'] < curr['SMA_20']:
                opportunities.append({
                    'index': i,
                    'timestamp': curr['date'],
                    'type': 'SELL',
                    'entry_price': curr['close'],
                    'sma_value': curr['SMA_20'],
                    'price_vs_sma': (curr['close'] / curr['SMA_20'] - 1) * 100,
                    'strategy': 'SMA_CROSSOVER'
                })

        return opportunities

    def find_trading_opportunities_rsi(self, data: pd.DataFrame) -> List[Dict]:
        data['RSI_14'] = self.calculate_rsi(data, 14)
        opportunities = []

        for i in range(14, len(data) - max(4, 1)):
            rsi = data.iloc[i]['RSI_14']
            if pd.isna(rsi):
                continue
            if rsi < 30:
                opportunities.append({
                    'index': i,
                    'timestamp': data.iloc[i]['date'],
                    'type': 'BUY',
                    'entry_price': data.iloc[i]['close'],
                    'rsi_value': rsi,
                    'strategy': 'RSI_STRATEGY'
                })
            elif rsi > 70:
                opportunities.append({
                    'index': i,
                    'timestamp': data.iloc[i]['date'],
                    'type': 'SELL',
                    'entry_price': data.iloc[i]['close'],
                    'rsi_value': rsi,
                    'strategy': 'RSI_STRATEGY'
                })

        return opportunities

    def run_backtest(self,
                    data: pd.DataFrame,
                    strategy: str,
                    initial_deposit: float,
                    tp_percent: float,
                    sl_percent: float,
                    max_candles: int,
                    commission_pct: float = 0.00075,
                    slippage_pct: float = 0.0005) -> Dict:
        """Основная функция бэктестинга с взаимоисключающими позициями"""

        if strategy == 'SMA_CROSSOVER':
            opportunities = self.find_trading_opportunities_sma(data)
        elif strategy == 'RSI_STRATEGY':
            opportunities = self.find_trading_opportunities_rsi(data)
        else:
            return {'error': f'Неизвестная стратегия: {strategy}'}

        trades = []
        equity_curve = [initial_deposit]
        current_balance = initial_deposit

        # Ключевой момент: до какой свечи (включительно) позиция остаётся открытой
        locked_until_index = -1

        for opp in opportunities:
            entry_idx = opp['index']

            # Пропускаем сигнал, если предыдущая позиция ещё не закрыта
            if entry_idx <= locked_until_index:
                continue

            # Симулируем сделку (в simulate_trade проверка начинается со следующей свечи!)
            sim = self.simulate_trade(
                opp['entry_price'],
                opp['type'],
                entry_idx,
                data,
                tp_percent=tp_percent,
                sl_percent=sl_percent,
                max_candles=max_candles,
                commission_pct=commission_pct,
                slippage_pct=slippage_pct
            )

            # Если симуляция не состоялась (недостаточно данных) — пропускаем
            if sim['candles_held'] == 0 and sim['exit_type'] in ('NOT_ENOUGH_DATA', 'END_OF_DATA'):
                continue

            # Вычисляем индекс свечи закрытия
            exit_idx = entry_idx + sim['candles_held']

            # Обновляем баланс (все деньги в сделке → pnl считается от current_balance)
            pnl_abs = current_balance * (sim['pnl_pct'] / 100)
            current_balance += pnl_abs
            equity_curve.append(current_balance)

            # Формируем запись о сделке
            trade_info = {
                'type': opp['type'],
                'entry_time': opp['timestamp'].isoformat(),
                'entry_price': round(opp['entry_price'], 6),
                'exit_price': sim['exit_price'],
                'exit_time': sim['exit_time'],
                'pnl_pct': sim['pnl_pct'],
                'gross_pnl_pct': sim['gross_pnl_pct'],
                'candles_held': sim['candles_held'],
                'status': sim['status'],
                'exit_type': sim['exit_type'],
                'strategy': opp['strategy']
            }

            if 'sma_value' in opp:
                trade_info['sma_value'] = round(opp['sma_value'], 4)
                trade_info['price_vs_sma'] = round(opp['price_vs_sma'], 4)
            if 'rsi_value' in opp:
                trade_info['rsi_value'] = round(opp['rsi_value'], 2)

            trades.append(trade_info)

            # Блокируем входы до момента закрытия этой позиции
            locked_until_index = exit_idx

            print(f"Сделка открыта на индексе {entry_idx}, закрыта на {exit_idx} | "
                f"Net P&L: {sim['pnl_pct']:.2f}% | Баланс: {current_balance:,.2f}")

        stats = self.calculate_statistics(trades, equity_curve, initial_deposit, data)

        return {
            'success': True,
            'trades': trades,
            'statistics': stats,
            'equity_curve': [round(e, 2) for e in equity_curve],
            'opportunities_count': len(opportunities),
            'executed_trades_count': len(trades),
            'initial_deposit': initial_deposit,
            'final_deposit': round(current_balance, 2),
            'strategy_used': strategy,
            'max_candles_used': max_candles
        }

    def calculate_statistics(self, trades: List[Dict], equity_curve: List[float],
                             initial_deposit: float, data: pd.DataFrame) -> Dict:
        if not trades:
            return {
                'total_trades': 0, 'profitable_trades': 0, 'losing_trades': 0,
                'win_rate': 0, 'avg_return_per_trade': 0, 'total_return_percent': 0,
                'max_drawdown': 0, 'buy_hold_return': 0, 'buy_hold_value': initial_deposit,
                'max_buy_hold_drawdown': 0, 'comparison_vs_bh': 0,
                'buy_trades_count': 0, 'sell_trades_count': 0,
                'avg_holding_time_candles': 0, 'initial_deposit': initial_deposit,
                'final_deposit': initial_deposit
            }

        df = pd.DataFrame(trades)

        total_trades = len(trades)
        profitable = len(df[df['pnl_pct'] > 0])
        win_rate = profitable / total_trades * 100 if total_trades else 0

        total_return_pct = (equity_curve[-1] - initial_deposit) / initial_deposit * 100

        # Max drawdown
        eq = pd.Series(equity_curve)
        rolling_max = eq.cummax()
        drawdowns = (eq - rolling_max) / rolling_max * 100
        max_dd = drawdowns.min()

        # Buy & Hold
        if len(data) >= 2:
            bh_start = data['close'].iloc[0]
            bh_end = data['close'].iloc[-1]
            bh_return = (bh_end - bh_start) / bh_start * 100
            bh_value = initial_deposit * (1 + bh_return / 100)

            bh_eq = data['close'] / bh_start * initial_deposit
            bh_rolling_max = bh_eq.cummax()
            bh_dd = ((bh_eq - bh_rolling_max) / bh_rolling_max * 100).min()
        else:
            bh_return = bh_value = bh_dd = 0

        buy_tr = df[df['type'] == 'BUY']
        sell_tr = df[df['type'] == 'SELL']

        return {
            'total_trades': total_trades,
            'profitable_trades': profitable,
            'losing_trades': total_trades - profitable,
            'win_rate': round(win_rate, 2),
            'avg_return_per_trade': round(df['pnl_pct'].mean(), 2),
            'total_return_percent': round(total_return_pct, 2),
            'total_profit': round(equity_curve[-1] - initial_deposit, 2),
            'max_drawdown': round(max_dd, 2),
            'buy_hold_return': round(bh_return, 2),
            'buy_hold_value': round(bh_value, 2),
            'max_buy_hold_drawdown': round(bh_dd, 2),
            'comparison_vs_bh': round(total_return_pct - bh_return, 2),
            'buy_trades_count': len(buy_tr),
            'sell_trades_count': len(sell_tr),
            'buy_win_rate': round(len(buy_tr[buy_tr['pnl_pct'] > 0]) / len(buy_tr) * 100, 2) if len(buy_tr) else 0,
            'sell_win_rate': round(len(sell_tr[sell_tr['pnl_pct'] > 0]) / len(sell_tr) * 100, 2) if len(sell_tr) else 0,
            'avg_holding_time_candles': round(df['candles_held'].mean(), 1),
            'initial_deposit': initial_deposit,
            'final_deposit': round(equity_curve[-1], 2)
        }


tester = TradingStrategyTester()


@strategy_bp.route('/test', methods=['POST'])
def test_strategy():
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({'success': False, 'message': 'No JSON payload'}), 400

        symbol        = payload.get('symbol', 'BTCUSDT')
        timeframe     = payload.get('timeframe', '1h')
        start_date    = payload.get('start_date')
        end_date      = payload.get('end_date') or datetime.now().strftime('%Y-%m-%d')
        initial_deposit = float(payload.get('initial_deposit', 100000))
        tp_pct        = float(payload.get('tp_percent', 4.0))
        sl_pct        = float(payload.get('sl_percent', 2.0))
        max_candles   = int(payload.get('max_candles', 4))
        strategy      = payload.get('strategy', 'SMA_CROSSOVER')
        commission    = float(payload.get('commission_pct', 0.05)) / 100
        slippage      = float(payload.get('slippage_pct', 0.05))   / 100

        if not start_date:
            return jsonify({'success': False, 'message': 'start_date is required'}), 400

        df = tester.fetch_ohlcv_data(symbol, timeframe, start_date, end_date)
        if df.empty:
            return jsonify({'success': False, 'message': 'Не удалось загрузить исторические данные'}), 400

        result = tester.run_backtest(
            df, strategy, initial_deposit, tp_pct, sl_pct, max_candles,
            commission_pct=commission, slippage_pct=slippage
        )

        if 'error' in result:
            return jsonify({'success': False, 'message': result['error']}), 400

        result.update({
            'success': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'test_period': {
                'start': start_date,
                'end': end_date,
                'total_candles': len(df)
            }
        })

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500


@strategy_bp.route('/strategies', methods=['GET'])
def get_strategies():
    return jsonify({
        'success': True,
        'strategies': [
            {'id': 'SMA_CROSSOVER', 'name': 'SMA Crossover', 'description': 'Пересечение цены и SMA(20)'},
            {'id': 'RSI_STRATEGY',  'name': 'RSI Strategy',  'description': 'RSI < 30 → long, RSI > 70 → short'}
        ]
    })


@strategy_bp.route('/status', methods=['GET'])
def status():
    return jsonify({'success': True, 'message': 'Strategy module active'})