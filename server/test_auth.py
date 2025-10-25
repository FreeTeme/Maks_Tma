#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы аутентификации
"""

import requests
import json

BASE_URL = "http://localhost:5010"

def test_login():
    """Тестирует систему входа"""
    print("🔐 Тестирование системы аутентификации")
    print("=" * 50)
    
    # Тест 1: Попытка доступа без аутентификации
    print("\n1. Тест доступа без аутентификации:")
    response = requests.get(f"{BASE_URL}/")
    print(f"   Статус: {response.status_code}")
    if response.status_code == 302:
        print("   ✅ Перенаправление на страницу входа работает")
    else:
        print("   ❌ Ошибка: должен быть редирект на /login")
    
    # Тест 2: Получение страницы входа
    print("\n2. Тест страницы входа:")
    response = requests.get(f"{BASE_URL}/login")
    print(f"   Статус: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Страница входа доступна")
    else:
        print("   ❌ Ошибка: страница входа недоступна")
    
    # Тест 3: Неверный пароль
    print("\n3. Тест неверного пароля:")
    response = requests.post(f"{BASE_URL}/login", data={'password': 'wrong_password'})
    print(f"   Статус: {response.status_code}")
    try:
        data = response.json()
        if not data.get('success'):
            print("   ✅ Неверный пароль отклонен")
        else:
            print("   ❌ Ошибка: неверный пароль принят")
    except:
        print("   ❌ Ошибка: не удалось получить JSON ответ")
    
    # Тест 4: Правильный пароль работника
    print("\n4. Тест входа работника:")
    session = requests.Session()
    response = session.post(f"{BASE_URL}/login", data={'password': '0397'})
    print(f"   Статус: {response.status_code}")
    try:
        data = response.json()
        if data.get('success'):
            print("   ✅ Вход работника успешен")
            
            # Проверяем доступ к защищенной странице
            response = session.get(f"{BASE_URL}/profile")
            print(f"   Доступ к профилю: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Доступ к профилю разрешен")
            else:
                print("   ❌ Ошибка: доступ к профилю запрещен")
        else:
            print("   ❌ Ошибка: вход работника не удался")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тест 5: Правильный пароль админа
    print("\n5. Тест входа админа:")
    session = requests.Session()
    response = session.post(f"{BASE_URL}/login", data={'password': '6860'})
    print(f"   Статус: {response.status_code}")
    try:
        data = response.json()
        if data.get('success'):
            print("   ✅ Вход админа успешен")
            
            # Проверяем доступ к админ панели
            response = session.get(f"{BASE_URL}/admin/logs")
            print(f"   Доступ к админ панели: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Доступ к админ панели разрешен")
            else:
                print("   ❌ Ошибка: доступ к админ панели запрещен")
        else:
            print("   ❌ Ошибка: вход админа не удался")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тест 6: Проверка API статистики
    print("\n6. Тест API статистики:")
    session = requests.Session()
    response = session.post(f"{BASE_URL}/login", data={'password': '6860'})
    if response.json().get('success'):
        response = session.get(f"{BASE_URL}/api/admin/stats")
        print(f"   Статус API статистики: {response.status_code}")
        try:
            data = response.json()
            if data.get('success'):
                print("   ✅ API статистики работает")
                print(f"   Статистика: {data.get('stats', {})}")
            else:
                print("   ❌ Ошибка: API статистики не работает")
        except Exception as e:
            print(f"   ❌ Ошибка API: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Тестирование завершено")

if __name__ == "__main__":
    print("Запуск тестов системы аутентификации...")
    print("Убедитесь, что сервер запущен на http://localhost:5010")
    print()
    
    try:
        test_login()
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка: Не удается подключиться к серверу")
        print("Убедитесь, что сервер запущен на http://localhost:5010")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
