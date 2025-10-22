# data_updater.py
import threading
import time
import schedule
from datetime import datetime, timedelta
import pandas as pd
from ai.main import get_full_historical_data, save_to_cache, get_cache_key, TIMEFRAME_MAP
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataUpdater:
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.update_interval = 60  # 1 час в секундах
        
    def update_all_timeframes(self):
        """Обновление данных для всех таймфреймов"""
        try:
            logger.info("Запуск фонового обновления данных...")
            
            for timeframe in TIMEFRAME_MAP.keys():
                try:
                    logger.info(f"Обновление данных для таймфрейма {timeframe}")
                    
                    # Загружаем свежие данные (функция сама определит период)
                    df = get_full_historical_data(timeframe)
                    
                    if not df.empty:
                        logger.info(f"Данные {timeframe} успешно обновлены. Записей: {len(df)}")
                    else:
                        logger.warning(f"Не удалось обновить данные для {timeframe}")
                        
                except Exception as e:
                    logger.error(f"Ошибка при обновлении {timeframe}: {e}")
                    
            logger.info("Фоновое обновление данных завершено")
            
        except Exception as e:
            logger.error(f"Критическая ошибка при обновлении данных: {e}")
    
    def incremental_update(self, timeframe='1d', lookback_days=7):
        """Инкрементальное обновление - только последние данные"""
        try:
            # Определяем дату начала обновления (последние N дней)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
            
            logger.info(f"Инкрементальное обновление {timeframe} с {start_date_str} по {end_date_str}")
            
            # Здесь нужно добавить логику для загрузки только новых данных
            # и объединения с существующими
            
            # Временно используем полную перезагрузку
            df = get_full_historical_data(timeframe)
            logger.info(f"Инкрементальное обновление {timeframe} завершено. Записей: {len(df)}")
            
        except Exception as e:
            logger.error(f"Ошибка инкрементального обновления {timeframe}: {e}")
    
    def run_scheduler(self):
        """Запуск планировщика в бесконечном цикле"""
        self.is_running = True
        
        # Немедленное обновление при старте
        self.update_all_timeframes()
        
        # Настраиваем расписание
        schedule.every(1).hours.do(self.update_all_timeframes)
        schedule.every().day.at("00:00").do(self.update_all_timeframes)  # Дублирующее обновление в полночь
        
        logger.info("Планировщик данных запущен")
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                time.sleep(300)  # Ждем 5 минут при ошибке
    
    def start(self):
        """Запуск фонового обновления"""
        if self.is_running:
            logger.warning("Фоновое обновление уже запущено")
            return
            
        self.thread = threading.Thread(target=self.run_scheduler, daemon=True)
        self.thread.start()
        logger.info("Фоновое обновление данных запущено")
    
    def stop(self):
        """Остановка фонового обновления"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=10)
        logger.info("Фоновое обновление данных остановлено")

# Глобальный экземпляр обновлятеля данных
data_updater = DataUpdater()