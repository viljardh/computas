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
         "caesar.rkt")

(define-runtime-path static-dir "src")

;; Så ikke noen kan sende inn gigantiske tekster
(define max-text-length 100000)

(define (bad-request msg)
  (response/jsexpr (hasheq 'error msg) #:code 400))

;; Tar imot forespørselen og svarer med forskjøvet tekst
(define (caesar-handler req)
  (define body
    (with-handlers ([exn:fail? (lambda (e) #f)])
      (bytes->jsexpr (or (request-post-data/raw req) #""))))
  (define text (and (hash? body) (hash-ref body 'text #f)))
  (define shift (and (hash? body) (hash-ref body 'shift #f)))
  (define mode (and (hash? body) (hash-ref body 'mode #f)))
  (cond ((not (eq? (request-method-symbol req) 'post))
         (bad-request "use POST"))
        ((not (string? text))
         (bad-request "text must be a string"))
        ((> (string-length text) max-text-length)
         (bad-request "text too long"))
        ((not (exact-integer? shift))
         (bad-request "shift must be an integer"))
        ((not (member mode '("encode" "decode")))
         (bad-request "mode must be encode or decode"))
        (else
         ;; Koding går framover i alfabetet, dekoding bakover.
         ;; modulo her så enorme tall ikke gjør mod i caesar.rkt tregt
         (let ((steps (modulo (if (equal? mode "decode") (- shift) shift)
                              abc-len)))
           (response/jsexpr (hasheq 'output (shift-string text steps)))))))

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
