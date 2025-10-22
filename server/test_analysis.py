#!/usr/bin/env python3
"""
Тестовый скрипт для проверки API анализа паттернов
"""
import requests
import json
import time
from datetime import datetime, timedelta

def test_analysis_api():
    """Тестирует API анализа паттернов"""
    base_url = "http://localhost:5010"
    
    # Тестовые данные - последние 3 свечи
    test_candles = [
        {
            "open_time": "2024-01-15T00:00:00Z",
            "close_time": "2024-01-15T23:59:59Z", 
            "open_price": 42000.0,
            "close_price": 42500.0,
            "high": 43000.0,
            "low": 41800.0,
            "volume": 1000000.0
        },
        {
            "open_time": "2024-01-16T00:00:00Z",
            "close_time": "2024-01-16T23:59:59Z",
            "open_price": 42500.0, 
            "close_price": 42000.0,
            "high": 42800.0,
            "low": 41500.0,
            "volume": 1200000.0
        },
        {
            "open_time": "2024-01-17T00:00:00Z",
            "close_time": "2024-01-17T23:59:59Z",
            "open_price": 42000.0,
            "close_price": 43500.0, 
            "high": 44000.0,
            "low": 41800.0,
            "volume": 1500000.0
        }
    ]
    
    payload = {
        "num_candles": 3,
        "candles": test_candles,
        "timeframe": "1d"
    }
    
    print("Тестируем API анализа паттернов...")
    print(f"Отправляем запрос с {len(test_candles)} свечами")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{base_url}/analyze_pattern",
            json=payload,
            timeout=120  # 2 минуты таймаут
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Ответ получен за {duration:.2f} секунд")
        print(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Анализ успешно завершен!")
            print(f"Найдено совпадений: {data.get('statistics', {}).get('matches_found', 0)}")
            
            if 'performance_stats' in data:
                stats = data['performance_stats']
                print(f"Медианное изменение цены: {stats.get('median_change', 0)}%")
                print(f"Процент успешных паттернов: {stats.get('success_rate', 0)}%")
            
            return True
        else:
            print(f"❌ Ошибка: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Сообщение об ошибке: {error_data.get('message', 'Неизвестная ошибка')}")
            except:
                print(f"Текст ответа: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Превышено время ожидания (120 секунд)")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка подключения. Убедитесь, что сервер запущен на localhost:5010")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_data_bounds():
    """Тестирует API получения границ данных"""
    base_url = "http://localhost:5010"
    
    print("\nТестируем API границ данных...")
    
    try:
        response = requests.get(f"{base_url}/api/pattern_bounds?timeframe=1d", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Границы данных получены!")
            print(f"Начало данных: {data.get('start', 'Неизвестно')}")
            print(f"Конец данных: {data.get('end', 'Неизвестно')}")
            return True
        else:
            print(f"❌ Ошибка получения границ: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при получении границ данных: {e}")
        return False

if __name__ == "__main__":
    print("=== Тестирование API анализа паттернов ===\n")
    
    # Тестируем границы данных
    bounds_ok = test_data_bounds()
    
    # Тестируем анализ
    analysis_ok = test_analysis_api()
    
    print(f"\n=== Результаты тестирования ===")
    print(f"Границы данных: {'✅ OK' if bounds_ok else '❌ FAIL'}")
    print(f"Анализ паттернов: {'✅ OK' if analysis_ok else '❌ FAIL'}")
    
    if bounds_ok and analysis_ok:
        print("\n🎉 Все тесты прошли успешно!")
    else:
        print("\n⚠️ Некоторые тесты не прошли. Проверьте логи сервера.")
