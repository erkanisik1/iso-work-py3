#!/bin/sh
if [ "$(whoami)" != "pisi" ]; then
    #rm -f /etc/profile.d/live-tz-fix.sh
    return 0 2>/dev/null || exit 0
fi

(
    for i in $(seq 1 30); do
        TZ=$(curl -s --max-time 5 "http://ip-api.com/line?fields=timezone" | tr -d ' \r\n')
        case "$TZ" in
            */*) break ;;
        esac
        sleep 2
    done

    if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
        sudo ln -sf "/usr/share/zoneinfo/$TZ" /etc/localtime
    fi

    #rm -f /etc/profile.d/live-tz-fix.sh
) &
