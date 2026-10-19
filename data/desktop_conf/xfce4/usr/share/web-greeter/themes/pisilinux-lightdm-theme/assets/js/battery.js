/**
 * battery.js - Batarya durumu yönetimi
 */

const updateBattery = (battery) => {
    const level = Math.floor(battery.level * 100);
    const charging = battery.charging;
    
    $('#battery-level').text(level + '%');
    
    // Renk değiştir
    if (level > 50) {
        $('#battery-level').css('color', '#00ff00'); // Yeşil
    } else if (level > 20) {
        $('#battery-level').css('color', '#ffaa00'); // Turuncu
    } else {
        $('#battery-level').css('color', '#ff0000'); // Kırmızı
    }
    
    // İkon ve durum
    if (charging) {
        $('#battery-icon').text('⚡').attr('title', 'Şarj oluyor');
    } else {
        const icons = {
            high: '🔋',    // %80+
            medium: '🔋',  // %50-80
            low: '🪫',     // %20-50
            critical: '🪫' // %0-20
        };
        
        let icon = level > 80 ? icons.high :
                   level > 50 ? icons.medium :
                   level > 20 ? icons.low : icons.critical;
        
        $('#battery-icon').text(icon).attr('title', `Batarya: ${level}%`);
    }
};

// Batarya sistemini başlat
const initBattery = () => {
    if ('getBattery' in navigator) {
        navigator.getBattery().then((battery) => {
            updateBattery(battery);
            
            battery.addEventListener('levelchange', () => updateBattery(battery));
            battery.addEventListener('chargingchange', () => updateBattery(battery));
            
            // Her 30 saniyede bir güncelle
            setInterval(() => updateBattery(battery), 30000);
        });
    } else {
        // Masaüstü PC için gizle
        $('#battery-status').hide();
        console.log("Battery API desteklenmiyor");
    }
};

