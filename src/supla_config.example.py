# -*- coding: utf-8 -*-
# ----------------------------
# KONFIG UŻYTKOWNIKA - PRZYKŁAD
# ----------------------------
# Skopiuj ten plik do src/supla_config.py i wypełnij swoimi danymi

SUPLA_TOKEN = "TWOJ_TOKEN_TUTAJ"   # Personal Access Token z SUPLA Cloud
CHANNEL_ID = 0                      # ID kanału licznika energii w SUPLA
YEAR = 2026
MONTH = 1

# Jeśli chcesz policzyć też dni ustawowo wolne (poza weekendem) dla G12w:
# pip install holidays
USE_POLISH_HOLIDAYS = True

# Czy Twój licznik ma przełączanie LATO/ZIMA w taryfie OSD?
# Jeśli nie wiesz, zostaw False (bezpieczniej, bo PGE podaje też stałe strefy całoroczne).
METER_SUPPORTS_SUMMER_WINTER = True

# Ceny (zł/kWh netto) – RZECZYWISTE z faktury PGE (energia + dystrybucja).
# Wartości energii czynnej z Ceny.png (Zestaw 1):
# - G11: 0.5000
# - G12: S1 (Dzień) 0.5000, S2 (Noc) 0.4220
# - G12w: S1 (Dzień) 0.5000, S2 (Noc) 0.4857
# Dystrybucja zmienna (z faktury):
# - Dzienna: 0.43360 zł/kWh
# - Nocna:   0.10860 zł/kWh

PRICES = {
    "G11": {"all": 0.5000 + 0.43360},  # Energia G11 + Dystrybucja dzienna
    "G12": {
        "day": 0.5656 + 0.43360,
        "night": 0.3718 + 0.10860
    },
    "G12w": {
        "day": 0.5821 + 0.43360,
        "night": 0.4235 + 0.10860
    },
    "G12n": { # Niedzielna
        # Ceny brutto podane przez użytkownika: S1 0.6212, S2 0.5593
        # Konwersja na netto (dzielenie przez 1.23)
        "day": 0.55511 + 0.43360,
        "night": 0.3912 + 0.10860
    }
}

# Opłaty stałe miesięczne (zł netto) - z faktury PGE listopad 2025
FIXED_CHARGES = {
    "handlowa": 12.48,
    "mocowa": 6.86,
    "stala": 14.40,
    "abonamentowa": 4.50,
    "przejsciowa": 0.10,
}

# Dodatkowe opłaty (zł/kWh netto)
ADDITIONAL_CHARGES = {
    "oze": 0.00350,
    "kogeneracja": 0.00300,
}

# VAT
VAT_RATE = 0.23

# Parametry taryfy dynamicznej PGE (na podstawie oferty z www.gkpge.pl)
# Oferta "Dynamiczna energia z PGE" dostępna do 31.01.2026
# Opłata handlowa dla taryfy G1x: 36,90 zł/msc brutto (29,98 zł netto)
DYNAMIC_TARIFF_FIXED_CHARGE = 29.98  # zł/msc netto (zamiast 12.48 w standardowej taryfie)

# Marża do ceny giełdowej - szacowana na podstawie struktury oferty PGE
# Cena = cena_tge + marża + koszty + obciążenia + podatki
# Typowa marża dla taryf dynamicznych to 0.10-0.20 zł/kWh
DYNAMIC_TARIFF_MARGIN = 0.15  # zł/kWh netto
