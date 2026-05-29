const purchases = [
    { n: "Marcelo C.", c: "México", f: "🇲🇽" }, { n: "Elena M.", c: "España", f: "🇪🇸" },
    { n: "Sofía V.", c: "Argentina", f: "🇦🇷" }, { n: "Carlos R.", c: "Colombia", f: "🇨🇴" },
    { n: "Ricardo T.", c: "Chile", f: "🇨🇱" }, { n: "Marcela P.", c: "Perú", f: "🇵🇪" },
    { n: "Andrés G.", c: "Uruguay", f: "🇺🇾" }, { n: "Lucía S.", c: "México", f: "🇲🇽" },
    { n: "Javier D.", c: "Ecuador", f: "🇪🇨" }, { n: "Valeria B.", c: "Costa Rica", f: "🇨🇷" },
    { n: "Fernando K.", c: "Panamá", f: "🇵🇦" }, { n: "Mónica L.", c: "Bolivia", f: "🇧🇴" },
    { n: "Diego N.", c: "Paraguay", f: "🇵🇾" }, { n: "Paula Q.", c: "Rep. Dominicana", f: "🇩🇴" },
    { n: "Santiago J.", c: "España", f: "🇪🇸" }, { n: "Gabriela F.", c: "México", f: "🇲🇽" },
    { n: "Roberto W.", c: "Argentina", f: "🇦🇷" }, { n: "Natalia Z.", c: "Colombia", f: "🇨🇴" },
    { n: "Miguel A.", c: "Chile", f: "🇨🇱" }, { n: "Carolina E.", c: "Perú", f: "🇵🇪" },
    { n: "Juan P.", c: "Uruguay", f: "🇺🇾" }, { n: "Isabel T.", c: "México", f: "🇲🇽" },
    { n: "Luis H.", c: "España", f: "🇪🇸" }, { n: "Patricia G.", c: "Colombia", f: "🇨🇴" },
    { n: "Felipe M.", c: "Chile", f: "🇨🇱" }, { n: "Sandra R.", c: "México", f: "🇲🇽" },
    { n: "Daniel O.", c: "Argentina", f: "🇦🇷" }, { n: "Andrea S.", c: "Perú", f: "🇵🇪" },
    { n: "Esteban L.", c: "Ecuador", f: "🇪🇨" }, { n: "Laura V.", c: "Costa Rica", f: "🇨🇷" },
    { n: "Tomas B.", c: "México", f: "🇲🇽" }, { n: "Clara C.", c: "España", f: "🇪🇸" },
    { n: "Raúl G.", c: "Colombia", f: "🇨🇴" }, { n: "Monica P.", c: "Chile", f: "🇨🇱" },
    { n: "Sergio F.", c: "Argentina", f: "🇦🇷" }, { n: "Silvia D.", c: "México", f: "🇲🇽" },
    { n: "Hugo R.", c: "Perú", f: "🇵🇪" }, { n: "Beatriz M.", c: "España", f: "🇪🇸" },
    { n: "Oscar L.", c: "Costa Rica", f: "🇨🇷" }, { n: "Rosa K.", c: "Colombia", f: "🇨🇴" },
    { n: "Emilio S.", c: "Chile", f: "🇨🇱" }, { n: "Carmen P.", c: "México", f: "🇲🇽" },
    { n: "Pedro T.", c: "Argentina", f: "🇦🇷" }, { n: "Marta G.", c: "España", f: "🇪🇸" },
    { n: "Lucas V.", c: "Uruguay", f: "🇺🇾" }, { n: "Julia D.", c: "Perú", f: "🇵🇪" },
    { n: "Cesar M.", c: "Colombia", f: "🇨🇴" }, { n: "Adriana B.", c: "México", f: "🇲🇽" },
    { n: "Jorge A.", c: "Chile", f: "🇨🇱" }, { n: "Ines F.", c: "España", f: "🇪🇸" },
    { n: "Ramiro P.", c: "México", f: "🇲🇽" }, { n: "Camila L.", c: "Argentina", f: "🇦🇷" },
    { n: "Nicolas G.", c: "Colombia", f: "🇨🇴" }, { n: "Lorena S.", c: "Uruguay", f: "🇺🇾" },
    { n: "Matías E.", c: "Perú", f: "🇵🇪" }, { n: "Teresa R.", c: "España", f: "🇪🇸" },
    { n: "Gonzalo J.", c: "México", f: "🇲🇽" }, { n: "Elisa C.", c: "Chile", f: "🇨🇱" },
    { n: "Marcos V.", c: "Argentina", f: "🇦🇷" }, { n: "Eva D.", c: "Colombia", f: "🇨🇴" },
    { n: "Victor P.", c: "México", f: "🇲🇽" }, { n: "Sara M.", c: "España", f: "🇪🇸" },
    { n: "Iván G.", c: "Chile", f: "🇨🇱" }, { n: "Diana R.", c: "Perú", f: "🇵🇪" },
    { n: "Rubén O.", c: "Uruguay", f: "🇺🇾" }, { n: "Cristina S.", c: "México", f: "🇲🇽" },
    { n: "Ángel B.", c: "Colombia", f: "🇨🇴" }, { n: "Pilar F.", c: "Argentina", f: "🇦🇷" },
    { n: "Agustín T.", c: "España", f: "🇪🇸" }, { n: "Noelia K.", c: "México", f: "🇲🇽" },
    { n: "Gerardo M.", c: "Chile", f: "🇨🇱" }, { n: "Claudia G.", c: "Ecuador", f: "🇪🇨" },
    { n: "Fabián D.", c: "Perú", f: "🇵🇪" }, { n: "Rocío L.", c: "México", f: "🇲🇽" },
    { n: "Manuel P.", c: "España", f: "🇪🇸" }, { n: "Claudio S.", c: "Argentina", f: "🇦🇷" },
    { n: "Josefina V.", c: "Chile", f: "🇨🇱" }, { n: "Enrique G.", c: "Colombia", f: "🇨🇴" },
    { n: "Olga R.", c: "México", f: "🇲🇽" }, { n: "Braulio T.", c: "Costa Rica", f: "🇨🇷" },
    { n: "Gisela F.", c: "Uruguay", f: "🇺🇾" }, { n: "Héctor B.", c: "Perú", f: "🇵🇪" },
    { n: "Irene S.", c: "España", f: "🇪🇸" }, { n: "Arturo D.", c: "México", f: "🇲🇽" },
    { n: "Blanca L.", c: "Colombia", f: "🇨🇴" }, { n: "Samuel M.", c: "Chile", f: "🇨🇱" },
    { n: "Nora P.", c: "Argentina", f: "🇦🇷" }, { n: "Alfredo G.", c: "España", f: "🇪🇸" },
    { n: "Celia V.", c: "México", f: "🇲🇽" }, { n: "Damián R.", c: "Uruguay", f: "🇺🇾" },
    { n: "Estela S.", c: "Perú", f: "🇵🇪" }, { n: "Félix B.", c: "España", f: "🇪🇸" },
    { n: "Gloria M.", c: "Colombia", f: "🇨🇴" }, { n: "Isidro F.", c: "Chile", f: "🇨🇱" },
    { n: "Lidia G.", c: "México", f: "🇲🇽" }, { n: "Mauricio D.", c: "Argentina", f: "🇦🇷" },
    { n: "Nieves L.", c: "España", f: "🇪🇸" }, { n: "Orlando P.", c: "México", f: "🇲🇽" },
    { n: "Queta V.", c: "Perú", f: "🇵🇪" }, { n: "René S.", c: "Colombia", f: "🇨🇴" }
];
let availablePurchases = [...purchases];
function showNotification() {
    if (availablePurchases.length === 0) {
        availablePurchases = [...purchases];
    }
    const chip = document.getElementById('purchaseChip');
    const content = document.getElementById('purchaseContent');
    
    if (!chip || !content) return;
        const randomIndex = Math.floor(Math.random() * availablePurchases.length);
    const p = availablePurchases.splice(randomIndex, 1)[0];
    
    content.innerHTML = `Nueva compra: <strong>${p.n}</strong> - ${p.c} ${p.f}`;
    
    chip.classList.add('show');
    
    setTimeout(() => {
        chip.classList.remove('show');
        
                const nextDelay = Math.floor(Math.random() * 2000) + 2000;
        setTimeout(showNotification, nextDelay);
    }, 1500); }
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(showNotification, 2000);
});