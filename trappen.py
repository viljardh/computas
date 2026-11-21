#!/usr/bin/env python3
"""Trappen: enklere modeller å sammenligne Cracker (transformeren i crack_caesar.py) med.

Vi tar bort ting trinn for trinn:
    Transformer             oppmerksomhet, to lag (crack_caesar.Cracker)
    MLP på alle plasser     alle plassene i teksten som én lang vektor, med egne vekter per plass og tegn
    Ett lag på alle plasser det samme, men uten skjult del
    Ett lag på tegnandeler  først en telling av hvor stor andel hvert tegn er, så ett lag på N x N vekter

De tre siste leser en tekst med fast lengde, så de må trenes på nøyaktig den lengden de skal brukes på.
"""
import time

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn

import crack_caesar as cc

N = cc.N


class FlatMLP(nn.Module):
    """Alle plassene i teksten som én lang vektor, en egen vekt for hver plass og hvert tegn."""

    def __init__(self, length, hidden=256):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(length * N, hidden), nn.ReLU(),
                                 nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, N))

    def forward(self, ids):  # (batch, length) -> (batch, N)
        return self.net(F.one_hot(ids, N).float().flatten(1))


class FlatLinear(nn.Module):
    """Det samme, men uten skjult del."""

    def __init__(self, length):
        super().__init__()
        self.net = nn.Linear(length * N, N)

    def forward(self, ids):
        return self.net(F.one_hot(ids, N).float().flatten(1))


class ShareLinear(nn.Module):
    """Tegnandelene (hvor stor del av teksten hvert tegn er) og ett lineært lag på N x N vekter."""

    def __init__(self, length=None):
        super().__init__()
        self.net = nn.Linear(N, N)

    def forward(self, ids):
        return self.net(F.one_hot(ids, N).float().mean(dim=1))


# (navn, lag) der lag(lengde) gir en ny, utrent modell
RUNGS = [
    ("Transformer", lambda length: cc.Cracker()),
    ("MLP på alle plasser", FlatMLP),
    ("Ett lag på alle plasser", FlatLinear),
    ("Ett lag på tegnandeler", ShareLinear),
]


def fit(make, length, steps=200, lr=1e-2, seed=0, batch=256, track=False):
    """Trener en modell på tekster med fast lengde. Gir (modell, sekunder, historikk).

    Historikken (bare med track=True) er treffsikkerheten på tekster av samme lengde underveis,
    med samme måltidspunkter som crack_caesar.train: tett i starten, der det skjer mest.
    """
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = make(length).to(cc.DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, steps)
    if track:
        val_ids, val_shift = cc.make_batch(np.random.default_rng(999), 2000, length)
        history = [{"step": 0, "texts": 0, "acc": cc.accuracy(model, val_ids, val_shift)}]
    else:
        history = []
    seconds = 0.0
    for step in range(1, steps + 1):
        start = time.time()
        ids, shift = cc.make_batch(rng, batch, length)
        model.train()
        loss = F.cross_entropy(model(ids.to(cc.DEVICE)), shift.to(cc.DEVICE))
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
        if cc.DEVICE.type == "cuda":
            torch.cuda.synchronize()  # GPU-en jobber asynkront, så vent før vi tar tiden
        seconds += time.time() - start
        if track and (step <= 32 and step % 2 == 0 or step % 8 == 0):
            history.append({"step": step, "texts": step * batch, "acc": cc.accuracy(model, val_ids, val_shift)})
    return model, seconds, history


def ladder(length=100, steps=200, seeds=(0, 1, 2), real=None):
    """Trener hvert trinn på samme måte, og gir {navn: resultater}.

    Hvert resultat har parametre, tid, treffsikkerhet på syntetisk tekst (og på ekte tekst hvis
    real=(ids, fasit) er gitt), og historikken (gjennomsnitt over frøene).
    """
    test = cc.make_batch(np.random.default_rng(1334), 3000, length)
    out = {}
    for name, make in RUNGS:
        syn, ekte, seconds, histories = [], [], 0.0, []
        for seed in seeds:
            model, sec, history = fit(make, length, steps=steps, seed=seed, track=True)
            seconds += sec / len(seeds)
            syn.append(cc.accuracy(model, *test))
            if real is not None:
                ekte.append(cc.accuracy(model, *real))
            histories.append(history)
        mean_history = [{"step": h["step"], "texts": h["texts"], "acc": float(np.mean([hs[i]["acc"] for hs in histories]))}
                        for i, h in enumerate(histories[0])]
        out[name] = {
            "params": sum(p.numel() for p in model.parameters()),
            "seconds": seconds,
            "synthetic": float(np.mean(syn)),
            "real": float(np.mean(ekte)) if ekte else None,
            "history": mean_history,
        }
    return out


def per_length(lengths, steps=400, seed=0, n_test=3000):
    """Trener hvert trinn for seg på hver lengde, og gir {navn: [treffsikkerhet per lengde]}."""
    out = {name: [] for name, _ in RUNGS}
    for length in lengths:
        test = cc.make_batch(np.random.default_rng(1234 + length), n_test, length)
        for name, make in RUNGS:
            model, _, _ = fit(make, length, steps=steps, seed=seed)
            out[name].append(cc.accuracy(model, *test))
    return out
