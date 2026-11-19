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

const shiftInput = document.getElementById('shift');
const input = document.getElementById('input');
const output = document.getElementById('output');
const error = document.getElementById('error');

function update() {
    const n = Number(shiftInput.value);
    if (shiftInput.value.trim() === '' || !Number.isInteger(n)) {
        error.textContent = 'Forskyvning må være et heltall';
        output.value = '';
        return;
    }
    error.textContent = '';
    // Koding går framover i alfabetet, dekoding bakover
    const decoding = document.getElementById('mode-decode').checked;
    output.value = shiftText(input.value, decoding ? -n : n);
}

document.querySelectorAll('input[name="mode"]').forEach(r => r.addEventListener('change', update));
shiftInput.addEventListener('input', update);
input.addEventListener('input', update);
update();
