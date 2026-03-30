# cli/main.py
import os
import sys
import time
from tabulate import tabulate
from colorama import init, Fore, Style

# Добавляем родительскую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.scraper import TwoGISScraper
from db.database import save_leads, load_leads, get_db_stats, clear_db
from db.exporter import export_to_csv, export_to_excel
from config import CITIES, CATEGORIES

init(autoreset=True) # Инициализация colorama

def print_header():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.CYAN + Style.BRIGHT + "═══════════════════════════════════════")
    print(Fore.CYAN + Style.BRIGHT + "   LEAD GENERATOR — Бизнес-база КР")
    print(Fore.CYAN + Style.BRIGHT + "═══════════════════════════════════════" + Style.RESET_ALL)

def show_main_menu():
    print("\n1. 🔍 Новый поиск (скрапинг)")
    print("2. 📊 Просмотр базы данных")
    print("3. 🔎 Фильтр и экспорт")
    print("4. 📈 Статистика базы")
    print("5. 🗑️  Очистить базу")
    print("0. Выход\n")
    return input("Выбор: ").strip()

def new_search():
    print(Fore.YELLOW + "\n--- Новый поиск ---")
    
    # 1. Город
    print("Выберите город:")
    city_keys = list(CITIES.keys())
    for i, city_key in enumerate(city_keys, 1):
        print(f"{i}. {CITIES[city_key]}")
    print("0. Ввести свой URL-идентификатор (например, astana)")
    
    city_choice = input("Выбор: ").strip()
    if city_choice == "0":
        city_id = input("Введите ID города: ").strip()
        city_name = city_id.capitalize()
    else:
        try:
            city_id = city_keys[int(city_choice) - 1]
            city_name = CITIES[city_id]
        except (ValueError, IndexError):
            print(Fore.RED + "Неверный выбор.")
            return

    # 2. Категория
    print(f"\nВыбран город: {Fore.GREEN}{city_name}{Style.RESET_ALL}")
    print("Выберите категорию:")
    for i, cat in enumerate(CATEGORIES, 1):
        print(f"{i}. {cat}")
    print("0. Ввести свою категорию")
    
    cat_choice = input("Выбор: ").strip()
    if cat_choice == "0":
        search_query = input("Введите запрос: ").strip()
    else:
        try:
            search_query = CATEGORIES[int(cat_choice) - 1]
        except (ValueError, IndexError):
            print(Fore.RED + "Неверный выбор.")
            return
            
    # 3. Страницы
    try:
        pages = int(input("\nСколько страниц парсить? (1-10, Enter=1): ") or "1")
    except ValueError:
        pages = 1

    print(Fore.YELLOW + f"\nЗапускаем скрапер: {city_name} -> {search_query} ({pages} стр.)")
    print("Это может занять время. Для остановки нажмите Ctrl+C (собранные данные сохранятся).\n")
    
    scraper = TwoGISScraper()
    leads_batch = []
    total_saved = 0
    
    try:
        # Получаем данные через генератор
        for lead in scraper.scrape_leads(city_id, city_name, search_query, pages):
            leads_batch.append(lead)
            print(f"[{len(leads_batch)}] Найден: {lead.name} {Fore.GREEN}({lead.phone or 'Нет телефона'}){Style.RESET_ALL}")
            
            # Сохраняем пачками по 5, чтобы не терять при Ctrl+C
            if len(leads_batch) >= 5:
                saved = save_leads(leads_batch)
                total_saved += saved
                leads_batch.clear()
                
    except KeyboardInterrupt:
        print(Fore.RED + "\n[!] Прервано пользователем. Сохраняем остатки...")
    except Exception as e:
        print(Fore.RED + f"\n[!] Ошибка скрапинга: {e}")
    finally:
        # Сохраняем остатки
        if leads_batch:
            saved = save_leads(leads_batch)
            total_saved += saved
        
        scraper.close()
        print(Fore.GREEN + f"\nСкрапинг завершён. Добавлено новых/обновлено: {total_saved}")
        input("\nНажмите Enter для возврата в меню...")

def view_database():
    print(Fore.YELLOW + "\n--- Просмотр БД (последние 20 записей) ---")
    df = load_leads()
    if df.empty:
        print("База пуста.")
    else:
        # Показываем только основные колонки
        view_cols = ['name', 'city', 'category', 'phone', 'instagram']
        available_cols = [c for c in view_cols if c in df.columns]
        
        print(tabulate(df.tail(20)[available_cols], headers='keys', tablefmt='psql', showindex=False))
        print(f"\nВсего записей: {len(df)}")
    
    input("\nНажмите Enter для возврата в меню...")

def filter_and_export():
    print(Fore.YELLOW + "\n--- Экспорт и Фильтр ---")
    df = load_leads()
    if df.empty:
        print("База пуста. Сначала запустите поиск.")
        input("\nНажмите Enter...")
        return
        
    print(f"Доступно записей: {len(df)}")
    print("1. Экспорт всей базы CSV")
    print("2. Экспорт всей базы Excel")
    print("3. Фильтр: Только с телефонами -> Excel")
    print("4. Фильтр: По категории -> Excel")
    print("5. Фильтр: По городу -> Excel")
    
    choice = input("\nВыбор: ").strip()
    
    try:
        if choice == "1":
            path = export_to_csv(df)
            print(Fore.GREEN + f"Сохранено: {path}")
            
        elif choice == "2":
            path = export_to_excel(df)
            print(Fore.GREEN + f"Сохранено: {path}")
            
        elif choice == "3":
            if 'phone' in df.columns:
                filtered = df[df['phone'].notna() & (df['phone'] != "")]
                path = export_to_excel(filtered, "leads_with_phones")
                print(Fore.GREEN + f"Сохранено: {path} (Кол-во: {len(filtered)})")
            
        elif choice == "4":
            if 'category' not in df.columns and 'search_category' not in df.columns:
                print("Нет колонки категорий.")
                return
                
            col = 'category' if 'category' in df.columns else 'search_category'
            cats = df[col].dropna().unique()
            print("\nДоступные категории:")
            for i, c in enumerate(cats, 1):
                print(f"{i}. {c}")
            c_idx = int(input("Выберите номер: ")) - 1
            
            filtered = df[df[col] == cats[c_idx]]
            path = export_to_excel(filtered, f"leads_{cats[c_idx]}")
            print(Fore.GREEN + f"Сохранено: {path} (Кол-во: {len(filtered)})")
            
        elif choice == "5":
            if 'city' not in df.columns:
                return
            cities = df['city'].dropna().unique()
            print("\nДоступные города:")
            for i, c in enumerate(cities, 1):
                print(f"{i}. {c}")
            c_idx = int(input("Выберите номер: ")) - 1
            
            filtered = df[df['city'] == cities[c_idx]]
            path = export_to_excel(filtered, f"leads_{cities[c_idx]}")
            print(Fore.GREEN + f"Сохранено: {path} (Кол-во: {len(filtered)})")
            
    except Exception as e:
        print(Fore.RED + f"Ошибка экспорта: {e}")
        
    input("\nНажмите Enter для возврата в меню...")

def view_stats():
    print(Fore.YELLOW + "\n--- Статистика БД ---")
    stats = get_db_stats()
    
    print(f"Всего лидов: {Fore.CYAN}{stats.get('total', 0)}{Style.RESET_ALL}")
    print(f"С телефоном: {Fore.CYAN}{stats.get('with_phone', 0)}{Style.RESET_ALL}")
    print(f"С email: {Fore.CYAN}{stats.get('with_email', 0)}{Style.RESET_ALL}")
    print(f"С Instagram: {Fore.CYAN}{stats.get('with_instagram', 0)}{Style.RESET_ALL}")
    
    print("\nТоп Городов:")
    for k, v in list(stats.get("by_city", {}).items())[:5]:
        print(f" - {k}: {v}")
        
    print("\nТоп Категорий:") # search_category is safer sometimes, but category is fine
    for k, v in list(stats.get("by_category", {}).items())[:5]:
        print(f" - {k}: {v}")
        
    input("\nНажмите Enter для возврата в меню...")

def main():
    while True:
        print_header()
        choice = show_main_menu()
        
        if choice == "1":
            new_search()
        elif choice == "2":
            view_database()
        elif choice == "3":
            filter_and_export()
        elif choice == "4":
            view_stats()
        elif choice == "5":
            if input(Fore.RED + "Отправить в мусор всю базу? (да/нет): ").strip().lower() == "да":
                clear_db()
                print(Fore.GREEN + "База очищена.")
                time.sleep(1)
        elif choice == "0":
            print("Выход...")
            break
        else:
            print("Неверный выбор.")
            time.sleep(1)

if __name__ == "__main__":
    main()
