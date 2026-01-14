# -*- coding: utf-8 -*-
import base64
import calendar
import io
import zipfile
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict

import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import numpy as np
from io import StringIO

# ----------------------------
# KONFIGURACJA
# ----------------------------
from supla_config import *


# ----------------------------
# GIEŁDA TGE - RYNEK DNIA NASTĘPNEGO
# ----------------------------
# ----------------------------
# GIEŁDA TGE - RYNEK DNIA NASTĘPNEGO
# ----------------------------
# ----------------------------
# GIEŁDA TGE - RYNEK DNIA NASTĘPNEGO
# ----------------------------
def scrape_tge_from_pse_website(year: int, month: int) -> Optional[pd.DataFrame]:
    """
    Pobiera dane RDN z PSE (Polskie Sieci Elektroenergetyczne).
    PSE publikuje średnie ceny RDN dostępne bez logowania.
    
    Endpoint: https://www.pse.pl/dane-systemowe/funkcjonowanie-rb/raporty-dobowe-z-funkcjonowania-rb
    
    Args:
        year: Rok
        month: Miesiąc
        
    Returns:
        DataFrame z cenami godzinowymi lub None
    """
    try:
        # PSE udostępnia dane w formacie Excel/CSV
        # Format nazwy pliku: YYYYMM_ceny_rdn.xlsx lub podobny
        
        # Próba różnych formatów URL
        base_urls = [
            f"https://www.pse.pl/-/ceny-rynkowe-rdn-{year}-{month:02d}",
            f"https://www.pse.pl/getattachment/data/{year}/{month:02d}/ceny-rdn.xlsx",
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }
        
        for url in base_urls:
            try:
                response = requests.head(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    # Znaleziono plik, pobierz
                    response = requests.get(url, headers=headers, timeout=15)
                    
                    # Spróbuj wczytać jako Excel
                    df = pd.read_excel(response.content, engine='openpyxl')
                    
                    # Przetwórz dane (format zależy od struktury pliku PSE)
                    # Zakładamy kolumny: Data, Godzina, Cena
                    if len(df) > 0:
                        return process_pse_data(df)
            except:
                continue
                
        return None
        
    except Exception as e:
        return None


def process_pse_data(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Przetwarza dane z PSE do ujednoliconego formatu."""
    try:
        # Identyfikuj kolumny (różne formaty PSE)
        date_col = None
        hour_col = None
        price_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if 'data' in col_lower or 'date' in col_lower:
                date_col = col
            elif 'godzina' in col_lower or 'hour' in col_lower:
                hour_col = col
            elif 'cena' in col_lower or 'price' in col_lower or 'rdn' in col_lower:
                price_col = col
        
        if not (date_col and hour_col and price_col):
            return None
        
        df_clean = pd.DataFrame({
            'date': pd.to_datetime(df[date_col]),
            'hour': df[hour_col],
            'price_mwh': pd.to_numeric(df[price_col], errors='coerce')
        })
        
        # Stwórz timestamp
        df_clean['timestamp_local'] = df_clean.apply(
            lambda row: datetime.combine(row['date'].date(), 
                                        datetime.min.time().replace(hour=int(row['hour']))),
            axis=1
        )
        df_clean['timestamp_local'] = pd.to_datetime(df_clean['timestamp_local']).dt.tz_localize('Europe/Warsaw')
        df_clean['timestamp_utc'] = df_clean['timestamp_local'].dt.tz_convert('UTC')
        df_clean['price_per_kwh_netto'] = df_clean['price_mwh'] / 1000
        
        return df_clean[['timestamp_utc', 'timestamp_local', 'price_per_kwh_netto']]
        
    except Exception as e:
        return None


def load_tge_prices_from_csv(year: int, month: int) -> Optional[pd.DataFrame]:
    """
    Wczytuje ceny TGE z pliku CSV (jeśli dostępny).
    
    Oczekiwany format pliku: tge_prices_YYYY_MM.csv
    Kolumny: timestamp, price_kwh
    
    Przykład:
        timestamp,price_kwh
        2025-12-01 00:00:00,0.350
        2025-12-01 01:00:00,0.320
        ...
    
    Args:
        year: Rok
        month: Miesiąc
    
    Returns:
        DataFrame z cenami lub None jeśli plik nie istnieje
    """
    import os
    
    filename = f"tge_prices_{year}_{month:02d}.csv"
    
    if not os.path.exists(filename):
        return None
    
    try:
        df = pd.read_csv(filename, parse_dates=['timestamp'])
        
        if 'timestamp' not in df.columns or 'price_kwh' not in df.columns:
            print(f"    ⚠️  Błędny format CSV: wymagane kolumny 'timestamp' i 'price_kwh'")
            return None
        
        # Konwertuj timestamp na UTC i local
        df['timestamp_utc'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC')
        df['timestamp_local'] = df['timestamp_utc'].dt.tz_convert('Europe/Warsaw')
        df['price_per_kwh_netto'] = df['price_kwh']
        
        print(f"    ✅ Wczytano {len(df)} rekordów z {filename}")
        return df[['timestamp_utc', 'timestamp_local', 'price_per_kwh_netto']]
        
    except Exception as e:
        print(f"    ⚠️  Błąd wczytywania CSV: {e}")
        return None


def scrape_tge_prices_from_pge(date_str: str, verbose: bool = False) -> Optional[pd.DataFrame]:
    """
    Scraping cen TGE ze strony PGE używając Selenium (renderowanie JavaScript).
    
    Wymaga instalacji:
        pip install selenium webdriver-manager
    
    Strona PGE ładuje dane dynamicznie przez JavaScript, więc używamy
    headless Chrome do renderowania strony i wyciągania danych z kontenera.
    
    Args:
        date_str: Data w formacie YYYY-MM-DD
        verbose: Jeśli True, wypisuje logi diagnostyczne
    
    Returns:
        DataFrame z cenami godzinowymi [timestamp_local, price_per_kwh_netto] lub None
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        from bs4 import BeautifulSoup
        import time
        import re
        import pytz
        from datetime import datetime
        
        # Konfiguracja headless Chrome
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--log-level=3')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            # Załaduj stronę PGE
            url = 'https://www.gkpge.pl/dla-domu/oferta/dynamiczna-energia-z-pge'
            driver.get(url)
            
            # Czekaj na załadowanie strony
            wait = WebDriverWait(driver, 15)
            
            # Znajdź input daty i ustaw datę
            try:
                date_input = wait.until(EC.presence_of_element_located((By.ID, "tge_quotes_form_dateTime")))
                
                # Ustaw datę przez JS (omija problem element not interactable)
                driver.execute_script("arguments[0].value = arguments[1];", date_input, date_str)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", date_input)
                
                # Znajdź przycisk "Zastosuj" i kliknij
                submit_btn = driver.find_element(By.ID, "tge_quotes_form_submit")
                driver.execute_script("arguments[0].click();", submit_btn)
                
                # Czekaj na przeładowanie danych (np. aż zniknie loader lub pojawi się tabela)
                # Proste czekanie 5s powinno wystarczyć na AJAX
                time.sleep(5)
                
            except Exception as e:
                if verbose:
                    print(f"         [DEBUG] ⚠️  Problem z ustawianiem daty: {e}")
                # Kontynuuj, może domyślna data jest OK (dla dzisiaj/jutro)
            
            # Pobierz wyrenderowany HTML
            page_source = driver.page_source
            
            # Sprawdź czy dane załadowane
            if 'PLN/kWh' not in page_source and 'PLN/MWh' not in page_source:
                driver.quit()
                return None
            
            # Parse HTML
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Znajdź kontener z danymi TGE
            tge_container = soup.find('div', class_='tge-quotes-element-container')
            if not tge_container:
                tge_container = soup.find('div', {'id': 'application-143455'})
            
            if not tge_container:
                driver.quit()
                return None
            
            # Wyciągnij cały tekst z kontenera
            container_text = tge_container.get_text(separator='\n', strip=True)
            
            # Parse tekst szukając cen po nagłówku "Kurs (PLN/kWh)"
            # Format z nowymi liniami: "0-1\n295.50\n0.29550\n1-2\n300.00\n0.30000..."
            parts = container_text.split('Kurs (PLN/kWh)')
            if len(parts) < 2:
                driver.quit()
                return None
            
            data_section = parts[1]
            
            # Wzorzec: godzina_start-godzina_koniec \n liczba_MWh \n cena_kWh
            # Pattern dopasowuje: "0-1\n295.50\n0.29550" -> ('0', '1', '0.29550')
            pattern = r'(\d+)-(\d+)\s*[\d.]+\s*(0\.\d+)'
            matches = re.findall(pattern, data_section)
            
            prices = []
            for match in matches:
                try:
                    hour_start = int(match[0])
                    price_kwh = float(match[2])  # Już w PLN/kWh
                    
                    if 0 <= hour_start < 24 and 0.01 <= price_kwh <= 10:
                        prices.append((hour_start, price_kwh))
                except:
                    continue
            
            driver.quit()
            
            if not prices:
                return None
            
            # Konwertuj na DataFrame
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            warsaw_tz = pytz.timezone('Europe/Warsaw')
            
            data = []
            for hour, price in prices:
                try:
                    timestamp_local = warsaw_tz.localize(
                        datetime(date_obj.year, date_obj.month, date_obj.day, hour, 0, 0)
                    )
                    data.append({
                        'timestamp_local': timestamp_local,
                        'price_per_kwh_netto': price
                    })
                except Exception as e:
                    continue
            
            if not data:
                return None
                
            return pd.DataFrame(data)
            
        except Exception as e:
            if verbose:
                print(f"         [DEBUG] ❌ Wyjątek wewnętrzny: {e}")
            driver.quit()
            return None
            
    except ImportError as e:
        # Selenium nie zainstalowany
        if verbose:
            print(f"         [DEBUG] ❌ ImportError: {e}")
        return None
    except Exception as e:
        if verbose:
            print(f"         [DEBUG] ❌ Wyjątek zewnętrzny: {e}")
        return None
        return None
    
    return None


def fetch_tge_prices(year: int, month: int, verbose: bool = False) -> pd.DataFrame:
    """
    Pobiera ceny z TGE (Towarowa Giełda Energii) - Rynek Dnia Następnego.
    
    Strategia pobierania danych (w kolejności):
    1. Plik CSV z cenami (tge_prices_YYYY_MM.csv) - jeśli dostępny
    2. Web scraping PGE (Selenium + Chrome) - rzeczywiste ceny aktualne
    3. PSE website (Polskie Sieci Elektroenergetyczne) - dane publiczne
    4. Dane symulowane - fallback
    
    Zwraca DataFrame z kolumnami:
    - timestamp_utc: Timestamp w UTC
    - timestamp_local: Timestamp w strefie Europe/Warsaw
    - price_per_kwh_netto: Cena netto w zł/kWh
    """
    try:
        print(f"📡 Pobieranie cen giełdowych TGE za {year}-{month:02d}...")
        
        # METODA 1: Sprawdź plik CSV (cache)
        print(f"    1. Sprawdzam plik CSV tge_prices_{year}_{month:02d}.csv...")
        csv_prices = load_tge_prices_from_csv(year, month)
        if csv_prices is not None and not csv_prices.empty:
            print(f"       ✅ Wczytano dane z pliku CSV")
            return csv_prices
        else:
            print(f"       ✗ Plik nie istnieje lub jest pusty")
        
        # METODA 2: Web scraping PGE (Selenium)
        print(f"    2. Próba web scrapingu PGE (Selenium)...")
        
        # Generuj listę dat dla całego miesiąca
        last_day = calendar.monthrange(year, month)[1]
        all_prices = []
        
        # Spróbuj pobrać pierwszy dzień jako test
        first_date = f"{year}-{month:02d}-01"
        first_day_prices = scrape_tge_prices_from_pge(first_date, verbose=verbose)
        
        if first_day_prices is not None and not first_day_prices.empty:
            all_prices.append(first_day_prices)
            print(f"       ✅ {first_date} - pobrano {len(first_day_prices)} godzin")
            
            # Kontynuuj dla pozostałych dni
            for day in range(2, last_day + 1):
                date_str = f"{year}-{month:02d}-{day:02d}"
                day_prices = scrape_tge_prices_from_pge(date_str, verbose=verbose)
                
                if day_prices is not None and not day_prices.empty:
                    all_prices.append(day_prices)
                    if day % 7 == 0:  # Progress co tydzień
                        print(f"       ✓ Pobrano {day}/{last_day} dni")
                else:
                    print(f"       ⚠️  Brak danych dla {date_str}")
                    # Nie przerywamy, może brakować jednego dnia, ale próbujemy dalej?
                    # Zwykle jak brakuje jednego, to może być problem z siecią.
                    # Ale w oryginalnym kodzie był break. Zostawmy break.
                    break
            
            # Jeśli udało się pobrać większość dni
            if len(all_prices) >= last_day * 0.8:  # Minimum 80% dni
                df_real = pd.concat(all_prices, ignore_index=True)
                df_real['timestamp_utc'] = df_real['timestamp_local'].dt.tz_convert('UTC')
                
                # ZAPIS DO CSV
                try:
                    csv_filename = f"tge_prices_{year}_{month:02d}.csv"
                    df_to_save = df_real.copy()
                    # Konwersja na naive UTC dla kompatybilności z load_tge_prices_from_csv
                    df_to_save['timestamp'] = df_to_save['timestamp_utc'].dt.tz_convert(None)
                    df_to_save['price_kwh'] = df_to_save['price_per_kwh_netto']
                    df_to_save[['timestamp', 'price_kwh']].to_csv(csv_filename, index=False)
                    print(f"       💾 Zapisano pobrane dane do pliku {csv_filename}")
                except Exception as e:
                    print(f"       ⚠️  Błąd zapisu do CSV: {e}")
                
                print(f"       ✅ Pobrano rzeczywiste ceny TGE dla {len(all_prices)}/{last_day} dni")
                return df_real[['timestamp_utc', 'timestamp_local', 'price_per_kwh_netto']]
        
        print(f"       ✗ Web scraping nieudany (brak Selenium lub błąd)")
        
        # METODA 3: Spróbuj pobrać z PSE
        print(f"    3. Próba pobrania danych z PSE...")
        pse_prices = scrape_tge_from_pse_website(year, month)
        if pse_prices is not None and not pse_prices.empty:
            print(f"       ✅ Pobrano dane z PSE")
            return pse_prices
        else:
            print(f"       ✗ Dane PSE niedostępne")
        
        # METODA 4: Użyj symulowanych danych
        print(f"    4. Używam danych symulowanych (wzorce rynkowe)")
        print(f"       💡 Aby użyć rzeczywistych cen:")
        print(f"          - Zainstaluj Selenium: pip install selenium webdriver-manager")
        print(f"          - Lub zapisz CSV jako: tge_prices_{year}_{month:02d}.csv")
        
        # Generuj godzinowe timestampy dla całego miesiąca
        start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        last_day = calendar.monthrange(year, month)[1]
        end = datetime(year, month, last_day, 23, 0, 0, tzinfo=timezone.utc)
        
        hours = []
        current = start
        while current <= end:
            hours.append(current)
            current += timedelta(hours=1)
        
        df = pd.DataFrame({'timestamp_utc': hours})
        df['timestamp_local'] = df['timestamp_utc'].dt.tz_convert('Europe/Warsaw')
        
        # Symuluj ceny bazując na rzeczywistych wzorcach z polskiego rynku energii
        # Wzorce cen RDN (zł/MWh) - bazowane na danych historycznych 2024:
        # - Noc (22-6): 200-400 zł/MWh
        # - Dzień (6-22): 350-650 zł/MWh  
        # - Szczyty (7-9, 17-20): 500-900 zł/MWh
        
        def simulate_tge_price(ts):
            hour = ts.hour
            day_of_week = ts.dayofweek
            
            # Bazowa cena zależy od pory doby
            if 0 <= hour < 6:  # Noc
                base = 300
                variance = 60
            elif 6 <= hour < 7:  # Ranek
                base = 450
                variance = 90
            elif 7 <= hour < 10:  # Poranny szczyt
                base = 700
                variance = 120
            elif 10 <= hour < 15:  # Dzień
                base = 500
                variance = 80
            elif 15 <= hour < 17:  # Popołudnie
                base = 550
                variance = 90
            elif 17 <= hour < 21:  # Wieczorny szczyt
                base = 750
                variance = 130
            elif 21 <= hour < 22:  # Późny wieczór
                base = 600
                variance = 100
            else:  # 22-24 - Noc
                base = 350
                variance = 70
            
            # Weekend - niższe ceny (60-75% cen z dni roboczych)
            if day_of_week >= 5:
                base *= 0.70
            
            # Dodaj losową zmienność (deterministyczną bazując na dniu miesiąca)
            variation = (hash(str(ts)) % 100 - 50) / 100 * variance
            price_mwh = base + variation
            
            # Konwertuj z zł/MWh na zł/kWh
            return price_mwh / 1000
        
        df['price_per_kwh_netto'] = df['timestamp_local'].apply(simulate_tge_price)
        
        return df[['timestamp_utc', 'timestamp_local', 'price_per_kwh_netto']]
        
    except Exception as e:
        print(f"❌ Błąd pobierania cen TGE: {e}")
        print(f"    Kontynuuję bez taryfy dynamicznej...")
        return None


def compute_dynamic_tariff_cost(hourly: pd.DataFrame, tge_prices: pd.DataFrame) -> Dict:
    """
    Oblicza koszt dla taryfy dynamicznej (giełdowej) PGE.
    
    Struktura ceny (oferta "Dynamiczna energia z PGE"):
    - Cena giełdowa TGE (zmienna co godzinę)
    - Marża sprzedawcy (szacowana ~0.15 zł/kWh)
    - Dystrybucja (według taryfy OSD)
    - Opłaty: OZE, kogeneracja
    - Opłata handlowa: 36,90 zł/msc brutto (29,98 zł/msc netto)
    - VAT 23%
    """
    if tge_prices is None or tge_prices.empty:
        return None
    
    # Połącz dane zużycia z cenami TGE
    hourly_merged = hourly.copy()
    hourly_merged = hourly_merged.merge(
        tge_prices[['timestamp_utc', 'price_per_kwh_netto']], 
        left_on='hour_utc', 
        right_on='timestamp_utc',
        how='left'
    )
    
    # Dla taryfy dynamicznej PGE:
    # Cena końcowa = cena_tge + marża + dystrybucja + OZE/kogeneracja
    
    # Średnia dystrybucja (przyjmujemy średnią ważoną z dystrybucji dziennej i nocnej)
    # W taryfie dynamicznej dystrybucja naliczana jest według standardowej taryfy G11/G12
    avg_distribution = (0.43360 + 0.10860) / 2  # 0.27110 zł/kWh
    
    # Całkowita cena za kWh
    hourly_merged['total_price'] = (
        hourly_merged['price_per_kwh_netto'] +  # Cena giełdowa TGE
        DYNAMIC_TARIFF_MARGIN +                  # Marża sprzedawcy
        avg_distribution +                        # Dystrybucja
        sum(ADDITIONAL_CHARGES.values())         # OZE + kogeneracja
    )
    
    # Koszt energii (netto)
    energy_cost = (hourly_merged['kwh'] * hourly_merged['total_price']).sum()
    
    # Opłaty stałe - w taryfie dynamicznej PGE:
    # - Opłata handlowa: 29,98 zł/msc netto (zamiast 12,48 w G11/G12)
    # - Pozostałe opłaty OSD (mocowa, stała, abonamentowa) jak w standardowej taryfie
    fixed_monthly = (
        DYNAMIC_TARIFF_FIXED_CHARGE +  # Opłata handlowa PGE Dynamiczna
        FIXED_CHARGES['mocowa'] +
        FIXED_CHARGES['stala'] +
        FIXED_CHARGES['abonamentowa'] +
        FIXED_CHARGES['przejsciowa']
    )
    
    # Suma netto
    total_netto = energy_cost + fixed_monthly
    
    # VAT
    vat = total_netto * VAT_RATE
    total_brutto = total_netto + vat
    
    # Statystyki cen TGE
    avg_tge_price = hourly_merged['price_per_kwh_netto'].mean()
    min_tge_price = hourly_merged['price_per_kwh_netto'].min()
    max_tge_price = hourly_merged['price_per_kwh_netto'].max()
    
    return {
        "taryfa": "Dynamiczna (TGE)",
        "koszt_energia_netto": float(energy_cost),
        "oplaty_stale": float(fixed_monthly),
        "oze_kogeneracja": 0.0,  # Już wliczone w cenę
        "suma_netto": float(total_netto),
        "vat_23": float(vat),
        "suma_brutto": float(total_brutto),
        "kWh": float(hourly_merged['kwh'].sum()),
        "avg_tge_price": float(avg_tge_price),
        "min_tge_price": float(min_tge_price),
        "max_tge_price": float(max_tge_price),
        "hourly_data": hourly_merged  # Dla wykresów
    }


# ----------------------------
# POMOCNICZE: SUPLA
# ----------------------------
def decode_supla_api_base_from_token(token: str) -> str:
    """
    SUPLA token ma postać: <random>.<base64url(api_base)>
    Wiki: druga część to base64-encoded URL docelowego API :contentReference[oaicite:5]{index=5}
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            raise ValueError("Token nie ma kropki – nie wygląda na token SUPLA z zakodowanym adresem API.")
        b64 = parts[1]
        # base64url -> base64 (uzupełnij padding)
        b64 += "=" * (-len(b64) % 4)
        api_base = base64.urlsafe_b64decode(b64.encode("utf-8")).decode("utf-8").strip()
        return api_base.rstrip("/")
    except Exception as e:
        raise RuntimeError(f"Nie udało się wyciągnąć adresu API z tokena: {e}")


def supla_request_get(url: str, token: str, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    return requests.get(url, headers=headers, timeout=60, **kwargs)


def download_measurement_logs_json(api_base: str, token: str, channel_id: int, date_from: datetime, date_to: datetime) -> list:
    """
    Endpoint w SUPLA: /channels/{channel}/measurement-logs zwraca JSON z pomiarami
    """
    # Generuj nazwę pliku cache na podstawie parametrów
    year = date_from.year
    month = date_from.month
    cache_filename = f"supla_logs_{channel_id}_{year}_{month:02d}.json"
    
    # Sprawdź czy plik cache istnieje
    if os.path.exists(cache_filename):
        print(f"📦 Wczytuję dane SUPLA z pliku cache: {cache_filename}")
        try:
            with open(cache_filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Błąd odczytu cache SUPLA: {e}. Pobieram z API...")
    
    print(f"📡 Pobieranie danych z API SUPLA...")
    url = f"{api_base}/api/v3/channels/{channel_id}/measurement-logs"
    params = {
        "dateFrom": date_from.isoformat(),
        "dateTo": date_to.isoformat(),
    }
    r = supla_request_get(url, token, params=params)
    if r.status_code != 200:
        raise RuntimeError(f"Nie udało się pobrać logów: HTTP {r.status_code}\n{r.text[:1000]}")
    
    data = r.json()
    
    # Zapisz do cache
    try:
        with open(cache_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"💾 Zapisano dane SUPLA do pliku: {cache_filename}")
    except Exception as e:
        print(f"⚠️  Błąd zapisu cache SUPLA: {e}")
    
    return data


def parse_json_to_dataframe(data: list) -> pd.DataFrame:
    """
    Parsuje JSON z API SUPLA do DataFrame.
    Dane zawierają kumulatywne odczyty energii (FAE - Forward Active Energy) w setnych Wh (0.01 Wh).
    """
    if not data:
        raise RuntimeError("API zwróciło pustą listę pomiarów")
    
    return pd.DataFrame(data)


# ----------------------------
# STREFY PGE (PGE Dystrybucja)
# ----------------------------
@dataclass(frozen=True)
class TimeWindows:
    # list of (start_hour, end_hour) w formacie [start, end) w godzinach 0-24
    windows: Tuple[Tuple[int, int], ...]

    def contains(self, hour: int) -> bool:
        for a, b in self.windows:
            if a <= hour < b:
                return True
        return False


def pge_g12_windows(month: int, supports_summer_winter: bool) -> Tuple[TimeWindows, TimeWindows]:
    """
    Definicja stref czasowych dla taryfy G12 (standardowa dwustrefowa):
    
    Strefa tańsza (noc/pozaszczyt):
    - Zima (1.10-31.03): 13:00-15:00 i 22:00-6:00.
    - Lato (1.04-30.09): 15:00-17:00 i 22:00-6:00.
    
    Strefa droższa (szczyt):
    - Pozostałe godziny (np. 6:00-13:00, 15:00-22:00 zimą).
    
    Weekendy w G12: Rozliczane jak dni robocze.
    """
    if not supports_summer_winter:
        day = TimeWindows(((6, 13), (15, 22)))
        night = TimeWindows(((13, 15), (22, 24), (0, 6)))
        return day, night

    # LATO wg PGE: 1 kwietnia–30 września :contentReference[oaicite:8]{index=8}
    is_summer = 4 <= month <= 9
    if is_summer:
        day = TimeWindows(((6, 15), (17, 22)))
        night = TimeWindows(((15, 17), (22, 24), (0, 6)))
    else:
        day = TimeWindows(((6, 13), (15, 22)))
        night = TimeWindows(((13, 15), (22, 24), (0, 6)))
    return day, night


def is_weekend_or_holiday(ts_local: pd.Timestamp) -> bool:
    if ts_local.weekday() >= 5:  # sobota=5, niedziela=6
        return True
    if not USE_POLISH_HOLIDAYS:
        return False
    try:
        import holidays
        pl_holidays = holidays.Poland(years=[ts_local.year])
        return ts_local.date() in pl_holidays
    except Exception:
        # jeśli nie ma biblioteki holidays – traktuj tylko weekend
        return False


def is_sunday_or_holiday(ts_local: pd.Timestamp) -> bool:
    if ts_local.weekday() == 6:  # niedziela=6
        return True
    if not USE_POLISH_HOLIDAYS:
        return False
    try:
        import holidays
        pl_holidays = holidays.Poland(years=[ts_local.year])
        return ts_local.date() in pl_holidays
    except Exception:
        return False


def classify_zone(ts_local: pd.Timestamp, tariff: str, supports_summer_winter: bool) -> str:
    h = ts_local.hour
    if tariff == "G11":
        return "all"

    day_w, night_w = pge_g12_windows(ts_local.month, supports_summer_winter)

    if tariff == "G12":
        return "night" if night_w.contains(h) else "day"

    if tariff == "G12w":
        # Taryfa G12w (weekendowa)
        # Strefa tańsza (noc/pozaszczyt):
        # - Dni robocze: Takie same jak w G12.
        # - Soboty, niedziele i święta: Cała doba (24/7) jest w tańszej strefie.
        if is_weekend_or_holiday(ts_local):
            return "night"
        return "night" if night_w.contains(h) else "day"

    if tariff == "G12n":
        # G12n (Niedzielna)
        # Niedziele i święta: Cała doba w strefie nocnej (S2)
        # Dni powszednie (Pn-Sob):
        # - Dzień (S1): 05:00 - 01:00
        # - Noc (S2): 01:00 - 05:00
        if is_sunday_or_holiday(ts_local):
            return "night"
        
        # Pn-Sob
        if 1 <= h < 5:
            return "night"
        else:
            return "day"

    raise ValueError(f"Nieznana taryfa: {tariff}")


# ----------------------------
# GŁÓWNA ANALIZA
# ----------------------------
def month_range_utc(year: int, month: int) -> Tuple[datetime, datetime]:
    start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


def normalize_logs_to_hourly_kwh(df_raw: pd.DataFrame, start_date: datetime = None, end_date: datetime = None) -> pd.DataFrame:
    """
    Konwertuje dane z API SUPLA na godzinowy bilans energii w kWh.
    
    API zwraca kumulatywne odczyty energii (FAE - Forward Active Energy) w setnych Wh (0.01 Wh).
    Funkcja oblicza różnice między kolejnymi odczytami, co daje faktyczne zużycie (bilans godzinowy).
    """
    df = df_raw.copy()
    
    # Konwertuj timestamp na datetime UTC
    df['ts_utc'] = pd.to_datetime(df['date_timestamp'], unit='s', utc=True)
    df = df.sort_values('ts_utc')
    
    # Filtruj dane do podanego zakresu dat
    if start_date is not None:
        df = df[df['ts_utc'] >= start_date]
    if end_date is not None:
        df = df[df['ts_utc'] <= end_date]
    
    # Użyj fae_balanced (suma energii ze wszystkich faz)
    if 'fae_balanced' not in df.columns:
        raise RuntimeError(f"Brak kolumny fae_balanced. Dostępne kolumny: {list(df.columns)}")
    
    df['total_wh'] = df['fae_balanced']
    
    # Konwertuj z setnych Wh (0.01 Wh) na kWh
    # API SUPLA zwraca wartości w setnych Wh, więc dzielimy przez 100000 (100 * 1000)
    df['total_kwh'] = df['total_wh'] / 100000.0
    
    # Oblicz różnicę (bilans/zużycie) między kolejnymi pomiarami
    # To daje faktyczne zużycie energii między pomiarami
    df['kwh_consumed'] = df['total_kwh'].diff()
    
    # Usuń pierwszy wiersz (diff daje NaN) i ujemne wartości (reset licznika)
    df = df[df['kwh_consumed'] > 0]
    
    # Agreguj do godzin (sumuj zużycie w ramach każdej godziny)
    df['hour_utc'] = df['ts_utc'].dt.floor('h')
    hourly = df.groupby('hour_utc', as_index=False)['kwh_consumed'].sum()
    hourly = hourly.rename(columns={'kwh_consumed': 'kwh'})
    
    return hourly



def compute_costs(hourly: pd.DataFrame, prices: Dict[str, Dict[str, float]], supports_summer_winter: bool) -> pd.DataFrame:
    # Do stref potrzebujemy czasu lokalnego PL (Europe/Warsaw)
    hourly = hourly.copy()
    hourly["hour_local"] = hourly["hour_utc"].dt.tz_convert("Europe/Warsaw")

    total_kwh = float(hourly["kwh"].sum())
    
    # Opłaty stałe miesięczne (netto)
    fixed_monthly = sum(FIXED_CHARGES.values())
    
    # Dodatkowe opłaty (OZE + kogeneracja) - zależne od zużycia
    additional_per_kwh = sum(ADDITIONAL_CHARGES.values())
    additional_cost = total_kwh * additional_per_kwh

    results = []
    for tariff in prices.keys():
        zones = hourly["hour_local"].apply(lambda ts: classify_zone(ts, tariff, supports_summer_winter))
        p = zones.map(lambda z: prices[tariff][z])
        
        # Koszt energii + dystrybucji zmiennej (netto)
        energy_cost = (hourly["kwh"] * p).sum()
        
        # Suma netto
        total_netto = energy_cost + fixed_monthly + additional_cost
        
        # VAT 23%
        vat = total_netto * VAT_RATE
        total_brutto = total_netto + vat
        
        results.append({
            "taryfa": tariff, 
            "koszt_energia_netto": float(energy_cost),
            "oplaty_stale": float(fixed_monthly),
            "oze_kogeneracja": float(additional_cost),
            "suma_netto": float(total_netto),
            "vat_23": float(vat),
            "suma_brutto": float(total_brutto),
            "kWh": total_kwh
        })

    res = pd.DataFrame(results).sort_values("suma_brutto")
    res["roznica_do_najtanszej_zl"] = res["suma_brutto"] - res["suma_brutto"].min()
    return res


def create_visualizations(hourly: pd.DataFrame, res: pd.DataFrame, year: int, month: int, dynamic_result: Dict = None):
    """Tworzy wykresy wizualizujące wyniki analizy."""
    
    # Ustaw styl wykresów
    plt.style.use('seaborn-v0_8-darkgrid')
    fig = plt.figure(figsize=(16, 10))
    
    # 1. Wykres słupkowy kosztów dla różnych taryf
    ax1 = plt.subplot(2, 3, 1)
    
    # Dodaj taryfa dynamiczną do porównania jeśli dostępna
    tariffs_to_plot = res.copy()
    if dynamic_result:
        dynamic_row = pd.DataFrame([{
            'taryfa': 'Dynamiczna',
            'suma_brutto': dynamic_result['suma_brutto'],
            'kWh': dynamic_result['kWh']
        }])
        tariffs_to_plot = pd.concat([tariffs_to_plot, dynamic_row], ignore_index=True)
    
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c', '#34495e']
    bars = ax1.bar(tariffs_to_plot['taryfa'], tariffs_to_plot['suma_brutto'], color=colors[:len(tariffs_to_plot)])
    ax1.set_ylabel('Koszt brutto (zł)', fontsize=11, fontweight='bold')
    ax1.set_title(f'Porównanie kosztów taryf\n{year}-{month:02d}', fontsize=12, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=15, ha='right')
    
    # Dodaj wartości na słupkach
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f} zł', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    # 2. Wykres struktury kosztów dla najtańszej taryfy
    ax2 = plt.subplot(2, 3, 2)
    best = res.iloc[0]
    costs = [best['koszt_energia_netto'], best['oplaty_stale'], 
             best['oze_kogeneracja'], best['vat_23']]
    labels = ['Energia +\nDystrybucja', 'Opłaty\nstałe', 'OZE +\nKogeneracja', 'VAT 23%']
    colors_pie = ['#3498db', '#e67e22', '#9b59b6', '#95a5a6']
    
    wedges, texts, autotexts = ax2.pie(costs, labels=labels, autopct='%1.1f%%',
                                        colors=colors_pie, startangle=90)
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(10)
    ax2.set_title(f'Struktura kosztów - {best["taryfa"]}\n({best["suma_brutto"]:.2f} zł)', 
                  fontsize=12, fontweight='bold')
    
    # 3. Ceny TGE (jeśli dostępne) vs zużycie
    ax3 = plt.subplot(2, 3, 3)
    
    if dynamic_result and 'hourly_data' in dynamic_result:
        tge_data = dynamic_result['hourly_data']
        tge_data_local = tge_data.copy()
        tge_data_local['hour_local'] = tge_data_local['hour_utc'].dt.tz_convert('Europe/Warsaw')
        
        # Dwie osie Y
        ax3_twin = ax3.twinx()
        
        # Ceny TGE (linia)
        ax3.plot(tge_data_local['hour_local'], tge_data_local['price_per_kwh_netto'], 
                 color='#e74c3c', linewidth=2, alpha=0.8, label='Cena TGE')
        ax3.set_ylabel('Cena TGE (zł/kWh)', fontsize=11, fontweight='bold', color='#e74c3c')
        ax3.tick_params(axis='y', labelcolor='#e74c3c')
        
        # Zużycie (słupki)
        ax3_twin.bar(tge_data_local['hour_local'], tge_data_local['kwh'], 
                     alpha=0.3, color='#3498db', width=0.03, label='Zużycie')
        ax3_twin.set_ylabel('Zużycie (kWh)', fontsize=11, fontweight='bold', color='#3498db')
        ax3_twin.tick_params(axis='y', labelcolor='#3498db')
        
        ax3.set_xlabel('Data', fontsize=11, fontweight='bold')
        ax3.set_title('Ceny TGE vs Zużycie energii', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
    else:
        # Jeśli nie ma danych TGE, pokaż zwykłe zużycie
        hourly_local = hourly.copy()
        hourly_local['hour_local'] = hourly_local['hour_utc'].dt.tz_convert('Europe/Warsaw')
        
        ax3.plot(hourly_local['hour_local'], hourly_local['kwh'], 
                 color='#3498db', linewidth=1.5, alpha=0.7)
        ax3.fill_between(hourly_local['hour_local'], hourly_local['kwh'], 
                          alpha=0.3, color='#3498db')
        ax3.set_ylabel('Zużycie (kWh)', fontsize=11, fontweight='bold')
        ax3.set_xlabel('Data', fontsize=11, fontweight='bold')
        ax3.set_title('Zużycie energii w czasie', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)
    
    # 4. Histogram zużycia godzinowego - rozkład według godziny doby
    ax4 = plt.subplot(2, 3, 4)
    hourly_local = hourly.copy()
    hourly_local['hour_local'] = hourly_local['hour_utc'].dt.tz_convert('Europe/Warsaw')
    hourly_local['hour_of_day'] = hourly_local['hour_local'].dt.hour
    
    # Agreguj zużycie według godziny doby (0-23)
    hourly_avg = hourly_local.groupby('hour_of_day')['kwh'].mean().sort_index()
    
    bars = ax4.bar(hourly_avg.index, hourly_avg.values, color='#2ecc71', alpha=0.7, edgecolor='black')
    ax4.set_xlabel('Godzina doby', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Średnie zużycie (kWh)', fontsize=11, fontweight='bold')
    ax4.set_title('Średnie zużycie według godziny doby', fontsize=12, fontweight='bold')
    ax4.set_xticks(range(0, 24, 2))
    ax4.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)], rotation=45)
    ax4.grid(axis='y', alpha=0.3)
    
    # Zaznacz strefy G12 (noc na czerwono, dzień na zielono)
    for i, bar in enumerate(bars):
        hour = hourly_avg.index[i]
        # Strefa nocna: 13-15 i 22-6
        if (13 <= hour < 15) or (hour >= 22) or (hour < 6):
            bar.set_color('#e74c3c')  # czerwony dla nocy
            bar.set_alpha(0.7)
    
    # 5. Analiza stref czasowych (G12 vs G12w)
    ax5 = plt.subplot(2, 3, 5)
    
    # Oblicz statystyki dla G12
    hourly_local['zone_g12'] = hourly_local['hour_local'].apply(
        lambda ts: classify_zone(ts, 'G12', METER_SUPPORTS_SUMMER_WINTER))
    stats_g12 = hourly_local.groupby('zone_g12')['kwh'].agg(['sum', 'count'])
    
    # Oblicz statystyki dla G12w
    hourly_local['zone_g12w'] = hourly_local['hour_local'].apply(
        lambda ts: classify_zone(ts, 'G12w', METER_SUPPORTS_SUMMER_WINTER))
    stats_g12w = hourly_local.groupby('zone_g12w')['kwh'].agg(['sum', 'count'])
    
    # Przygotuj dane do wykresu
    categories = ['G12 Dzień', 'G12 Noc', 'G12w Dzień', 'G12w Noc']
    
    def get_stat(stats, zone, col):
        return stats.loc[zone, col] if zone in stats.index else 0
        
    hours_data = [
        get_stat(stats_g12, 'day', 'count'),
        get_stat(stats_g12, 'night', 'count'),
        get_stat(stats_g12w, 'day', 'count'),
        get_stat(stats_g12w, 'night', 'count')
    ]
    
    kwh_data = [
        get_stat(stats_g12, 'day', 'sum'),
        get_stat(stats_g12, 'night', 'sum'),
        get_stat(stats_g12w, 'day', 'sum'),
        get_stat(stats_g12w, 'night', 'sum')
    ]
    
    x = np.arange(len(categories))
    width = 0.35
    
    # Słupki godzin (lewa oś)
    bars1 = ax5.bar(x - width/2, hours_data, width, label='Liczba godzin', color='#3498db', alpha=0.8)
    ax5.set_ylabel('Liczba godzin', fontsize=10, fontweight='bold', color='#3498db')
    ax5.tick_params(axis='y', labelcolor='#3498db')
    
    # Słupki zużycia (prawa oś)
    ax5_twin = ax5.twinx()
    bars2 = ax5_twin.bar(x + width/2, kwh_data, width, label='Zużycie (kWh)', color='#e74c3c', alpha=0.8)
    ax5_twin.set_ylabel('Zużycie (kWh)', fontsize=10, fontweight='bold', color='#e74c3c')
    ax5_twin.tick_params(axis='y', labelcolor='#e74c3c')
    
    ax5.set_title('Porównanie stref: G12 vs G12w', fontsize=12, fontweight='bold')
    ax5.set_xticks(x)
    ax5.set_xticklabels(categories, rotation=15, ha='right', fontsize=9)
    ax5.grid(axis='y', alpha=0.3)
    
    # Dodaj wartości na słupkach
    for bar in bars1:
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}h', ha='center', va='bottom', fontsize=8, fontweight='bold')
    for bar in bars2:
        height = bar.get_height()
        ax5_twin.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}', ha='center', va='bottom', fontsize=8, fontweight='bold')
    
    # 6. Statystyki tekstowe
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')
    
    if dynamic_result:
        stats_text = f"""
    STATYSTYKI {year}-{month:02d}
    
    Zużycie energii:
       • Całkowite: {hourly['kwh'].sum():.2f} kWh
       • Średnie godz.: {hourly['kwh'].mean():.3f} kWh
       • Max godz.: {hourly['kwh'].max():.3f} kWh
       • Min godz.: {hourly['kwh'].min():.3f} kWh
    
    Strefy G12:
       • Dzień: {get_stat(stats_g12, 'day', 'count'):.0f}h ({get_stat(stats_g12, 'day', 'sum'):.1f} kWh)
       • Noc: {get_stat(stats_g12, 'night', 'count'):.0f}h ({get_stat(stats_g12, 'night', 'sum'):.1f} kWh)
    
    Porównanie kosztów:
       • Najtańsza: {res.iloc[0]['taryfa']} ({res.iloc[0]['suma_brutto']:.2f} zł)
       • Dynamiczna (TGE): {dynamic_result['suma_brutto']:.2f} zł
       • Różnica: {abs(dynamic_result['suma_brutto'] - res.iloc[0]['suma_brutto']):.2f} zł
    
    Ceny TGE:
       • Średnia: {dynamic_result['avg_tge_price']:.4f} zł/kWh
       • Min: {dynamic_result['min_tge_price']:.4f} zł/kWh
       • Max: {dynamic_result['max_tge_price']:.4f} zł/kWh
    """
    else:
        stats_text = f"""
    STATYSTYKI {year}-{month:02d}
    
    Zużycie energii:
       • Całkowite: {hourly['kwh'].sum():.2f} kWh
       • Średnie godz.: {hourly['kwh'].mean():.3f} kWh
       • Max godz.: {hourly['kwh'].max():.3f} kWh
       • Min godz.: {hourly['kwh'].min():.3f} kWh
    
    Strefy G12:
       • Dzień: {get_stat(stats_g12, 'day', 'count'):.0f}h ({get_stat(stats_g12, 'day', 'sum'):.1f} kWh)
       • Noc: {get_stat(stats_g12, 'night', 'count'):.0f}h ({get_stat(stats_g12, 'night', 'sum'):.1f} kWh)
    
    Oszczędności:
       • G12w vs G12: {res.iloc[1]['roznica_do_najtanszej_zl']:.2f} zł
       • G12w vs G11: {res.iloc[2]['roznica_do_najtanszej_zl']:.2f} zł
    
    Najtańsza: {res.iloc[0]['taryfa']} ({res.iloc[0]['suma_brutto']:.2f} zł)
    """
    
    ax6.text(0.1, 0.95, stats_text, transform=ax6.transAxes,
             fontsize=11, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))
    
    plt.tight_layout()
    filename = f'analiza_energii_{year}_{month:02d}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n✅ Zapisano wykres: {filename}")
    plt.show()


def main():
    api_base = decode_supla_api_base_from_token(SUPLA_TOKEN)
    start_utc, end_utc = month_range_utc(YEAR, MONTH)

    json_data = download_measurement_logs_json(api_base, SUPLA_TOKEN, CHANNEL_ID, start_utc, end_utc)
    df_raw = parse_json_to_dataframe(json_data)
    
    # Przefiltruj dane do żądanego miesiąca i oblicz bilans godzinowy
    hourly = normalize_logs_to_hourly_kwh(df_raw, start_utc, end_utc)

    # Oblicz koszty dla standardowych taryf
    res = compute_costs(hourly, PRICES, METER_SUPPORTS_SUMMER_WINTER)
    
    # Pobierz ceny TGE i oblicz koszt dla taryfy dynamicznej
    tge_prices = fetch_tge_prices(YEAR, MONTH, verbose=False)
    dynamic_result = None
    if tge_prices is not None:
        dynamic_result = compute_dynamic_tariff_cost(hourly, tge_prices)
    
    print(f"\n{'='*60}")
    print(f"  ANALIZA TARYF ENERGII ELEKTRYCZNEJ - {YEAR}-{MONTH:02d}")
    print(f"{'='*60}\n")
    print(f"📊 Liczba godzin z danymi: {len(hourly)}")
    print(f"⚡ Całkowite zużycie: {hourly['kwh'].sum():.2f} kWh\n")
    print(f"{'─'*60}")
    print(f"  PORÓWNANIE TARYF")
    print(f"{'─'*60}\n")
    print(res[["taryfa", "suma_brutto", "kWh", "roznica_do_najtanszej_zl"]].to_string(index=False))
    
    if dynamic_result:
        print(f"\n{'─'*60}")
        print(f"  TARYFA DYNAMICZNA (GIEŁDOWA TGE)")
        print(f"{'─'*60}\n")
        print(f"  💰 Suma brutto:                    {dynamic_result['suma_brutto']:>8.2f} zł")
        print(f"  📊 Średnia cena TGE:               {dynamic_result['avg_tge_price']:>8.4f} zł/kWh")
        print(f"  📉 Min cena TGE:                   {dynamic_result['min_tge_price']:>8.4f} zł/kWh")
        print(f"  📈 Max cena TGE:                   {dynamic_result['max_tge_price']:>8.4f} zł/kWh")
        print(f"  🔧 Marża sprzedawcy:               {DYNAMIC_TARIFF_MARGIN:>8.4f} zł/kWh")
        
        diff = dynamic_result['suma_brutto'] - res.iloc[0]['suma_brutto']
        if diff > 0:
            print(f"  ⚠️  Droższa o:                      {diff:>8.2f} zł vs {res.iloc[0]['taryfa']}")
        else:
            print(f"  ✅ Tańsza o:                       {-diff:>8.2f} zł vs {res.iloc[0]['taryfa']}")
    
    print(f"\n{'─'*60}")
    print(f"  SZCZEGÓŁY NAJTAŃSZEJ TARYFY: {res.iloc[0]['taryfa']}")
    print(f"{'─'*60}\n")
    print(f"  💡 Energia + dystrybucja (netto): {res.iloc[0]['koszt_energia_netto']:>8.2f} zł")
    print(f"  📋 Opłaty stałe:                  {res.iloc[0]['oplaty_stale']:>8.2f} zł")
    print(f"  🌱 OZE + kogeneracja:             {res.iloc[0]['oze_kogeneracja']:>8.2f} zł")
    print(f"  {'─'*56}")
    print(f"  💵 Suma netto:                     {res.iloc[0]['suma_netto']:>8.2f} zł")
    print(f"  🧾 VAT 23%:                        {res.iloc[0]['vat_23']:>8.2f} zł")
    print(f"  {'─'*56}")
    print(f"  💰 SUMA BRUTTO:                    {res.iloc[0]['suma_brutto']:>8.2f} zł")
    print(f"\n{'='*60}\n")
    
    # Generuj wykresy
    create_visualizations(hourly, res, YEAR, MONTH, dynamic_result)


if __name__ == "__main__":
    main()
