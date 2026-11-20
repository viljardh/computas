// Cæsar-chiffer, portert fra caesar.rkt.
// Skriver man i Decoded kodes teksten fremover (Encoded), skriver man i Encoded
// dekodes den bakover (Decoded).

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
// rett over hver bokstav nedenfor er den kodede. Posisjonen er forskyvningen:
// dra til venstre for å øke den, til høyre for å minke den.

const N = ABC.length;
const COPIES = 3; // tre kopier så raden kan gå rundt uten hull
const strip = document.getElementById('strip');
const plain = document.getElementById('plain');

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

const decoded = document.getElementById('decoded');
const encoded = document.getElementById('encoded');

// Forskyvningen: heltall, kan bli større enn alfabetet hvis man drar flere runder.
// Posisjonen på skiven er den eneste inngangen.
let shift = 3;

// Feltet man sist skrev i er "fasit", det andre regnes ut fra det
let source = decoded;

function update() {
    // Koding går framover i alfabetet, dekoding bakover
    if (source === decoded) encoded.value = shiftText(decoded.value, shift);
    else decoded.value = shiftText(encoded.value, -shift);
}

// Setter forskyvningen, og flytter raden med mindre vi drar (da flytter musa den selv)
function setShift(n, moveStrip = true) {
    shift = n;
    if (moveStrip) {
        strip.classList.remove('snap');
        setStrip(n);
    }
    update();
}

let drag = null;

strip.addEventListener('pointerdown', e => {
    if (e.button !== 0) return;
    const base = shift;
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
    if (n !== shift) setShift(n, false);
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
    setStrip(shift);
});

// Piltaster på den fokuserte raden, samme retning som å dra
strip.addEventListener('keydown', e => {
    if (e.key === 'ArrowLeft') setShift(shift + 1);
    else if (e.key === 'ArrowRight') setShift(shift - 1);
    else return;
    e.preventDefault();
});

// Alfabetet har bare små bokstaver, så begge feltene tvinges til små bokstaver
// (også ved lim inn). Vi husker markøren, ellers hopper den til slutten når
// verdien byttes ut.
function forceLowercase(field) {
    const lower = field.value.toLowerCase();
    if (lower !== field.value) {
        const start = field.selectionStart;
        const end = field.selectionEnd;
        field.value = lower;
        field.setSelectionRange(start, end);
    }
}

decoded.addEventListener('input', () => { forceLowercase(decoded); source = decoded; update(); });
encoded.addEventListener('input', () => { forceLowercase(encoded); source = encoded; update(); });
setStrip(shift);
update();
