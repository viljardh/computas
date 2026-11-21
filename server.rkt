#lang racket/base

;; Webserver: serverer src/ og har ett API-endepunkt som bruker caesar.rkt.
;; Bruk: racket server.rkt     (PORT og HOST kan settes som miljøvariabler)
;;
;; POST /api/caesar  {"text": "...", "shift": 3, "mode": "encode"|"decode"}
;;   -> 200 {"output": "..."}
;;   -> 400 {"error": "..."}

(require racket/runtime-path
         json
         web-server/servlet
         web-server/servlet-env
         web-server/http/json
         "api.rkt")

(define-runtime-path static-dir "src")

(define (bad-request msg)
  (response/jsexpr (hasheq 'error msg) #:code 400))

;; Tar imot forespørselen og svarer med forskjøvet tekst.
;; Selve logikken ligger i api.rkt, så Netlify-funksjonen kan bruke den samme.
(define (caesar-handler req)
  (cond ((not (eq? (request-method-symbol req) 'post))
         (bad-request "use POST"))
        (else
         (define body
           (with-handlers ([exn:fail? (lambda (e) #f)])
             (bytes->jsexpr (or (request-post-data/raw req) #""))))
         (define-values (status answer) (caesar-api body))
         (response/jsexpr answer #:code status))))

(define (request-method-symbol req)
  (string->symbol (string-downcase (bytes->string/utf-8 (request-method req)))))

(define port (string->number (or (getenv "PORT") "8000")))
(define host (or (getenv "HOST") "127.0.0.1"))

(serve/servlet caesar-handler
               #:port port
               #:listen-ip host
               #:servlet-regexp #rx"^/api/caesar$"
               #:extra-files-paths (list static-dir)
               #:launch-browser? #f
               #:banner? #t)
