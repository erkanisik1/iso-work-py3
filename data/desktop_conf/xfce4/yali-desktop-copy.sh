#!/bin/sh

USER=pisi
HOME_DIR="/home/$USER"
DESKTOP="$HOME_DIR/Desktop"
SRC="/usr/share/applications/yali.desktop"
DST="$DESKTOP/yali.desktop"
AUTOSTART="/etc/xdg/autostart/yali-desktop.desktop"

# masaüstü yoksa çık
[ -d "$DESKTOP" ] || exit 0
[ -f "$SRC" ] || exit 0

# kopyala
cp "$SRC" "$DST"
chmod +x "$DST"
chown "$USER:$USER" "$DST"

# 🔑 KRİTİK: kullanıcı olarak trusted flag
runuser -u "$USER" -- gio set "$DST" metadata::trusted true

# tek seferlik çalışsın
#rm -f "$AUTOSTART"

exit 0
