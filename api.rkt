#lang racket/base

;; Logikken bak POST /api/caesar, uten noen webserver.
;; Brukes både av server.rkt og av Netlify-funksjonen (netlify/caesar-api.rkt),
;; så de to gir nøyaktig de samme svarene.

(require "caesar.rkt")

(provide caesar-api max-text-length)

;; Så ikke noen kan sende inn gigantiske tekster
(define max-text-length 100000)

(define (bad msg)
  (values 400 (hasheq 'error msg)))

;; body er forespørselen som jsexpr, eller #f hvis den ikke var gyldig JSON.
;; Gir (values statuskode svar), der svaret er en jsexpr:
;;   {"text": "...", "shift": 3, "mode": "encode"|"decode"}
;;   -> 200 {"output": "..."}
;;   -> 400 {"error": "..."}
(define (caesar-api body)
  (define text (and (hash? body) (hash-ref body 'text #f)))
  (define shift (and (hash? body) (hash-ref body 'shift #f)))
  (define mode (and (hash? body) (hash-ref body 'mode #f)))
  (cond ((not (string? text))
         (bad "text must be a string"))
        ((> (string-length text) max-text-length)
         (bad "text too long"))
        ((not (exact-integer? shift))
         (bad "shift must be an integer"))
        ((not (member mode '("encode" "decode")))
         (bad "mode must be encode or decode"))
        (else
         ;; Koding går framover i alfabetet, dekoding bakover.
         ;; modulo her så enorme tall ikke gjør mod i caesar.rkt tregt
         (let ((steps (modulo (if (equal? mode "decode") (- shift) shift)
                              abc-len)))
           (values 200 (hasheq 'output (shift-string text steps)))))))
