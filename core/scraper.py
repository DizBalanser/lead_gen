# core/scraper.py
import time
import re
from typing import List, Optional, Generator
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from core.models import Lead
from config import BASE_URL, SEARCH_URL_TEMPLATE, HEADLESS, REQUEST_DELAY_SECONDS, PAGE_LOAD_TIMEOUT

class TwoGISScraper:
    """Модуль скрапинга 2GIS на основе Selenium."""
    
    def __init__(self):
        self.driver = self._init_driver()
        
    def _init_driver(self) -> webdriver.Chrome:
        options = Options()
        if HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        options.add_argument("--disable-notifications")
        return webdriver.Chrome(options=options)
        
    def close(self):
        if self.driver:
            self.driver.quit()

    def scrape_leads(self, city: str, city_name: str, search_query: str, pages: int) -> Generator[Lead, None, None]:
        """
        Главный генератор лидов. Сначала парсит списки (Фаза 1),
        затем заходит в каждую карточку для детальной инфы (Фаза 2).
        Возвращает лиды по одному через yield.
        """
        urls_and_basics = self._collect_links_and_basics(city, search_query, pages)
        
        for basic_data in urls_and_basics:
            if basic_data.get("url"):
                details = self._get_details(basic_data["url"], city_name)
                # Мержим базовые данные и детали
                merged = {**basic_data, **details}
                
                yield Lead(
                    external_id=merged.get("external_id", ""),
                    name=merged.get("name", "Unknown"),
                    city=city_name,
                    address=merged.get("address", ""),
                    district=merged.get("district"),
                    category=merged.get("category"),
                    search_category=search_query,
                    phone=merged.get("phone"),
                    email=merged.get("email"),
                    website=merged.get("website"),
                    instagram=merged.get("instagram"),
                    rating=merged.get("rating"),
                    review_count=merged.get("review_count"),
                    url=merged.get("url")
                )
            else:
                # Если ссылки нет
                yield Lead(
                    external_id=basic_data.get("external_id", ""),
                    name=basic_data.get("name", "Unknown"),
                    city=city_name,
                    address=basic_data.get("address", ""),
                    search_category=search_query,
                    category=basic_data.get("category")
                )

    def _collect_links_and_basics(self, city: str, query: str, max_pages: int) -> List[dict]:
        """Собирает список площадок со страниц поиска."""
        results = []
        url = SEARCH_URL_TEMPLATE.format(base=BASE_URL, city=city, query=query.replace(" ", "+"))
        self.driver.get(url)
        time.sleep(3) # Initial load
        
        for page in range(1, max_pages + 1):
            try:
                WebDriverWait(self.driver, PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, '_1kf6gff') or contains(@class, '_1heozzz')]"))
                )
            except TimeoutException:
                # Можем попытаться обновить или пропустить капчу
                print("\n[!] Не удалось загрузить результаты. Возможно капча? Ждём 10 секунд...")
                time.sleep(10)
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//div[contains(@class, '_1kf6gff') or contains(@class, '_1heozzz')]"))
                    )
                except TimeoutException:
                    break

            time.sleep(1) # Extra wait for react render
            
            # Парсим элементы
            elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, '_1kf6gff') or contains(@class, '_1heozzz')]")
            for el in elements:
                try:
                    basic = self._parse_basic_card(el)
                    if basic:
                        results.append(basic)
                except StaleElementReferenceException:
                    continue

            # Переход на следующую страницу
            if page < max_pages:
                if not self._go_next_page():
                    break
                time.sleep(REQUEST_DELAY_SECONDS)
                
        return results

    def _parse_basic_card(self, el) -> Optional[dict]:
        """Парсинг базовой инфы с карточки."""
        text = el.text
        if not text:
            return None
            
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if not lines:
            return None
            
        name = lines[0]
        
        # Попытка найти ссылку
        try:
            link_el = el.find_element(By.XPATH, ".//a[contains(@href, '/firm/')]")
            href = link_el.get_attribute("href")
            external_id = href.split("/firm/")[1].split("?")[0].split("/")[0] if "/firm/" in href else ""
        except NoSuchElementException:
            href = None
            external_id = ""
            
        # Попытка найти рейтинг
        rating = None
        reviews = None
        for i, line in enumerate(lines):
            if "," in line and "оцен" in line:
                # "4,5, 12 оценок"
                try:
                    parts = line.split(",")
                    rating_part = parts[0].replace(",", ".")
                    rating = float(rating_part)
                    reviews_str = re.sub(r'\D', '', parts[1])
                    reviews = int(reviews_str) if reviews_str else 0
                except:
                    pass
                break
                
        # Попытка найти адрес/категорию (примерно, т.к. точные данные возьмём с деталки)
        address = lines[1] if len(lines) > 1 else ""
        category = lines[2] if len(lines) > 2 else ""

        return {
            "name": name,
            "url": href,
            "external_id": external_id,
            "rating": rating,
            "review_count": reviews,
            "address": address,
            "category": category
        }

    def _get_details(self, url: str, city_name: str) -> dict:
        """Переход на детальную страницу для получения телефона, инсты, email и более точного адреса."""
        details = {
            "phone": None,
            "email": None,
            "instagram": None,
            "website": None,
            "address": None,
            "district": None,
            "category": None
        }
        
        try:
            self.driver.get(url)
            time.sleep(2) # Load details
            
            # 1. Точный адрес и район
            try:
                addr_el = self.driver.find_element(By.XPATH, "//div[contains(@class, '_1p8iqzw')]//div[contains(@class, '_2lcm958')] | //h2[contains(@class, '_1y2s87x')]")
                details["address"] = addr_el.text
                if "мкр" in details["address"].lower() or "микрорайон" in details["address"].lower():
                    # Примитивное извлечение района
                    parts = details["address"].split(",")
                    for p in parts:
                        if "мкр" in p.lower() or "микрорайон" in p.lower():
                            details["district"] = p.strip()
            except NoSuchElementException:
                pass
                
            # 2. Категория (более точная с деталки)
            try:
                cat_el = self.driver.find_element(By.XPATH, "//div[contains(@class, '_1h2zae6')] | //span[contains(@class, '_oqoid')]")
                details["category"] = cat_el.text
            except NoSuchElementException:
                pass

            # 3. Телефон (нужно нажать "Показать телефон")
            try:
                phone_btn = self.driver.find_element(By.XPATH, "//button[descendant::span[contains(text(), 'Показать телефон')] or contains(text(), 'Показать телефон')]")
                phone_btn.click()
                time.sleep(1) # wait for phone to reveal
            except NoSuchElementException:
                pass
                
            # Ищем все ссылки
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    if href.startswith("tel:"):
                        details["phone"] = href.replace("tel:", "").strip()
                    elif href.startswith("mailto:"):
                        details["email"] = href.replace("mailto:", "").strip()
                    elif "instagram.com" in href:
                        details["instagram"] = href
                    elif "wa.me" in href or "api.whatsapp.com" in href:
                         pass # Можно сохранять whatsapp
                    elif href.startswith("http") and "2gis" not in href and "google" not in href and "instagram" not in href:
                        # Учитываем только первую не-социальную ссылку как сайт
                        if not details["website"]:
                            details["website"] = href
                except StaleElementReferenceException:
                    pass
                    
        except Exception as e:
            # Игнорируем ошибки при загрузке деталки - вернем что смогли
            pass
            
        return details

    def _go_next_page(self) -> bool:
        """Попытка переключить на следующую страницу (пагинация)."""
        try:
            # Ищем кнопку "Дальше" (обычно последняя кнопка в блоке пагинации или содержит иконку вправо)
            # В 2GIS часто класс _n5hmn94
            next_btn = self.driver.find_element(By.XPATH, "//div[contains(@class, '_n5hmn94')]//button[last()] | //div[contains(@class, '_1x4k6z7')]//div[last()]")
            if next_btn.is_enabled():
                # Прокручиваем к кнопке
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                time.sleep(0.5)
                next_btn.click()
                return True
        except Exception:
            pass
        return False
