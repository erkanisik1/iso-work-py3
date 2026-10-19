#!/bin/bash
# KDE 6 Menu Watcher for Pisi Linux
# Uygulama dizinlerini izler ve değişiklik olduğunda KDE menü önbelleğini günceller.

# İzlenecek dizinler
TARGET_DIRS="/usr/share/applications $HOME/.local/share/applications"

# Geçerli dizinleri filtrele
WATCH_DIRS=""
for d in $TARGET_DIRS; do
    if [ -d "$d" ]; then
        WATCH_DIRS="$WATCH_DIRS $d"
    fi
done

echo "KDE Menu Watcher baslatiliyor. Izlenen dizinler: $WATCH_DIRS"

# gio monitor komutu ile dosya sistemi değişikliklerini dinle
# dbus üzerinden veya systemd --user servisi üzerinden de yapılabilirdi ama
# pisi linux/elogind ortamında bu yöntem en portatif olanıdır.

gio monitor $WATCH_DIRS | while read -r line; do
    CURRENT_TIME=$(date +%s)
    
    # Basit debounce (yumuşatma): 
    # Aynı anda birçok dosya kopyalanırsa (paket yükleme vb.) her dosya için ayrı ayrı
    # çalıştırmamak adına, son çalıştırmadan bu yana 2 saniye geçmesini bekle.
    
    if [ -z "$LAST_RUN" ] || [ $((CURRENT_TIME - LAST_RUN)) -ge 2 ]; then
         echo "[$(date +'%H:%M:%S')] Değişiklik algılandı, menü güncelleniyor..."
         
         # KDE System Configuration Cache'i (sycoca) yeniden oluştur
         kbuildsycoca6 --noincremental
         
         LAST_RUN=$(date +%s)
    fi
done
