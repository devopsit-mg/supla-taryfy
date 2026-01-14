# Analiza Kosztów Energii (Supla + PGE/TGE)

Skrypt służy do analizy kosztów energii elektrycznej na podstawie danych zużycia z licznika w systemie SUPLA oraz cen energii, w tym cen dynamicznych z Rynku Dnia Następnego (TGE).

## Funkcjonalności

*   **Pobieranie danych z SUPLA**: Automatyczne pobieranie logów zużycia energii z API SUPLA.
*   **Scraping cen TGE**: Pobieranie godzinowych cen energii z Rynku Dnia Następnego ze strony PGE (używając Selenium).
*   **Caching danych**:
    *   Logi SUPLA zapisywane są do plików JSON (`supla_logs_...`).
    *   Ceny TGE zapisywane są do plików CSV (`tge_prices_...`).
*   **Analiza taryf**: Porównanie kosztów dla taryf:
    *   **G11** (stała stawka całą dobę)
    *   **G12** (strefa dzienna i nocna)
    *   **G12w** (strefa weekendowa)
    *   **Taryfa Dynamiczna** (ceny godzinowe TGE + marża i opłaty)
*   **Wizualizacja**: Generowanie wykresów (`analiza_energii_YYYY_MM.png`) przedstawiających:
    *   Porównanie kosztów całkowitych.
    *   Strukturę kosztów.
    *   Profil zużycia na tle cen giełdowych.
    *   Średnie zużycie godzinowe.
    *   Analizę stref czasowych (G12 vs G12w).

## Wymagania

*   Python 3.8+
*   Przeglądarka Google Chrome (do scrapowania danych przez Selenium)

## Dla początkujących

### 1. Jak uzyskać token SUPLA?

1. Zaloguj się na swoje konto w [SUPLA Cloud](https://cloud.supla.org/).
2. W menu wejdź w **Integracje** -> **API (OAuth)**.
3. Kliknij **Utwórz nowy token**.
4. Zaznacz uprawnienia do odczytu kanałów (Channel read) oraz odczytu historii pomiarów (Log read).
5. Skopiuj wygenerowany token. Będziesz go musiał wkleić w pliku `supla_config.py` w polu `SUPLA_TOKEN`.

### 2. ID kanału

1. W SUPLA Cloud przejdź do listy urządzeń.
2. Kliknij na swój licznik energii.
3. ID kanału znajdziesz w adresie przeglądarki lub w szczegółach urządzenia (np. "ID: 12345").

## Instalacja

1.  Sklonuj repozytorium lub pobierz pliki.
2.  Zainstaluj wymagane biblioteki Python:

    ```bash
    pip install -r requirements.txt
    ```

## Konfiguracja

Otwórz plik `supla_config.py` i dostosuj ustawienia:

```python
SUPLA_TOKEN = "TWOJ_TOKEN_SUPLA"   # Token dostępu do API SUPLA
CHANNEL_ID = 12345                 # ID kanału licznika energii w SUPLA
YEAR = 2025                        # Rok do analizy
MONTH = 12                         # Miesiąc do analizy
USE_POLISH_HOLIDAYS = True         # Czy uwzględniać święta w taryfie G12w
```

Możesz również dostosować ceny energii w słowniku `PRICES` oraz opłaty stałe w `FIXED_CHARGES`, jeśli ulegną zmianie.

## Uruchomienie

Uruchom skrypt poleceniem:

```bash
python3 supla_pge_for.py
```

Skrypt:
1.  Pobierze (lub wczyta z cache) dane o zużyciu z SUPLA.
2.  Pobierze (lub wczyta z cache) ceny TGE dla wybranego miesiąca.
3.  Przeliczy koszty dla wszystkich zdefiniowanych taryf.
4.  Wyświetli podsumowanie w terminalu.
5.  Wygeneruje plik z wykresami (np. `analiza_energii_2025_12.png`).

## Uwagi

*   Pierwsze uruchomienie dla danego miesiąca może potrwać dłużej ze względu na konieczność pobrania danych ze strony PGE (scraping każdego dnia miesiąca). Kolejne uruchomienia będą korzystać z zapisanego pliku CSV.
*   Upewnij się, że masz zainstalowaną przeglądarkę Chrome, aby Selenium mogło działać.

## ⚠️ DISCLAIMER - WYŁĄCZENIE ODPOWIEDZIALNOŚCI

**PRZECZYTAJ UWAŻNIE PRZED UŻYCIEM**

1. **Brak gwarancji**: To oprogramowanie jest dostarczane "TAKIE JAKIE JEST" bez jakichkolwiek gwarancji, ani wyraźnych, ani dorozumianych, w tym między innymi gwarancji przydatności handlowej, przydatności do określonego celu oraz nienaruszania praw.

2. **Tylko cele informacyjne**: Narzędzie służy wyłącznie celom edukacyjnym i informacyjnym. NIE jest certyfikowanym narzędziem do rozliczeń energii elektrycznej.

3. **Dokładność obliczeń**: Obliczenia mogą zawierać błędy wynikające z:
   - Nieprawidłowych/nieaktualnych danych o cenach energii
   - Błędów w algorytmach klasyfikacji stref taryfowych
   - Zmian w regulacjach prawnych i taryfach
   - Różnic regionalnych w taryfikacji
   - Błędów w odczycie danych z licznika

4. **Nie podstawa do rozliczeń**: NIGDY nie używaj tego narzędzia jako jedynej podstawy do:
   - Oficjalnych rozliczeń z dostawcą energii
   - Decyzji finansowych lub inwestycyjnych
   - Reklamacji lub sporów prawnych
   - Porad dla osób trzecich w celach komercyjnych

5. **Wyłączenie odpowiedzialności**: Autorzy, współtwórcy i dystrybutorzy tego oprogramowania NIE ponoszą odpowiedzialności za:
   - Jakiekolwiek szkody (bezpośrednie, pośrednie, przypadkowe, szczególne, następcze)
   - Straty finansowe wynikłe z użycia lub niemożności użycia oprogramowania
   - Błędne decyzje podjęte na podstawie wyników z tego narzędzia
   - Utratę danych, przychodu, zysku lub oszczędności

6. **Weryfikacja wyników**: Użytkownik jest WYŁĄCZNIE odpowiedzialny za weryfikację wszystkich wyników z oficjalnymi źródłami (faktury, taryfy operatorów, przepisy prawne).

7. **Ryzyko użytkowania**: Używając tego oprogramowania, akceptujesz pełne ryzyko związane z jego użytkowaniem.

**Korzystając z tego oprogramowania, potwierdzasz, że przeczytałeś/-aś i zrozumiałeś/-aś powyższe ostrzeżenia oraz akceptujesz wszystkie związane z tym ryzyka.**

## Licencja

Ten projekt jest udostępniony na licencji Apache 2.0. Zobacz plik [LICENSE](LICENSE) po więcej szczegółów.
