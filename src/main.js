// Selve chifferet ligger i backend (caesar.rkt via server.rkt).
// Her sender vi bare input, forskyvning og modus til /api/caesar og viser svaret.

const shiftInput = document.getElementById('shift');
const input = document.getElementById('input');
const output = document.getElementById('output');
const error = document.getElementById('error');

let timer = null;
let controller = null;

function showError(msg) {
    error.textContent = msg;
    output.value = '';
}

async function update() {
    // Avbryt forrige forespørsel så gamle svar ikke overskriver nye
    if (controller) controller.abort();

    const n = Number(shiftInput.value);
    if (shiftInput.value.trim() === '' || !Number.isInteger(n)) {
        showError('Forskyvning må være et heltall');
        return;
    }

    controller = new AbortController();
    const mode = document.getElementById('mode-decode').checked ? 'decode' : 'encode';

    try {
        const res = await fetch('/api/caesar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: input.value, shift: n, mode }),
            signal: controller.signal,
        });
        const data = await res.json();
        if (!res.ok) {
            showError(data.error || 'Noe gikk galt');
            return;
        }
        error.textContent = '';
        output.value = data.output;
    } catch (e) {
        if (e.name === 'AbortError') return;
        showError('Fikk ikke kontakt med serveren');
    }
}

// Liten pause så vi ikke sender én forespørsel per tastetrykk
function scheduleUpdate() {
    clearTimeout(timer);
    timer = setTimeout(update, 150);
}

document.querySelectorAll('input[name="mode"]').forEach(r => r.addEventListener('change', update));
shiftInput.addEventListener('input', scheduleUpdate);
input.addEventListener('input', scheduleUpdate);
update();
