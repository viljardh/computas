#lang racket/base

;; Programmet Netlify-funksjonen starter for hver forespørsel.
;; Leser forespørselen (JSON) fra stdin og skriver {"status": 200, "body": {...}} til stdout.
;; Logikken ligger i api.rkt, den samme som server.rkt bruker, så svarene blir like.
;;
;; Bygges til en frittstående mappe med: scripts/build-racket.sh

(require json
         "../api.rkt")

(define body
  (with-handlers ([exn:fail? (lambda (e) #f)])   ; ugyldig JSON gir samme svar som i server.rkt
    (read-json)))

(define-values (status answer) (caesar-api body))

(write-json (hasheq 'status status 'body answer))
(newline)
