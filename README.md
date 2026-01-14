# Analiza Kosztów Energii (SUPLA + PGE/TGE)

Skrypt do analizy kosztów energii elektrycznej na podstawie danych zużycia z licznika w systemie SUPLA oraz cen energii, w tym cen dynamicznych z Rynku Dnia Następnego (TGE).

## 📋 Spis treści

- [Funkcjonalności](#funkcjonalności)
- [Wymagania](#wymagania)
- [Instalacja](#instalacja)
- [Konfiguracja](#konfiguracja)
- [Uruchomienie](#uruchomienie)
- [Struktura projektu](#struktura-projektu)
- [Uwagi](#uwagi)
- [Disclaimer](#️-disclaimer---wyłączenie-odpowiedzialności)
- [Licencja](#licencja)

## ✨ Funkcjonalności

*   **Pobieranie danych z SUPLA**: Automatyczne pobieranie logów zużycia energii z API SUPLA.
*   **Scraping cen TGE**: Pobieranie godzinowych cen energii z Rynku Dnia Następnego ze strony PGE (używając Selenium).
*   **Caching danych**:
    *   Logi SUPLA zapisywane są do `data/supla_logs_*.json`
    *   Ceny TGE zapisywane są do `data/tge_prices_*.csv`
*   **Analiza taryf**: Porównanie kosztów dla taryf:
    *   **G11** (stała stawka całą dobę)
    *   **G12** (strefa dzienna i nocna)
    *   **G12w** (strefa weekendowa)
    *   **G12n** (strefa niedzielna)
    *   **Taryfa Dynamiczna** (ceny godzinowe TGE + marża i opłaty)
*   **Wizualizacja**: Generowanie wykresów w `output/analiza_energii_YYYY_MM.png`:
    *   Porównanie kosztów całkowitych
    *   Struktura kosztów
    *   Profil zużycia na tle cen giełdowych
    *   Średnie zużycie godzinowe
    *   Analiza stref czasowych (G12 vs G12w)

## 📦 Wymagania

*   Python 3.8+
*   Przeglądarka Google Chrome (do scrapowania danych przez Selenium)
*   Konto SUPLA Cloud z licznikiem energii

## 🚀 Instalacja

### 1. Sklonuj repozytorium

```bash
git clone https://github.com/devopsit-mg/supla-taryfy.git
cd supla-taryfy
```

### 2. Zainstaluj zależności Python

```bash
pip install -r requirements.txt
```

### 3. Utwórz katalogi (jeśli nie istnieją)

```bash
mkdir -p data output
```

## ⚙️ Konfiguracja

### Krok 1: Uzyskaj token SUPLA

1. Zaloguj się na swoje konto w [SUPLA Cloud](https://cloud.supla.org/)
2. Przejdź do: **Konto** → **Bezpieczeństwo** → **Osobiste Tokeny Dostępowe**
   - Bezpośredni link: [https://cloud.supla.org/security/personal-access-tokens](https://cloud.supla.org/security/personal-access-tokens)
3. Kliknij **"Generuj nowy token"**
4. Zaznacz uprawnienia:
   - ✅ **Kanały** (odczyt danych z urządzeń)
   - ✅ **Historia pomiarów** (odczyt logów zużycia energii)
5. Kliknij **"Generuj"** i skopiuj wygenerowany token

### Krok 2: Znajdź ID kanału

1. W SUPLA Cloud przejdź do listy urządzeń
2. Kliknij na swój licznik energii
3. ID kanału znajdziesz w adresie URL przeglądarki (np. `/channels/12345`)

### Krok 3: Utwórz plik konfiguracyjny

```bash
cp src/supla_config.example.py src/supla_config.py
```

Następnie edytuj plik `src/supla_config.py` i uzupełnij:

```python
SUPLA_TOKEN = "TWOJ_TOKEN_Z_SUPLA_CLOUD"
CHANNEL_ID = 12345  # Twoje ID kanału
YEAR = 2026
MONTH = 1
```

### Krok 4: Dostosuj ceny (opcjonalnie)

W pliku `src/supla_config.py` możesz zaktualizować ceny energii i opłaty zgodnie z Twoją fakturą:

```python
PRICES = {
    "G11": {"all": 0.5000 + 0.43360},
    "G12": {
        "day": 0.5656 + 0.43360,
        "night": 0.3718 + 0.10860
    },
    # ... itd.
}
```

## ▶️ Uruchomienie

```bash
cd src
python supla_pge.py
```

### Co robi skrypt?

1.  Pobiera (lub wczyta z cache) dane o zużyciu z SUPLA
2.  Pobiera (lub wczyta z cache) ceny TGE dla wybranego miesiąca
3.  Przelicza koszty dla wszystkich zdefiniowanych taryf
4.  Wyświetla podsumowanie w terminalu
5.  Generuje wykresy w katalogu `output/`

### Przykładowy wynik w terminalu

```
============================================================
  ANALIZA TARYF ENERGII ELEKTRYCZNEJ - 2025-12
============================================================

📊 Liczba godzin z danymi: 744
⚡ Całkowite zużycie: 234.56 kWh

────────────────────────────────────────────────────────────
  PORÓWNANIE TARYF
────────────────────────────────────────────────────────────

  taryfa  suma_brutto    kWh  roznica_do_najtanszej_zl
    G12w       256.78  234.56                      0.00
     G12       267.34  234.56                     10.56
    G12n       272.45  234.56                     15.67
     G11       289.12  234.56                     32.34
```

## 📁 Struktura projektu

```
supla-taryfy/
├── src/                              # Kod źródłowy
│   ├── supla_pge.py                 # Główny skrypt analizy
│   ├── supla_config.example.py      # Przykładowy plik konfiguracji
│   └── supla_config.py              # Twoja konfiguracja (git ignore)
├── data/                             # Dane cache (git ignore)
│   ├── supla_logs_*.json            # Cache logów SUPLA
│   ├── tge_prices_*.csv             # Cache cen TGE
│   └── .gitkeep
├── output/                           # Wyniki analiz (git ignore)
│   ├── analiza_energii_*.png        # Wygenerowane wykresy
│   └── .gitkeep
├── docs/                             # Dokumentacja dodatkowa
├── .gitignore                        # Pliki ignorowane przez git
├── LICENSE                           # Licencja Apache 2.0
├── README.md                         # Ten plik
└── requirements.txt                  # Zależności Python
```

## 📝 Uwagi

*   **Pierwsze uruchomienie**: Może potrwać 5-10 minut ze względu na scraping cen TGE dla całego miesiąca (każdy dzień osobno). Kolejne uruchomienia będą korzystać z cache.
*   **Google Chrome**: Wymagany do scrapowania danych przez Selenium. WebDriver pobierze się automatycznie.
*   **Cache**: Dane są zapisywane w katalogach `data/` (logi SUPLA, ceny TGE). Możesz je usunąć, aby wymusić ponowne pobranie.
*   **Dokładność obliczeń**: Weryfikuj wyniki z oficjalnymi fakturami. Narzędzie służy do analizy i porównań, nie do rozliczeń prawnych.

## 🤝 Współpraca

Zgłaszanie błędów, propozycje nowych funkcji i pull requesty są mile widziane!

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

## 📄 Licencja

Ten projekt jest udostępniony na licencji Apache 2.0. Zobacz plik [LICENSE](LICENSE) po więcej szczegółów.

---

**Autor:** [devopsit-mg](https://github.com/devopsit-mg)  
**Repozytorium:** [supla-taryfy](https://github.com/devopsit-mg/supla-taryfy)
