#!/usr/bin/env python3
"""Lærer et lite PyTorch-nettverk å knekke cæsar-chiffer på norsk.

Bruk:
    python crack_caesar.py train          lager syntetiske tekster, trener, evaluerer og lagrer modellen
    python crack_caesar.py crack FIL      gjetter forskyvningen til en kodet fil og skriver ut klarteksten

Alfabetet og bokstavfrekvensene leses fra vanligst.csv: bokstavene i den rekkefølgen de
står, og så mellomrom til slutt. Alfabetet må være det samme som tekstene ble kodet med.
Mellomrom er med i alfabetet og blir forskjøvet som alle andre tegn, så i en kodet
tekst er det vanligste tegnet gjerne mellomrommets nye bokstav.
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

HERE = Path(__file__).parent
MODEL_PATH = HERE / "caesar_cracker.pt"


def read_alphabet(path=HERE / "vanligst.csv"):
    """Leser vanligst.csv. Gir (alfabet med mellomrom sist, bokstavsannsynligheter uten mellomrom)."""
    letters, freqs = [], []
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) != 2:  # tomme linjer
                continue
            letter = row[0]
            if len(letter) != 1 or letter == " " or letter in letters:
                raise ValueError(f"{path.name}: ugyldig eller duplisert bokstav {letter!r}")
            letters.append(letter)
            freqs.append(float(row[1]))
    probs = np.array(freqs)
    return "".join(letters) + " ", probs / probs.sum()


ABC, LETTER_P = read_alphabet()
N = len(ABC) 
SPACE = N - 1


# ---------------------------------------------------------------- data


def make_plain(rng, batch, length, letter_p, word_len_range=(2.0, 5.0)):
    """Syntetiske norske tekster som tall 0..29, form (batch, length).

    Bokstavene trekkes etter vanligst.csv. CSV-en sier ingenting om mellomrom, så vi
    deler teksten i ord: ordlengden er 1 + Poisson(lam), med en egen lam per tekst
    trukket tilfeldig i word_len_range. Da lærer modellen seg ikke ett bestemt
    mellomromsforhold (ca. 14-25 % av tegnene), og den tåler tekster som ligner
    litt mindre på det vi antok.
    """
    lam = rng.uniform(*word_len_range, size=(batch, 1))
    max_words = length // 2 + 2  # ord på 1 tegn + mellomrom er korteste mulige
    word_len = 1 + rng.poisson(lam, size=(batch, max_words))
    space_pos = np.cumsum(word_len + 1, axis=1) - 1  # plassen til mellomrommet etter hvert ord
    text = rng.choice(N - 1, size=(batch, length), p=letter_p)
    rows, cols = np.nonzero(space_pos < length)
    text[rows, space_pos[rows, cols]] = SPACE
    return text


def make_batch(rng, batch, length, letter_p):
    """Koder tekstene med tilfeldige forskyvninger. Gir (histogram, fasit-forskyvning)."""
    plain = make_plain(rng, batch, length, letter_p)
    shift = rng.integers(0, N, size=batch)
    cipher = (plain + shift[:, None]) % N
    return histogram(torch.from_numpy(cipher)), torch.from_numpy(shift)


def histogram(idx):
    """(batch, length) tegn-indekser -> (batch, 30) andel av hvert tegn."""
    return F.one_hot(idx, N).sum(1).float() / idx.shape[1]


def shift_text(text, steps):
    """tegn utenfor alfabetet blir stående."""
    return "".join(ABC[(ABC.index(c) + steps) % N] if c in ABC else c for c in text)


# ---------------------------------------------------------------- modell

class Cracker(nn.Module):
    """For hver mulige forskyvning k: angre den og spør et lite nett "ligner dette norsk?".

    Samme lille nett brukes for alle k, så modellen har forskyvningen innebygd og trenger
    ikke lære 30 ulike tilfeller hver for seg. Utgangen er en poengsum per forskyvning.
    """

    def __init__(self, hidden=16):
        super().__init__()
        self.scorer = nn.Sequential(
            nn.Linear(N, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden), nn.ReLU(),
            nn.Linear(hidden, 1),
        )
        k = torch.arange(N)
        self.register_buffer("idx", (k[:, None] + k[None, :]) % N)  # idx[k, i] = (k + i) % 30

    def forward(self, hist):  # hist: (batch, 30)
        undone = hist[:, self.idx]  # (batch, k, i): histogrammet om forskyvningen var k
        return self.scorer(torch.sqrt(undone)).squeeze(-1)  # (batch, 30)


def likelihood_baseline(letter_p, rng, hist):
    """Klassisk løsning: velg forskyvningen som gir størst sannsynlighet for en norsk tekst.

    Bruker de samme bokstavfrekvensene pluss gjennomsnittlig mellomromsandel fra generatoren.
    Dette er omtrent det beste man kan gjøre med bare bokstavtelling, så nettverket kan
    ikke forventes å slå det.
    """
    sample = torch.from_numpy(make_plain(rng, 20000, 100, letter_p))
    q = histogram(sample).mean(0)
    log_q = torch.log(q)
    idx = (torch.arange(N)[:, None] + torch.arange(N)[None, :]) % N
    return (hist[:, idx] * log_q).sum(-1)  # (batch, 30)


# ---------------------------------------------------------------- trening og evaluering

def accuracy(scores, shift):
    return (scores.argmax(1) == shift).float().mean().item()


def evaluate(model, letter_p, lengths=(30, 50, 100, 200, 400), n=20000):
    print(f"\n{'lengde':>7} {'nettverk':>9} {'sannsynl.':>10} {'tilfeldig':>10}")
    model.eval()
    for length in lengths:
        rng = np.random.default_rng(1234 + length)  # samme testsett hver gang
        hist, shift = make_batch(rng, n, length, letter_p)
        with torch.no_grad():
            net = accuracy(model(hist), shift)
        base = accuracy(likelihood_baseline(letter_p, np.random.default_rng(0), hist), shift)
        print(f"{length:>7} {net:>9.1%} {base:>10.1%} {1 / N:>10.1%}")


def train(epochs=3, batches_per_epoch=20, batch=512, lr=3e-3, seed=0):
    """Dataene lages fortløpende, så en epoke er bare et fast antall nye batcher."""
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    letter_p = LETTER_P

    print("Eksempel på syntetisk tekst (klartekst, og kodet med forskyvning 7):")
    for row in make_plain(rng, 3, 100, letter_p):
        text = "".join(ABC[i] for i in row)
        print(f"  {text}\n  {shift_text(text, 7)}\n")

    model = Cracker()
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs * batches_per_epoch)

    val_hist, val_shift = make_batch(np.random.default_rng(999), 10000, 100, letter_p)
    for epoch in range(1, epochs + 1):
        for _ in range(batches_per_epoch):
            length = int(rng.integers(50, 151))  # ca. 100 tegn, litt variasjon
            hist, shift = make_batch(rng, batch, length, letter_p)
            loss = F.cross_entropy(model(hist), shift)
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
        with torch.no_grad():
            val = accuracy(model(val_hist), val_shift)
        print(f"epoke {epoch}/{epochs}  tap {loss.item():.3f}  treffsikkerhet på 100 tegn {val:.1%}")

    evaluate(model, letter_p)
    torch.save({"alphabet": ABC, "model": model.state_dict()}, MODEL_PATH)
    print(f"\nModellen er lagret i {MODEL_PATH.name}")
    return model


# ---------------------------------------------------------------- knekke ekte tekst

def crack_text(model, text):
    """Gir (forskyvning, sikkerhet) for en kodet tekst. Tegn utenfor alfabetet telles ikke."""
    idx = torch.tensor([[ABC.index(c) for c in text if c in ABC]])
    if idx.shape[1] == 0:
        raise ValueError("fant ingen tegn fra alfabetet i teksten")
    model.eval()
    with torch.no_grad():
        probs = F.softmax(model(histogram(idx)), dim=1)[0]
    shift = int(probs.argmax())
    return shift, float(probs[shift])


def load_model():
    if not MODEL_PATH.exists():
        sys.exit(f"Fant ikke {MODEL_PATH.name}, kjør først: python crack_caesar.py train")
    saved = torch.load(MODEL_PATH, weights_only=True)
    if saved["alphabet"] != ABC:
        sys.exit("vanligst.csv har et annet alfabet enn modellen ble trent med, kjør på nytt: python crack_caesar.py train")
    model = Cracker()
    model.load_state_dict(saved["model"])
    return model


def crack_file(model, path):
    text = Path(path).read_text(encoding="utf-8")
    shift, conf = crack_text(model, text)
    print(f"{path}: forskyvning {shift} (sikkerhet {conf:.0%}), klartekst:")
    print(shift_text(text, -shift))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("train")
    p = sub.add_parser("crack")
    p.add_argument("file")
    args = parser.parse_args()

    if args.cmd == "train":
        model = train()
        for f in ("s13.txt", "s7.txt"):
            print()
            crack_file(model, HERE / f)
    else:
        crack_file(load_model(), args.file)


if __name__ == "__main__":
    main()
