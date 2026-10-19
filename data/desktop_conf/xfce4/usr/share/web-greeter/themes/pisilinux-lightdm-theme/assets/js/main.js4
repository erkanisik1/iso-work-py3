/**
 * Pisi Linux - Nody Greeter Final main.js (Düzeltilmiş Versiyon)
 */

let myKeyboard;
let isReadyForPassword = false;

// 1. Sistem Callback Fonksiyonları (Global Alanda Olmalı)
window.show_prompt = function(text, type) {
    console.log("show_prompt çağrıldı:", text, type);
    isReadyForPassword = true; 
    $('#error-message').text("");
};

window.show_message = function(text, type) {
    console.log("show_message çağrıldı:", text, type);
    $('#error-message').text(text);
};

window.authentication_complete = function() {
    console.log("authentication_complete çağrıldı. is_authenticated:", lightdm.is_authenticated);
    
    if (lightdm.is_authenticated) {
        console.log("Giriş başarılı! Oturum başlatılıyor...");
        $('#error-message').text("Giriş başarılı!").css('color', 'green');
        
        // ÖNEMLİ: start_session kullan, login değil
        const session = $('#session-list').val() || lightdm.default_session;
        lightdm.start_session(session);
        
    } else {
        console.log("Giriş başarısız!");
        $('#error-message').text("Hatalı şifre! Lütfen tekrar deneyin.").css('color', 'red');
        $('#password').val("");
        if (myKeyboard) myKeyboard.clearInput();
        
        // ÖNEMLİ: Shake animasyonu ekle
        $('#password').addClass('shake');
        setTimeout(() => {
            $('#password').removeClass('shake');
        }, 500);
        
        isReadyForPassword = false;
        
        // Aynı kullanıcı için tekrar authentication başlat
        const selectedUser = $('#user-list').val();
        if (selectedUser) {
            lightdm.authenticate(selectedUser);
        }
    }
};

// Batarya güncelleme fonksiyonu
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
            high: '🔋',
            medium: '🔋',
            low: '🪫',
            critical: '🪫'
        };
        
        let icon = level > 80 ? icons.high :
                   level > 50 ? icons.medium :
                   level > 20 ? icons.low : icons.critical;
        
        $('#battery-icon').text(icon).attr('title', `Batarya: ${level}%`);
    }
};

// Test/Demo modu - Sahte batarya göster
const showFakeBattery = () => {
    let fakeLevel = 75; // %75'ten başla
    let fakeCharging = false;
    
    const updateFakeBattery = () => {
        $('#battery-level').text(fakeLevel + '%');
        
        if (fakeLevel > 50) {
            $('#battery-level').css('color', '#00ff00');
        } else if (fakeLevel > 20) {
            $('#battery-level').css('color', '#ffaa00');
        } else {
            $('#battery-level').css('color', '#ff0000');
        }
        
        if (fakeCharging) {
            $('#battery-icon').text('⚡').attr('title', 'Şarj oluyor (TEST)');
            fakeLevel = Math.min(100, fakeLevel + 1); // Şarj oluyormuş gibi
        } else {
            const icons = {
                high: '🔋',
                medium: '🔋',
                low: '🪫',
                critical: '🪫'
            };
            
            let icon = fakeLevel > 80 ? icons.high :
                       fakeLevel > 50 ? icons.medium :
                       fakeLevel > 20 ? icons.low : icons.critical;
            
            $('#battery-icon').text(icon).attr('title', `Batarya: ${fakeLevel}% (TEST)`);
            fakeLevel = Math.max(0, fakeLevel - 1); // Azalıyormuş gibi
        }
        
        // %20'ye düşünce şarja tak
        if (fakeLevel <= 20) fakeCharging = true;
        // %100'e ulaşınca şarjı çıkar
        if (fakeLevel >= 100) fakeCharging = false;
    };
    
    updateFakeBattery();
    setInterval(updateFakeBattery, 2000); // 2 saniyede bir güncelle
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
        }).catch((error) => {
            console.log("Battery API hatası:", error);
            showFakeBattery(); // Test modu
        });
    } else {
        console.log("Battery API desteklenmiyor (VM/Desktop)");
        showFakeBattery(); // Test modu
    }
};

$(document).ready(function() {
    // ÖNEMLİ: Callback'leri ÖNCE bağla
    if (lightdm.authentication_complete) {
        lightdm.authentication_complete.connect(authentication_complete);
    }
    if (lightdm.show_prompt) {
        lightdm.show_prompt.connect(show_prompt);
    }
    if (lightdm.show_message) {
        lightdm.show_message.connect(show_message);
    }

    // 3. Listeleri Doldur
    const initLists = () => {
        console.log("Lightdm objesi:", lightdm);
        console.log("Kullanıcılar:", lightdm.users);
        console.log("Oturumlar:", lightdm.sessions);
        
        // Oturumları doldur
        if (lightdm.sessions && lightdm.sessions.length > 0) {
            const sessionOptions = lightdm.sessions.map(s => 
                `<option value="${s.key}">${s.name}</option>`
            ).join('');
            $('#session-list').html(sessionOptions);
        }
        
        // Kullanıcıları doldur
        if (lightdm.users && lightdm.users.length > 0) {
            const userOptions = lightdm.users.map((u) => {
                const userName = u.username || u.name;
                const displayName = u.display_name || userName;
                return `<option value="${userName}">${displayName}</option>`;
            }).join('');
            $('#user-list').html(userOptions);
            
            // İlk kullanıcıyı seç
            const firstUser = lightdm.users[0];
            const userName = firstUser.username || firstUser.name;
            $('#user-list').val(userName);
            
            // ÖNEMLİ: Authentication'ı hemen başlat
            console.log("Authentication başlatılıyor:", userName);
            lightdm.authenticate(userName);
            
            // Focus'u password alanına ver
            $('#password').focus();
        }
    };
    initLists();

    // Kullanıcı değiştiğinde
    $('#user-list').on('change', function() {
        console.log("Kullanıcı değişti:", $(this).val());
        $('#password').val("");
        if (myKeyboard) myKeyboard.clearInput();
        $('#error-message').text("");
        
        isReadyForPassword = false;
        lightdm.cancel_authentication();
        lightdm.authenticate($(this).val());
        
        $('#password').focus();
    });

    // 4. Giriş Mantığı
    $('#login-button').on('click', function() {
        const pass = $('#password').val();
        const selectedUser = $('#user-list').val();
        
        console.log("Giriş butonu - Kullanıcı:", selectedUser, "Şifre var mı:", !!pass);
        console.log("isReadyForPassword:", isReadyForPassword);
        
        if (!pass) {
            $('#error-message').text("Şifre boş olamaz.").css('color', 'orange');
            return;
        }

        
        // ÖNEMLİ: Basitçe respond çağır
        console.log("Şifre gönderiliyor...");
        lightdm.respond(pass);
    });

    // Enter tuşu ile giriş
    $('#password').on('keypress', function(e) {
        if (e.key === 'Enter' || e.keyCode === 13) {
            e.preventDefault();
            $('#login-button').trigger('click');
        }
    });

    // 6. Saat
    const updateTime = () => {
        const now = new Date();
        $('#clock').text(now.toLocaleTimeString('tr-TR', {hour: '2-digit', minute:'2-digit'}));
        $('#date').text(now.toLocaleDateString('tr-TR'));
    };
    setInterval(updateTime, 1000); 
    updateTime();
    
    // 7. Batarya
    initBattery();

    // 8. Sanal Klavye
    if (window.SimpleKeyboard) {
        const Keyboard = window.SimpleKeyboard.default;
        myKeyboard = new Keyboard({
            onChange: input => { 
                $('#password').val(input); 
            },
            onKeyPress: button => { 
                if (button === "{enter}") {
                    $('#login-button').trigger('click');
                }
            },
            layout: {
                default: [
                    '1 2 3 4 5 6 7 8 9 0 {bksp}',
                    'q w e r t y u i o p',
                    'a s d f g h j k l {enter}',
                    'z x c v b n m',
                    '{space}'
                ]
            },
            display: {
                '{bksp}': '⌫',
                '{enter}': '↵',
                '{space}': ' '
            }
        });

        window.changeLanguage = function(lang) {
            const layout = lang === 'tr' ? 
                {
                    default: [
                        '1 2 3 4 5 6 7 8 9 0 {bksp}', 
                        'q w e r t y u ı o p ğ ü', 
                        'a s d f g h j k l ş i {enter}', 
                        'z x c v b n m ö ç', 
                        '{space}'
                    ]
                } : 
                {
                    default: [
                        '1 2 3 4 5 6 7 8 9 0 {bksp}',
                        'q w e r t y u i o p',
                        'a s d f g h j k l {enter}',
                        'z x c v b n m',
                        '{space}'
                    ]
                };
            
            myKeyboard.setOptions({
                layout: layout
            });

            // Buton metnini değiştir
    if (lang === 'tr') {
        $('#login-button').text('Giriş Yap');
        $('#password').attr('placeholder', 'Şifre');
    } else {
        $('#login-button').text('Login');
        $('#password').attr('placeholder', 'Password');
    }
        };
    }
});

// Klavye toggle fonksiyonu
window.toggleKeyboard = function() {
    $('.simple-keyboard').toggle();
};