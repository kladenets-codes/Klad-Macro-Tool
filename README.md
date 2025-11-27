# Template Config Manager v3

**Çok Amaçlı Görsel Makro ve Combo Box Sistemi**

Bu uygulama birçok oyun, emülatör ve özellikle Knight Online USKO/MYKO gibi oyunlarda Assassin - Warrior combo box olarak kullanılabilir. Ekran görüntüsü eşleştirme ile otomatik tuş/makro tetikleme yaparak skill rotation, combo zincirleri ve otomatik tepki sistemleri oluşturmanızı sağlar.

---

Ekran görüntüsü eşleştirme ve otomatik tuş basma uygulaması. Oyun otomasyonu, makro sistemleri ve görsel tetiklemeli işlemler için tasarlanmıştır.

## Özellikler

### Grup Sistemi
- Birden fazla bağımsız grup oluşturma
- Her grup kendi toggle tuşu, arama bölgesi ve template'leri ile çalışır
- Gruplar paralel process olarak çalışır (multiprocessing)
- Grup bazlı spam tuşu ve timing ayarları

### Template Yönetimi
- Ekrandan görsel kesit alma
- OpenCV ile template matching (cv2.matchTemplate)
- Eşik değeri (threshold) ayarlama
- Template'leri aktif/pasif yapma
- Template kopyalama (duplicate)
- Renk kodlu görsel gösterge

### Makro Sistemi (Logitech G Hub Tarzı)
İki mod desteklenir:

**Basit Mod:**
- Tek tuş kombinasyonu (örn: `alt+"`, `shift+t`)
- Pre-delay, hold time, post-delay timing ayarları

**Gelişmiş Makro Modu:**
- `key_down` - Tuşa bas
- `key_up` - Tuşu bırak
- `key_press` - Bas ve bırak
- `sleep` - Bekleme (ms)
- Kayıt özelliği (Record) - Klavye hareketlerini otomatik kaydet
- Drag & drop ile sıralama
- Butonları sürükleyerek listeye ekleme

### Performans
- mss kütüphanesi ile hızlı ekran yakalama (~3-8ms)
- Grayscale template matching (3x daha hızlı)
- 60+ FPS arama hızı
- Gerçek zamanlı FPS overlay göstergesi

### Kullanıcı Arayüzü
- Modern karanlık tema (CustomTkinter)
- Tab sistemi (Gruplar, Genel Ayarlar)
- Gerçek zamanlı durum göstergesi
- Ekran bölgesi seçici
- Görsel önizleme
- Debug log konsolu

## Dosya Yapısı

```
configmanagerv2/
├── config_manager_v3.py    # Ana uygulama
├── config_v3.json          # Konfigürasyon dosyası
├── images/                 # Template görselleri klasörü
│   ├── purple.png
│   ├── yellow.png
│   └── orange.png
├── requirements.txt
└── README.md
```

## Konfigürasyon Yapısı (config_v3.json)

```json
{
  "groups": [
    {
      "id": "group_unique_id",
      "name": "Grup Adı",
      "enabled": true,
      "toggle_key": "num lock",
      "spam_key": "\"",
      "spam_enabled": true,
      "spam_timing": {
        "pre_delay": 1,
        "hold_time": 1,
        "post_delay": 1
      },
      "spam_key_interval": 0.025,
      "search_region": [430, 275, 750, 460],
      "templates": [
        {
          "name": "purple",
          "file": "purple.png",
          "enabled": true,
          "threshold": 0.9,
          "key_combo": "alt+\"",
          "color": "#800080",
          "timing": {
            "pre_delay": 1,
            "hold_time": 1,
            "post_delay": 1
          },
          "use_macro": false,
          "macro": []
        }
      ]
    }
  ],
  "global_settings": {
    "debug_enabled": false
  }
}
```

## Makro Örneği

```json
{
  "use_macro": true,
  "macro": [
    {"action": "key_down", "key": "alt"},
    {"action": "sleep", "ms": 50},
    {"action": "key_down", "key": "\""},
    {"action": "sleep", "ms": 100},
    {"action": "key_up", "key": "\""},
    {"action": "key_up", "key": "alt"}
  ]
}
```

## Gereksinimler

```
opencv-python==4.8.1.78
numpy==1.24.3
pyautogui==0.9.54
keyboard==0.13.5
Pillow==10.0.0
mss==10.1.0
customtkinter==5.2.0
```

## Kurulum

```bash
pip install -r requirements.txt
```

## Kullanım

```bash
python config_manager_v3.py
```

### Temel İş Akışı

1. **Grup Oluştur** - "+ Ekle" ile yeni grup
2. **Toggle Tuşu Seç** - Grubu başlatacak tuş
3. **Arama Bölgesi Belirle** - Ekranda taranacak alan
4. **Template Ekle** - Ekrandan görsel kes
5. **Tuş/Makro Ayarla** - Eşleşme olunca ne yapılacak
6. **Başlat** - Toggle tuşu ile aktifleştir

### Makro Kayıt

1. Template düzenle
2. "Gelişmiş Makro Kullan" seç
3. "Kayıt Başlat" tıkla
4. Klavyede tuşlara bas
5. "Bitti" ile kayıt bitir

### Drag & Drop

- Makro butonlarını listeye sürükle
- Liste içinde "≡" tutamacı ile sırala

## Knight Online Combo Box Kullanımı

### Assassin İçin:
1. Skill bar'daki skill ikonlarını template olarak ekleyin
2. Her skill için tetiklenecek tuşu ayarlayın
3. Combo sırasına göre öncelik belirleyin (liste sırası = öncelik)

### Warrior İçin:
1. Buff/debuff ikonlarını izleyin
2. Otomatik skill rotation oluşturun
3. Spam tuşu ile temel saldırı döngüsü ekleyin

## Notlar

- Windows'ta yönetici hakları gerekebilir (keyboard hook için)
- Template görselleri `images/` klasöründe saklanır
- Her grup ayrı process olarak çalışır
- Kaydetmeyi unutmayın!
- FPS overlay ekranın sağ üst köşesinde görünür

## Lisans

MIT
