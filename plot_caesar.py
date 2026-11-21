#!/usr/bin/env python3
"""Tegner figurer som viser hva crack_caesar.py gjør og hvordan det går.

Bruk:
    python plot_caesar.py                 lager PNG-filer i plots/
    python plot_caesar.py --dark          samme, men mørk bakgrunn
    python plot_caesar.py --out MAPPE     lagrer et annet sted

Trenger en trent modell (python crack_caesar.py train).

Figurene:
    1_kryptert_tekst            hva et cæsar-chiffer gjør med bokstavfordelingen
    2_treningskurve             hvor fort transformeren lærer seg oppgaven
    3_treningskurver_trappen    det samme for alle modellene i trappen (trappen.py)
    4_treffsikkerhet            transformeren mot not_that_difficult.py, etter tekstlengde
    5_trappen_per_lengde        alle modellene, hver trent på lengden de testes på, mot statistikken
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import ConnectionPatch

import crack_caesar as cc
import not_that_difficult as nd
import trappen as tp

# Fargene følger en validert palett: blå og oransje er kategori 1 og 2, grå er "bakgrunn"
# når ett tegn skal fram.
THEMES = {
    "light": dict(
        surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781",
        grid="#e1e0d9", axis="#c3c2b7", dim="#c3c2b7", blue="#2a78d6", orange="#eb6834",
        aqua="#1baf7a", yellow="#eda100", magenta="#e87ba4",
    ),
    "dark": dict(
        surface="#1a1a19", ink="#f0efec", ink2="#c3c2b7", muted="#898781",
        grid="#2c2c2a", axis="#383835", dim="#52514e", blue="#3987e5", orange="#d95926",
        aqua="#199e70", yellow="#c98500", magenta="#d55181",
    ),
}

# Hver modell har sin egen farge i alle figurene (fast rekkefølge, aldri etter rang)
SERIES = {"Transformer": "blue", "Statistikk": "orange", "MLP på alle plasser": "aqua",
          "Ett lag på alle plasser": "yellow", "Ett lag på tegnandeler": "magenta"}


def series_color(t, name):
    return t[SERIES[name]]


# not_that_difficult.py leser alfabetet fra samme CSV som nettverket, og må få samme tegn i samme rekkefølge
STATS_ABC, STATS_FREQ = nd.load_frequencies(cc.HERE / "vanligst.csv")
assert STATS_ABC == cc.ABC


def stats_accuracy(ids, shift):
    """Andel riktige for not_that_difficult.py. Den får tekst og ikke tall, som i virkeligheten."""
    hits = 0
    for row, k in zip(ids.tolist(), shift.tolist()):
        text = "".join(STATS_ABC[i] for i in row)
        hits += nd.decipher(text, STATS_ABC, STATS_FREQ)[1] == k
    return hits / len(shift)


def sym(c):
    return "␣" if c == " " else c


def pct(x, digits=0):
    return f"{x:.{digits}f}".replace(".", ",") + " %"


def thousands(n):
    return f"{n:,}".replace(",", " ")


def apply_theme(t):
    plt.rcParams.update({
        "figure.facecolor": t["surface"], "axes.facecolor": t["surface"],
        "savefig.facecolor": t["surface"], "font.family": "DejaVu Sans", "font.size": 10,
        "text.color": t["ink"], "axes.labelcolor": t["ink2"],
        "xtick.color": t["muted"], "ytick.color": t["muted"],
        "xtick.labelcolor": t["ink2"], "ytick.labelcolor": t["ink2"],
        "axes.edgecolor": t["axis"], "axes.spines.top": False, "axes.spines.right": False,
    })


def heading(fig, t, title, sub):
    fig.text(0.04, 0.965, title, fontsize=16, fontweight="semibold", color=t["ink"], va="top")
    fig.text(0.04, 0.915, sub, fontsize=10.5, color=t["ink2"], va="top", linespacing=1.4)


def style(ax, t, grid="y"):
    """Rolige akser: tynne, hele, lyse rutelinjer og ingen ramme rundt."""
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color(t["axis"])
    ax.tick_params(length=0)
    if grid:
        ax.grid(axis=grid, color=t["grid"], linewidth=0.8, linestyle="-")


def save(fig, out, name):
    path = out / f"{name}.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


# ---------------------------------------------------------------- 1: hva chifferet gjør

def fig_shift(t, out):
    """Samme 100 tegn før og etter koding: histogrammet glir sidelengs, formen er den samme."""
    N, shift, length = cc.N, 7, 100
    plain = cc.make_plain(np.random.default_rng(3), 1, length, cc.LETTER_P)[0]
    cipher = (plain + shift) % N
    h_plain = np.bincount(plain, minlength=N) / length * 100
    h_cipher = np.bincount(cipher, minlength=N) / length * 100
    top = np.argsort(-h_plain)[:2]  # de to vanligste tegnene i klarteksten

    fig = plt.figure(figsize=(11, 6.6))
    heading(fig, t, "Et cæsar-chiffer flytter bokstavfordelingen",
            f"Samme 100 tegn før og etter koding med forskyvning {shift}. Formen er den samme, den er bare skjøvet "
            f"{shift} plasser.\nAlfabetet går i ring, så tegn som havner utenfor slutten kommer rundt til starten.")
    ax1 = fig.add_axes([0.06, 0.54, 0.92, 0.25])
    ax2 = fig.add_axes([0.06, 0.10, 0.92, 0.25])
    ymax = max(h_plain.max(), h_cipher.max()) * 1.2

    panels = ((ax1, h_plain, top, "Klartekst"), (ax2, h_cipher, (top + shift) % N, f"Kodet (forskyvning {shift})"))
    for ax, h, hi, title in panels:
        ax.bar(range(N), h, width=0.62, color=[t["blue"] if i in hi else t["dim"] for i in range(N)])
        for i in hi:  # bare de to fremhevede får tall
            ax.text(i, h[i] + ymax * 0.02, pct(h[i]), ha="center", va="bottom", fontsize=9, color=t["ink2"])
        ax.set_ylim(0, ymax)
        ax.set_xlim(-0.7, N - 0.3)
        ax.set_xticks(range(N), [sym(c) for c in cc.ABC], fontsize=10)
        ax.set_yticks(range(0, int(ymax) + 1, 5), [f"{v} %" for v in range(0, int(ymax) + 1, 5)])
        ax.set_title(title, loc="left", fontsize=11, fontweight="semibold", color=t["ink"], pad=10)
        style(ax, t)

    for p in top:  # piler fra der tegnet sto til der det står nå
        c = (p + shift) % N
        fig.add_artist(ConnectionPatch(
            xyA=(p, -0.24), coordsA=ax1.get_xaxis_transform(), xyB=(c, 1.1), coordsB=ax2.get_xaxis_transform(),
            arrowstyle="-|>", mutation_scale=12, color=t["blue"], linewidth=1.6, shrinkA=0, shrinkB=0))
    save(fig, out, "1_kryptert_tekst")


# ---------------------------------------------------------------- 2: treningskurven

def fig_training(t, out, curves, name="2_treningskurve"):
    """Treffsikkerhet på 100 tegn mot antall tekster modellene har sett. curves er {navn: historikk}."""
    chance = 100 / cc.N
    multi = len(curves) > 1

    def first95(history):  # første målepunkt over 95 %
        return next((h["texts"] for h in history if h["acc"] >= 0.95), None)

    fig = plt.figure(figsize=(10.5, 6.0))
    if multi:
        title = "Hvor fort hver modell lærer seg oppgaven"
        sub = ("Treffsikkerhet på tekster på 100 tegn underveis i treningen (gjennomsnitt av flere treninger).\n"
               f"Alle starter på tilfeldig gjetting ({pct(chance, 1)}). Prikkene viser hvor hver kurve passerer 95 %.")
    else:
        (history,) = curves.values()
        k95 = first95(history)
        title = "Nettverket må lære alt fra bunnen av"
        sub = f"Treffsikkerhet på tekster på 100 tegn, målt underveis i treningen. Starter på tilfeldig gjetting ({pct(chance, 1)})"
        sub += f"\nog er over 95 % etter {thousands(k95)} tekster." if k95 is not None else "."
    heading(fig, t, title, sub)

    ax = fig.add_axes([0.09, 0.13, 0.86, 0.62])
    last = max(h["texts"] for hist in curves.values() for h in hist)
    ax.axhline(chance, color=t["axis"], linewidth=1.5, zorder=1)
    ax.text(last, chance + 2, f"tilfeldig gjetting, {pct(chance, 1)}", ha="right", va="bottom", fontsize=9.5,
            color=t["muted"])
    for rank, (model_name, history) in enumerate(curves.items()):
        texts = [h["texts"] for h in history]
        acc = [h["acc"] * 100 for h in history]
        color = series_color(t, model_name)
        ax.plot(texts, acc, color=color, linewidth=2, label=model_name if multi else None, zorder=3)
        if multi:  # en prikk der kurven først passerer 95 %
            k = next((i for i, a in enumerate(acc) if a >= 95), None)
            if k is not None:
                ax.scatter([texts[k]], [acc[k]], s=110 - 18 * rank, color=color, edgecolor=t["surface"], linewidth=2, zorder=4)
        if not multi:
            ax.scatter([texts[-1]], [acc[-1]], s=70, color=color, edgecolor=t["surface"], linewidth=2, zorder=4)
            ax.annotate(pct(acc[-1]), (texts[-1], acc[-1]), xytext=(-8, -22), textcoords="offset points", ha="right",
                        fontsize=10, color=t["ink2"])
            k = next((i for i, a in enumerate(acc) if a >= 95), None)
            if k is not None:
                ax.scatter([texts[k]], [acc[k]], s=70, color=color, edgecolor=t["surface"], linewidth=2, zorder=4)
                ax.annotate(f"{pct(acc[k])} etter {thousands(texts[k])} tekster", (texts[k], acc[k]),
                            xytext=(14, -26), textcoords="offset points", fontsize=10, color=t["ink2"])
    ax.set_xscale("symlog", linthresh=512)  # tett i starten, der det skjer mest
    ax.set_xlim(0, last * 1.1)
    ax.set_ylim(0, 105)
    ax.set_yticks(range(0, 101, 20), [f"{v} %" for v in range(0, 101, 20)])
    xt = [v for v in (0, 1_000, 10_000, 100_000) if v <= last]
    ax.set_xticks(xt, [thousands(v) for v in xt])
    ax.minorticks_off()
    ax.set_xlabel("tekster modellen har sett (logaritmisk akse)")
    ax.set_ylabel("treffsikkerhet")
    style(ax, t)
    if multi:
        ax.legend(loc="lower right", bbox_to_anchor=(1, 0.1), frameon=False, labelcolor=t["ink2"], fontsize=10)
    save(fig, out, name)


# ---------------------------------------------------------------- 3: treffsikkerhet mot statistikk

def fig_accuracy(t, out, model, n_net=3000, n_stats=400):
    lengths = [3, 5, 8, 12, 16, 20, 30, 50, 100, 200, 400]
    net, stats = [], []
    for length in lengths:
        ids, shift = cc.make_batch(np.random.default_rng(1234 + length), n_net, length)
        net.append(cc.accuracy(model, ids, shift) * 100)
        stats.append(stats_accuracy(ids[:n_stats], shift[:n_stats]) * 100)
    chance = 100 / cc.N
    lo, hi = cc.TRAIN_LENGTHS

    fig = plt.figure(figsize=(10.5, 6.2))
    stats_wins = all(s >= n - 1 for s, n in zip(stats, net))  # statistikken er minst like god overalt
    intro = "Andel riktige gjetninger på syntetisk norsk tekst. not_that_difficult.py trenger ingen trening"
    if stats_wins:
        sub = intro + " og er like god\neller bedre på alle lengder. Nettverket er svakest på korte tekster, og det er slike det har sett minst av."
    else:
        sub = intro + ".\nNettverket ligger tett på. Se hvor de skiller lag."
    heading(fig, t, "Nettverket mot en håndfull linjer statistikk", sub)
    ax = fig.add_axes([0.09, 0.13, 0.80, 0.65])
    ax.axvspan(lo, hi, color=t["grid"], alpha=0.7, zorder=0, linewidth=0)
    ax.text(np.sqrt(lo * hi), 8, f"trent på\n{lo}–{hi} tegn", ha="center", va="bottom", fontsize=9, color=t["muted"])
    ax.axhline(chance, color=t["axis"], linewidth=1.5, zorder=1)
    ax.text(lengths[0], chance + 2, f"tilfeldig gjetting, {pct(chance, 1)}", ha="left", va="bottom", fontsize=9.5,
            color=t["muted"])
    ax.plot(lengths, stats, color=t["orange"], linewidth=2, marker="o", markersize=10, markeredgecolor=t["surface"],
            markeredgewidth=2, label="not_that_difficult.py (statistikk, ingen trening)", zorder=2)
    ax.plot(lengths, net, color=t["blue"], linewidth=2, marker="o", markersize=6, markeredgecolor=t["surface"],
            markeredgewidth=2, label="Transformer-nettverket", zorder=3)
    ax.set_xscale("log")
    ax.set_xticks(lengths, [str(v) for v in lengths])
    ax.minorticks_off()
    ax.set_ylim(0, 105)
    ax.set_yticks(range(0, 101, 20), [f"{v} %" for v in range(0, 101, 20)])
    ax.set_xlabel("tegn i teksten (logaritmisk akse)")
    ax.set_ylabel("treffsikkerhet")
    style(ax, t)
    leg = ax.legend(loc="lower right", bbox_to_anchor=(1, 0.14), frameon=False, labelcolor=t["ink2"], fontsize=10)
    for h in leg.legend_handles:
        h.set_markersize(8)
    k = lengths.index(12)  # et sted der avstanden er tydelig
    ax.annotate(f"{pct(stats[k])} mot {pct(net[k])}\nved {lengths[k]} tegn", (lengths[k], net[k]), xytext=(14, -34),
                textcoords="offset points", fontsize=9.5, color=t["ink2"])
    save(fig, out, "4_treffsikkerhet")


# ---------------------------------------------------------------- 5: alle modellene, trent per lengde

def fig_trappen(t, out, lengths=(3, 5, 8, 10, 12, 16, 20, 30, 50, 100, 200, 400), n_stats=400):
    """Hver modell trent og testet på samme lengde (de flate kan ikke lese andre lengder). Gir resultatene."""
    lengths = list(lengths)
    results = tp.per_length(lengths)
    stats = []
    for length in lengths:
        ids, shift = cc.make_batch(np.random.default_rng(1234 + length), 3000, length)  # samme tekster som nettverkene
        n = 3000 if length <= 30 else n_stats  # korte tekster er der forskjellene er, og der trengs mange tester
        stats.append(stats_accuracy(ids[:n], shift[:n]))
    results["Statistikk"] = stats
    chance = 100 / cc.N

    fig = plt.figure(figsize=(10.5, 6.2))
    heading(fig, t, "Alle modellene, trent på lengden de testes på",
            "Andel riktige gjetninger på syntetisk norsk tekst. Hver modell er trent for seg på hver lengde (400 steg),\n"
            "siden de flate modellene bare kan lese én lengde. not_that_difficult.py trenger ingen trening.")
    ax = fig.add_axes([0.09, 0.13, 0.80, 0.65])
    ax.axhline(chance, color=t["axis"], linewidth=1.5, zorder=1)
    ax.text(lengths[-1], chance + 2, f"tilfeldig gjetting, {pct(chance, 1)}", ha="right", va="bottom", fontsize=9.5,
            color=t["muted"])
    order = ["Statistikk", "MLP på alle plasser", "Ett lag på alle plasser", "Ett lag på tegnandeler", "Transformer"]
    sizes = [10, 9, 8, 7, 6]  # størst bakerst, så de synes der de ligger oppå hverandre
    for model_name, size in zip(order, sizes):
        label = "Statistikk (not_that_difficult.py)" if model_name == "Statistikk" else model_name
        ax.plot(lengths, [v * 100 for v in results[model_name]], color=series_color(t, model_name), linewidth=2,
                marker="o", markersize=size, markeredgecolor=t["surface"], markeredgewidth=2, label=label,
                zorder=2 + sizes.index(size) * 0.1)
    ax.set_xscale("log")
    ax.set_xticks(lengths, [str(v) for v in lengths])
    ax.minorticks_off()
    ax.set_ylim(0, 105)
    ax.set_yticks(range(0, 101, 20), [f"{v} %" for v in range(0, 101, 20)])
    ax.set_xlabel("tegn i teksten (logaritmisk akse)")
    ax.set_ylabel("treffsikkerhet")
    style(ax, t)
    leg = ax.legend(loc="lower right", bbox_to_anchor=(1, 0.14), frameon=False, labelcolor=t["ink2"], fontsize=10)
    for h in leg.legend_handles:
        h.set_markersize(8)
    save(fig, out, "5_trappen_per_lengde")
    results["lengths"] = lengths
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dark", action="store_true", help="mørk bakgrunn")
    parser.add_argument("--out", default=str(cc.HERE / "plots"), help="mappe for bildene")
    args = parser.parse_args()

    t = THEMES["dark" if args.dark else "light"]
    apply_theme(t)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    saved = cc.load_saved()
    model = cc.load_model()

    fig_shift(t, out)
    fig_training(t, out, {"Transformer": saved["history"]})
    ladder = tp.ladder()
    fig_training(t, out, {name: r["history"] for name, r in ladder.items()}, "3_treningskurver_trappen")
    fig_accuracy(t, out, model)
    fig_trappen(t, out)


if __name__ == "__main__":
    main()
