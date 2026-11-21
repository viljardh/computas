// Netlify-funksjonen for POST /api/caesar.
//
// Den gjør nesten ingenting selv: den starter et frittstående Racket-program (bygget med
// scripts/build-racket.sh, ligger i netlify/racket/ og pakkes med funksjonen) og sender
// forespørselen inn på stdin. Racket-programmet bruker de samme reglene som server.rkt.

import { spawn } from "node:child_process";
import { access, chmod, constants, cp } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

// Funksjonen svarer på samme adresse som server.rkt, så siden trenger ingen endringer
export const config = { path: "/api/caesar" };

const here = path.dirname(fileURLToPath(import.meta.url));
const MAX_BODY = 1_000_000; // tegn. Racket sjekker selve teksten (maks 100 000), dette er bare et grovt vern
const TIMEOUT_MS = 8000;

// En feil med en kort årsak, så en 500 forteller hva som gikk galt uten at man må lete i loggene
class RacketError extends Error {
    constructor(reason, detail = "") {
        super(detail ? `${reason}: ${detail}` : reason);
        this.reason = reason;
        this.detail = detail;
    }
}

function json(status, body) {
    return new Response(JSON.stringify(body), {
        status,
        headers: { "content-type": "application/json" },
    });
}

// Finner Racket-programmet. Hvor Netlify legger filene avhenger av miljøet, så vi prøver flere steder.
// Husker svaret mellom forespørsler (en "varm" funksjon slipper å lete og kopiere på nytt).
let binary = null;
function findBinary() {
    binary ??= locate();
    return binary;
}

async function locate() {
    const taskRoot = process.env.LAMBDA_TASK_ROOT;
    const dirs = [
        // racket/ ligger ved siden av functions/, både i repoet (netlify/) og i pakken Netlify lager
        path.resolve(here, "..", "racket"),
        taskRoot && path.join(taskRoot, "racket"),
        taskRoot && path.join(taskRoot, "netlify", "racket"),
        path.join(process.cwd(), "netlify", "racket"),
    ];
    for (const dir of dirs.filter(Boolean)) {
        const bin = path.join(dir, "bin", "caesar-api");
        try {
            await access(bin);
        } catch {
            continue;
        }
        try {
            await access(bin, constants.X_OK);
            return bin;
        } catch {
            // Filrettighetene ble ikke med i pakken. Kopier til tmp-mappen og gjør programmet kjørbart der.
            const tmp = path.join(os.tmpdir(), "racket"); // /tmp hos Netlify
            await cp(dir, tmp, { recursive: true });
            await chmod(path.join(tmp, "bin", "caesar-api"), 0o755);
            return path.join(tmp, "bin", "caesar-api");
        }
    }
    throw new RacketError("binary-not-found", "racket/bin/caesar-api ble ikke funnet, har du kjørt scripts/build-racket.sh?");
}

// Starter Racket, sender inn forespørselen på stdin og gir tilbake det som kommer ut på stdout
function runRacket(bin, input) {
    return new Promise((resolve, reject) => {
        const child = spawn(bin, [], { stdio: ["pipe", "pipe", "pipe"] });
        let out = "";
        let err = "";
        const timer = setTimeout(() => {
            child.kill("SIGKILL");
            reject(new RacketError("timeout"));
        }, TIMEOUT_MS);
        child.stdout.setEncoding("utf8").on("data", (d) => (out += d));
        child.stderr.setEncoding("utf8").on("data", (d) => (err += d));
        child.on("error", (e) => {
            clearTimeout(timer);
            reject(new RacketError(`spawn-${e.code ?? "error"}`, e.message));
        });
        child.on("close", (code, signal) => {
            clearTimeout(timer);
            if (code === 0) resolve(out);
            else reject(new RacketError(`exit-${code ?? signal}`, err.trim().slice(0, 300)));
        });
        child.stdin.on("error", () => {}); // hvis Racket dør tidlig, rapporterer "close" det
        child.stdin.end(input);
    });
}

export default async (req) => {
    if (req.method !== "POST") return json(400, { error: "use POST" });

    const body = await req.text();
    if (body.length > MAX_BODY) return json(400, { error: "text too long" });

    try {
        const bin = await findBinary();
        const { status, body: answer } = JSON.parse(await runRacket(bin, body));
        return json(status, answer);
    } catch (e) {
        console.error(e);
        const reason = e instanceof RacketError ? e.reason : "unexpected";
        return json(500, { error: "internal error", reason, ...(e.detail ? { detail: e.detail } : {}) });
    }
};
