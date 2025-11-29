# Klad Macro Tool

Ekran görüntüsü okuyarak tetiklenen makro aracı. Oyunlarda skill ikonları, buff/debuff göstergeleri veya herhangi bir görsel değişiklik algılandığında otomatik tuş/makro çalıştırır.

## Kullanım Alanları

- **Knight Online**: Assassin combo, Minor combo, HP/MP potion otomasyonu
- **World of Warcraft**: WeakAuras + GSE entegrasyonu ile rotation desteği
- **Emulator / Diğer**: Görsel tetiklemeli her türlü otomasyon

> Proje WoW'daki GSE (Gnome Sequencer Enhanced) kullanımı için geliştirilmiştir.

## Özellikler

- **Grup Sistemi**: Bağımsız toggle key, arama bölgesi ve template'ler
- **Template Matching**: OpenCV tabanlı, ayarlanabilir threshold
- **Makro Sistemi**: Basit tuş combo veya Logitech G Hub tarzı gelişmiş makro (key_down, key_up, sleep)
- **Kayıt**: Klavye girişlerini direkt makroya kaydet
- **Performans**: mss + grayscale, 60+ FPS
- **FPS Overlay**: Gerçek zamanlı arama hızı göstergesi

## Kurulum

```bash
pip install -r requirements.txt
python config_manager_v3.py
```

## Kullanım

1. Grup oluştur, toggle key belirle
2. Ekranda arama bölgesi seç
3. Template ekle (ekrandan yakala)
4. Her template için tuş/makro ayarla
5. Hotkey ile başlat

## Lisans

MIT
