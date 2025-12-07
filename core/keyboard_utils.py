"""
Klad Macro Tool - Keyboard Utilities
Ortak klavye tuş ismi dönüşüm fonksiyonları
"""

# Türkçe Q klavye scan code -> tuş eşleştirmesi
SCAN_CODE_MAP = {
    # Sayı satırı - 41: " tuşu (Esc altında)
    41: '"', 2: '1', 3: '2', 4: '3', 5: '4', 6: '5',
    7: '6', 8: '7', 9: '8', 10: '9', 11: '0', 12: '*', 13: '-',
    # Harf satırları
    16: 'q', 17: 'w', 18: 'e', 19: 'r', 20: 't', 21: 'y',
    22: 'u', 23: 'i', 24: 'o', 25: 'p', 26: 'ğ', 27: 'ü',
    30: 'a', 31: 's', 32: 'd', 33: 'f', 34: 'g', 35: 'h',
    36: 'j', 37: 'k', 38: 'l', 39: 'ş', 40: 'i', 43: ',',
    44: 'z', 45: 'x', 46: 'c', 47: 'v', 48: 'b', 49: 'n',
    50: 'm', 51: 'ö', 52: 'ç', 53: '.',
    # Özel tuşlar
    14: 'backspace', 15: 'tab', 28: 'enter', 57: 'space',
    58: 'caps lock', 1: 'esc',
    # F tuşları
    59: 'f1', 60: 'f2', 61: 'f3', 62: 'f4', 63: 'f5', 64: 'f6',
    65: 'f7', 66: 'f8', 67: 'f9', 68: 'f10', 87: 'f11', 88: 'f12',
    # Numpad
    69: 'num lock', 71: 'num 7', 72: 'num 8', 73: 'num 9', 74: 'num -',
    75: 'num 4', 76: 'num 5', 77: 'num 6', 78: 'num +',
    79: 'num 1', 80: 'num 2', 81: 'num 3', 82: 'num 0', 83: 'num .',
    # Ok tuşları ve diğerleri (extended scan codes)
    328: 'up', 336: 'down', 331: 'left', 333: 'right',
    327: 'home', 335: 'end', 329: 'page up', 337: 'page down',
    338: 'insert', 339: 'delete',
    # < > tuşu (Z'nin solunda)
    86: '<',
}

# Shift ile basılan karakterlerin orijinal tuşu (Türkçe Q klavye)
SHIFT_CHAR_MAP = {
    # Sayı satırı shift karakterleri
    '!': '1', 'é': '2', 'É': '2', '"': '2', '\'': '2',
    '^': '3', '+': '4', '$': '4', '%': '5',
    '&': '6', '/': '7', '(': '8', ')': '9', '=': '0',
    '?': '*', '_': '-',
    # Noktalama shift karakterleri
    ';': ',', ':': '.', '>': '<',
    # Windows'un döndürebileceği diğer garip karakterler
    '²': '2', '@': '2', '#': '3', '£': '3',
}

# Modifier tuşları
MODIFIER_KEYS = {
    'shift', 'ctrl', 'alt', 'left shift', 'right shift',
    'left ctrl', 'right ctrl', 'left alt', 'right alt',
    'left windows', 'right windows'
}


def get_physical_key_name(event):
    """
    Fiziksel tuş adını döndür (shift ile değişen karakterleri önle)

    Args:
        event: keyboard modülünden gelen event objesi

    Returns:
        str: Fiziksel tuş adı (küçük harf)
    """
    # Modifier tuşları direkt kullan
    if event.name.lower() in MODIFIER_KEYS:
        return event.name.lower()

    # Scan code ile fiziksel tuşu bul
    scan_code = event.scan_code

    if scan_code in SCAN_CODE_MAP:
        return SCAN_CODE_MAP[scan_code]

    # event.name'den gelen karakteri kontrol et ve düzelt
    name = event.name
    if name in SHIFT_CHAR_MAP:
        return SHIFT_CHAR_MAP[name]

    # Tek karakter ise küçük harfe çevir
    if len(name) == 1:
        return name.lower()

    return name.lower()
