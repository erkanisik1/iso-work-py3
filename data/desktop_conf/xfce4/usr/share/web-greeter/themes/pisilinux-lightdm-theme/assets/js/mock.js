 // Mock API Module (Sadece tarayıcıda test için)
export function initMockAPI() {
    if (typeof lightdm === 'undefined') {
        window.lightdm = {
            users: [{ name: "pisi_test", display_name: "Pisi Kullanıcı" }],
            sessions: [{ key: "plasma", name: "KDE Plasma" }],
            authenticate: function(u) { setTimeout(() => window.show_prompt("Password: "), 200); },
            cancel_authentication: function() {},
            respond: function(p) { setTimeout(() => window.authentication_complete(), 500); },
            is_authenticated: false, // Yanlış şifre testi için false yapabilirsin
            login: function(u, s) { console.log("Giriş yapılıyor: " + s); },
            default_session: "plasma",
            in_authentication: false
        };
    }
}