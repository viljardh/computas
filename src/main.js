// Cæsar-chiffer, portert fra caesar.rkt.
// Modus (kod/dekod) bestemmer om forskyvningen går framover eller bakover.

const ABC = [..."abcdefghijklmnopqrstuvwxyzæøå "];

// Fungerer også for negative tall (% i JS gir negativt resultat for negative tall)
function mod(x, y) {
    return ((x % y) + y) % y;
}

// Tegn utenfor alfabetet (store bokstaver, tegn, linjeskift) blir værende
function shiftChar(c, steps) {
    const index = ABC.indexOf(c);
    return index === -1 ? c : ABC[mod(index + steps, ABC.length)];
}

function shiftText(text, steps) {
    return Array.from(text, c => shiftChar(c, steps)).join('');
}

// ---- Chifferskive ----
// Nederste rad er alfabetet vi koder. Øverste rad kan dras sideveis, og bokstaven
// rett over hver bokstav nedenfor er den kodede. Posisjonen er det samme som tallet
// i forskyvningsfeltet: dra til venstre for å øke, til høyre for å minke.
// Modus bestemmer bare lesretningen (kod: nede -> oppe, dekod: oppe -> nede).

const N = ABC.length;
const COPIES = 3; // tre kopier så raden kan gå rundt uten hull
const strip = document.getElementById('strip');
const plain = document.getElementById('plain');
const caption = document.getElementById('caption');

function makeCell(c) {
    const cell = document.createElement('div');
    cell.className = 'cell';
    cell.textContent = c === ' ' ? '␣' : c; // synlig mellomrom
    return cell;
}

for (let k = 0; k < COPIES * N; k++) strip.appendChild(makeCell(ABC[k % N]));
for (let i = 0; i < N; i++) plain.appendChild(makeCell(ABC[i]));
strip.setAttribute('aria-valuemax', N - 1);

// Plasserer raden. d kan ha desimaler mens man drar
function setStrip(d) {
    strip.style.setProperty('--pos', N + mod(d, N));
    strip.setAttribute('aria-valuenow', Math.round(mod(Math.round(d), N)));
}

const shiftInput = document.getElementById('shift');
const input = document.getElementById('input');
const output = document.getElementById('output');
const error = document.getElementById('error');

function update() {
    const decoding = document.getElementById('mode-decode').checked;
    caption.textContent = 'Dra den blå raden sideveis. ' + (decoding
        ? 'Dekod: finn bokstaven i øverste rad, svaret står under'
        : 'Kod: finn bokstaven i nederste rad, svaret står over');
    const n = Number(shiftInput.value);
    if (shiftInput.value.trim() === '' || !Number.isInteger(n)) {
        error.textContent = 'Forskyvning må være et heltall';
        output.value = '';
        return;
    }
    error.textContent = '';
    // Koding går framover i alfabetet, dekoding bakover
    output.value = shiftText(input.value, decoding ? -n : n);
}

// Gjeldende forskyvning fra feltet, eller null hvis det ikke er et heltall
function currentShift() {
    const n = Number(shiftInput.value);
    return shiftInput.value.trim() === '' || !Number.isInteger(n) ? null : n;
}

// Setter tallet, og flytter raden med mindre vi drar (da flytter musa den selv)
function setShift(n, moveStrip = true) {
    shiftInput.value = n;
    if (moveStrip) {
        strip.classList.remove('snap');
        setStrip(n);
    }
    update();
}

let drag = null;

strip.addEventListener('pointerdown', e => {
    const base = currentShift();
    if (base === null || e.button !== 0) return;
    strip.classList.remove('snap');
    strip.classList.add('dragging');
    strip.setPointerCapture(e.pointerId);
    setStrip(base);
    drag = {
        id: e.pointerId,
        startX: e.clientX,
        base,
        d: base,
        cell: strip.firstElementChild.getBoundingClientRect().width,
    };
});

strip.addEventListener('pointermove', e => {
    if (!drag || e.pointerId !== drag.id) return;
    // Raden følger musa: drar du til venstre øker forskyvningen
    drag.d = drag.base - (e.clientX - drag.startX) / drag.cell;
    setStrip(drag.d);
    const n = Math.round(drag.d);
    if (n !== currentShift()) setShift(n, false);
});

function endDrag(e) {
    if (!drag || e.pointerId !== drag.id) return;
    const n = Math.round(drag.d);
    // Gli på plass uten å gå via mod, ellers sveiper raden en hel runde tilbake
    const pos = Number(strip.style.getPropertyValue('--pos'));
    strip.classList.add('snap');
    strip.style.setProperty('--pos', pos + (n - drag.d));
    strip.classList.remove('dragging');
    drag = null;
    setShift(n, false);
}

strip.addEventListener('pointerup', endDrag);
strip.addEventListener('pointercancel', endDrag);

// Etter glidningen setter vi raden tilbake til normal posisjon (samme utseende)
strip.addEventListener('transitionend', () => {
    if (drag) return;
    strip.classList.remove('snap');
    const n = currentShift();
    if (n !== null) setStrip(n);
});

// Piltaster på den fokuserte raden, samme retning som å dra
strip.addEventListener('keydown', e => {
    const n = currentShift();
    if (n === null) return;
    if (e.key === 'ArrowLeft') setShift(n + 1);
    else if (e.key === 'ArrowRight') setShift(n - 1);
    else return;
    e.preventDefault();
});

// Skriver man tallet selv, flytter raden seg til riktig sted
shiftInput.addEventListener('input', () => {
    const n = currentShift();
    if (n !== null && !drag) {
        strip.classList.remove('snap');
        setStrip(n);
    }
});

// Store knapper i stedet for de små pilene i tallfeltet
document.getElementById('shift-minus').addEventListener('click', () => setShift((currentShift() ?? 0) - 1));
document.getElementById('shift-plus').addEventListener('click', () => setShift((currentShift() ?? 0) + 1));

document.querySelectorAll('input[name="mode"]').forEach(r => r.addEventListener('change', update));
shiftInput.addEventListener('input', update);
input.addEventListener('input', update);
update();
if (currentShift() !== null) setStrip(currentShift());
