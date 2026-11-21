#!/usr/bin/env python3
"""Lærer et PyTorch-nettverk å knekke cæsar-chiffer ved å lese teksten, og ingenting annet.

Dette er med vilje en dum måte å løse det på. Nettverket får de kodede tegnene og skal svare
med en av 30 mulige forskyvninger. Det får ikke vite at tegn kan telles, at norsk har en
bestemt bokstavfordeling eller at en forskyvning er en rotasjon av alfabetet. Alt det må
finne ut selv, av syntetiske eksempler. Det er mye maskineri for noe man kan gjøre med litt
statistikk, og not_that_difficult.py viser hvor lite som egentlig skal til.

Bruk:
    python crack_caesar.py train          lager syntetiske tekster, trener, evaluerer og lagrer modellen
    python crack_caesar.py crack FIL      gjetter forskyvningen til en kodet fil og skriver ut klarteksten

Alfabetet og frekvensene leses fra vanligst.csv: ett tegn per linje, i den rekkefølgen de
står, mellomrom (" ") er også en linje. Alfabetet må være det samme som tekstene ble kodet
med. Mellomrom blir forskjøvet som alle andre tegn, så i en kodet tekst er det vanligste
tegnet gjerne mellomrommets nye bokstav. Mellomrommets andel i CSV-en bestemmer hvor lange
ord de syntetiske tekstene får. Frekvensene brukes bare til å lage treningsdata, selve
nettverket får aldri se dem.
"""
import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

HERE = Path(__file__).parent
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # trener og kjører på GPU hvis den finnes
MODEL_PATH = HERE / "caesar_cracker.pt"


def read_alphabet(path=HERE / "vanligst.csv"):
    """Leser vanligst.csv. Gir (alfabetet i filens rekkefølge, sannsynlighet per tegn, sum 1)."""
    symbols, freqs = [], []
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) != 2:  # tomme linjer
                continue
            symbol = row[0]
            if len(symbol) != 1 or symbol in symbols:
                raise ValueError(f"{path.name}: ugyldig eller duplisert tegn {symbol!r}")
            symbols.append(symbol)
            freqs.append(float(row[1]))
    if " " not in symbols:
        raise ValueError(f"{path.name}: mangler en linje for mellomrom (' ,andel')")
    probs = np.array(freqs)
    return "".join(symbols), probs / probs.sum()


ABC, SYMBOL_P = read_alphabet()
N = len(ABC)
SPACE = ABC.index(" ")
SPACE_P = SYMBOL_P[SPACE]  # mellomrommets andel av alle tegn
LETTERS = np.array([i for i in range(N) if i != SPACE])  # plassene til alt som ikke er mellomrom
LETTER_P = SYMBOL_P[LETTERS] / SYMBOL_P[LETTERS].sum()  # fordelingen blant bokstavene alene

# Ord er 1 + Poisson(lam) bokstaver og ett mellomrom, så mellomrommets andel er 1 / (lam + 2).
# Løser vi for lam får vi ordlengden som gir akkurat andelen fra CSV-en.
WORD_LAM = (1 - SPACE_P) / SPACE_P - 1

TRAIN_LENGTHS = (50, 150)  # nettverket trenes på tekster med så mange tegn (ca. 100, litt variasjon)


# ---------------------------------------------------------------- data


def make_plain(rng, batch, length, letter_p=LETTER_P, lam_spread=1.5):
    """Syntetiske norske tekster som tegn-indekser 0..N-1, form (batch, length).

    Bokstavene trekkes etter vanligst.csv (letter_p er fordelingen blant bokstavene alene).
    Mellomrommene legges inn så teksten består av ord: ordlengden er 1 + Poisson(lam), og lam
    er satt så mellomrommets andel blir den samme som i CSV-en. Hver tekst får sin egen lam, litt
    over eller under snittet (± lam_spread), så modellen ikke lærer ett bestemt mellomromsforhold
    og tåler tekster som ligner litt mindre på CSV-en.
    """
    lo, hi = max(WORD_LAM - lam_spread, 0.0), WORD_LAM + lam_spread
    lam = rng.uniform(lo, hi, size=(batch, 1))
    max_words = length // 2 + 2  # ord på 1 tegn + mellomrom er korteste mulige
    word_len = 1 + rng.poisson(lam, size=(batch, max_words))
    space_pos = np.cumsum(word_len + 1, axis=1) - 1  # plassen til mellomrommet etter hvert ord
    text = LETTERS[rng.choice(len(LETTERS), size=(batch, length), p=letter_p)]
    rows, cols = np.nonzero(space_pos < length)
    text[rows, space_pos[rows, cols]] = SPACE
    return text


def make_batch(rng, batch, length, letter_p=LETTER_P):
    """Koder tekstene med tilfeldige forskyvninger. Gir (kodet tekst som tegn-indekser, fasit-forskyvning)."""
    plain = make_plain(rng, batch, length, letter_p)
    shift = rng.integers(0, N, size=batch)
    cipher = (plain + shift[:, None]) % N
    return torch.from_numpy(cipher), torch.from_numpy(shift)


def shift_text(text, steps):
    """tegn utenfor alfabetet blir stående."""
    return "".join(ABC[(ABC.index(c) + steps) % N] if c in ABC else c for c in text)


# ---------------------------------------------------------------- modell

class Cracker(nn.Module):
    """En liten transformer som leser den kodede teksten og svarer med en av N forskyvninger.

    Tegnene gjøres om til vektorer, noen lag med oppmerksomhet blander dem, snittet over hele
    teksten går inn i et lag som gir en poengsum per forskyvning. Det er hele modellen, og
    ingenting i den vet noe om cæsar-chiffer. Eneste forhåndskunnskap er at vi ikke har gitt
    den posisjonskoding: rekkefølgen på tegnene sier ingenting om forskyvningen.
    """

    def __init__(self, d=64, heads=4, layers=2):
        super().__init__()
        self.embed = nn.Embedding(N, d)
        layer = nn.TransformerEncoderLayer(d, heads, 4 * d, dropout=0.0, batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.head = nn.Linear(d, N)

    def forward(self, ids):  # ids: (batch, length) tegn-indekser -> (batch, N) poengsum per forskyvning
        return self.head(self.encoder(self.embed(ids)).mean(dim=1))


# ---------------------------------------------------------------- trening og evaluering

def predict(model, ids, chunk=2000):
    """Gjetter forskyvning for mange tekster på én gang (i biter, så minnet holder)."""
    model.eval()
    device = next(model.parameters()).device
    with torch.no_grad():
        return torch.cat([model(ids[i:i + chunk].to(device)).argmax(1).cpu() for i in range(0, len(ids), chunk)])


def accuracy(model, ids, shift):
    return (predict(model, ids) == shift.cpu()).float().mean().item()


def evaluate(model, lengths=(10, 30, 50, 100, 200), n=3000):
    print(f"\n{'lengde':>7} {'nettverk':>9} {'tilfeldig':>10}")
    for length in lengths:
        ids, shift = make_batch(np.random.default_rng(1234 + length), n, length)  # samme testsett hver gang
        print(f"{length:>7} {accuracy(model, ids, shift):>9.1%} {1 / N:>10.1%}")


def train(epochs=5, batches_per_epoch=40, batch=256, lr=0.01, seed=0, eval_every=8):
    """Dataene lages fortløpende, så en epoke er bare et fast antall nye batcher.

    Gir (modell, historikk). Historikken er treffsikkerheten på 100 tegn underveis i treningen.
    """
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)

    print("Eksempel på syntetisk tekst (klartekst, og kodet med forskyvning 7):")
    for row in make_plain(rng, 3, 100):
        text = "".join(ABC[i] for i in row)
        print(f"  {text}\n  {shift_text(text, 7)}\n")

    model = Cracker().to(DEVICE)
    gpu = f" ({torch.cuda.get_device_name(DEVICE)})" if DEVICE.type == "cuda" else ""
    print(f"Trener på {DEVICE.type}{gpu}")
    print(f"Nettverket har {sum(p.numel() for p in model.parameters()):,} parametre".replace(",", " "))
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs * batches_per_epoch)

    val_ids, val_shift = make_batch(np.random.default_rng(999), 1000, 100)
    history = [{"step": 0, "texts": 0, "acc": accuracy(model, val_ids, val_shift)}]
    seconds = 0.0  # tiden selve treningen tok, uten målingene
    step = 0
    for epoch in range(1, epochs + 1):
        for _ in range(batches_per_epoch):
            start = time.time()
            length = int(rng.integers(TRAIN_LENGTHS[0], TRAIN_LENGTHS[1] + 1))
            ids, shift = make_batch(rng, batch, length)
            ids, shift = ids.to(DEVICE), shift.to(DEVICE)
            model.train()
            loss = F.cross_entropy(model(ids), shift)
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
            if DEVICE.type == "cuda":
                torch.cuda.synchronize()  # GPU-en jobber asynkront, så vent før vi tar tiden
            seconds += time.time() - start
            step += 1
            if step <= 32 and step % 2 == 0 or step % eval_every == 0:  # tett i starten, der det skjer mest
                history.append({"step": step, "texts": step * batch, "acc": accuracy(model, val_ids, val_shift)})
        print(f"epoke {epoch}/{epochs}  tap {loss.item():.3f}  treffsikkerhet på 100 tegn {history[-1]['acc']:.1%}")

    print(f"\nTreningen tok {seconds:.0f} sekunder og så {step * batch:,} tekster".replace(",", " "))
    evaluate(model)
    weights = {k: v.cpu() for k, v in model.state_dict().items()}  # lagres uavhengig av hvor vi trente
    torch.save({"alphabet": ABC, "model": weights, "history": history, "seconds": seconds}, MODEL_PATH)
    print(f"\nModellen er lagret i {MODEL_PATH.name}")
    return model, history


# ---------------------------------------------------------------- knekke ekte tekst

def crack_text(model, text):
    """Gir (forskyvning, sikkerhet) for en kodet tekst. Tegn utenfor alfabetet telles ikke."""
    idx = torch.tensor([[ABC.index(c) for c in text if c in ABC]])
    if idx.shape[1] == 0:
        raise ValueError("fant ingen tegn fra alfabetet i teksten")
    model.eval()
    with torch.no_grad():
        probs = F.softmax(model(idx.to(next(model.parameters()).device)), dim=1)[0].cpu()
    shift = int(probs.argmax())
    return shift, float(probs[shift])


def load_saved():
    """Leser den lagrede modellen (vekter, historikk, treningstid). Nekter hvis alfabetet er endret."""
    if not MODEL_PATH.exists():
        sys.exit(f"Fant ikke {MODEL_PATH.name}, kjør først: python crack_caesar.py train")
    saved = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
    if saved["alphabet"] != ABC:
        sys.exit("vanligst.csv har et annet alfabet enn modellen ble trent med, kjør på nytt: python crack_caesar.py train")
    return saved


def load_model():
    model = Cracker()
    model.load_state_dict(load_saved()["model"])
    return model.to(DEVICE)


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
        model, _ = train()
        for f in ("s13.txt", "s7.txt"):
            print()
            crack_file(model, HERE / f)
        print("\nTil sammenligning gjør python not_that_difficult.py s13.txt det samme uten noe av dette.")
    else:
        crack_file(load_model(), args.file)


if __name__ == "__main__":
    main()
