#!/bin/bash

# 1. Konumları Belirle (Sistemin döndürdüğü Türkçe yolları alır)
DESKTOP_DIR=$(xdg-user-dir DESKTOP)
DOCUMENTS_DIR=$(xdg-user-dir DOCUMENTS)
PICTURES_DIR=$(xdg-user-dir PICTURES)
VIDEOS_DIR=$(xdg-user-dir VIDEOS)
MUSIC_DIR=$(xdg-user-dir MUSIC)
DOWNLOAD_DIR=$(xdg-user-dir DOWNLOAD)

# 2. Fonksiyon: Desktop dosyası oluşturur
create_desktop_file() {
    local filename=$1
    local name=$2
    local icon=$3
    local url=$4

    # Eğer hedef dizin (Masaüstü) yoksa oluştur
    mkdir -p "$DESKTOP_DIR"

    cat <<EOF > "$DESKTOP_DIR/$filename"
[Desktop Entry]
Type=Link
Name=$name
Name[tr]=$name
Icon=$icon
URL=$url
EOF
    chmod +x "$DESKTOP_DIR/$filename"
}

# 3. Masaüstü Öğelerini İnşa Et
# Ev Klasörü (Kullanıcı Adı)
create_desktop_file "home.desktop" "$USER" "user-home" "$HOME"

# Bilgisayar (Sistem Adı ile)
create_desktop_file "computer.desktop" "Bilgisayarım" "computer" "/"

# Standart Klasörler
create_desktop_file "documents.desktop" "Belgeler" "folder-documents" "$DOCUMENTS_DIR"
#create_desktop_file "downloads.desktop" "İndirilenler" "folder-download" "$DOWNLOAD_DIR"
#create_desktop_file "pictures.desktop" "Resimler" "folder-pictures" "$PICTURES_DIR"

# Pisi Linux Sosyal (Örnek)
#create_desktop_file "pisi-web.desktop" "https://pisilinux.org" "distributor-logo-pisilinux" "https://pisilinux.org"

# 4. Kapanış ve Temizlik
AUTOSTART_FILE="$HOME/.config/autostart/fix-name.desktop"
if [ -f "$AUTOSTART_FILE" ]; then
    rm "$AUTOSTART_FILE"
fi

# KDE Masaüstünü tazelemek için (isteğe bağlı)
# qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.refreshCurrentShell
