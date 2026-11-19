#lang racket/base

;; Koder eller dekoder en fil med cæsar-chiffer.
;; Bruk: racket test.rkt -e TALL FIL   (koder)
;;       racket test.rkt -d TALL FIL   (dekoder)

;; Alfabetet. 30 tegn, mellomrom er med helt til slutt.
(define abc (list "a" "b" "c" "d" "e" "f" "g" "h" "i" "j" "k" "l" "m" "n"
                  "o" "p" "q" "r" "s" "t" "u" "v" "w" "x" "y" "z" "æ" "ø" "å" " "))

(define (length lst)
  (if (null? lst)
      0
      (+ 1 (length (cdr lst)))))

(define abc-len (length abc))

;; Henter ut element nummer i fra lista (første er 0).
;; Hopper over ett element og teller ned i til vi er framme.
(define (look-up lst i)
  (if (= i 0)
      (car lst)
      (look-up (cdr lst) (- i 1))))

;; Skal ha tre argumenter: flagg, hvor langt det er forskjøvet, og fila
(define args (vector->list (current-command-line-arguments)))
(cond ((not (= (length args) 3))
       (error 'test "usage: racket test.rkt -e|-d INTEGER FILE")))

(define n (string->number (cadr args)))
;(display n)
(cond ((not (exact-integer? n))
       (error 'test "expected an integer")))

(define path (caddr args))

;; Koding går framover i alfabetet, dekoding bakover
(define shift
  (cond ((string=? (car args) "-e") n)
        ((string=? (car args) "-d") (- n))
        (else (error 'test "expected -e or -d"))))

;; Finner plassen til et tegn i lista, #f hvis det ikke er der.
;; pos teller oppover mens vi går gjennom lista
(define (find-index c lst pos)
  (cond ((null? lst) #f)
        ((string=? c (car lst)) pos)
        (else (find-index c (cdr lst) (+ pos 1)))))

;; Ett tegn. Står det ikke i alfabetet (store bokstaver, tall, komma osv)
;; blir det bare latt være som det er.
;; modulo passer på at vi starter på nytt i andre enden når vi går over/under
;; make-shifter tar inn hvor mye vi skal flytte og gir tilbake en prosedyre
;; som flytter ett tegn akkurat så mye. let husker plassen så vi slipper å
;; lete to ganger.
(define (make-shifter steps)
  (lambda (c)
    (let ((index (find-index (string c) abc 0)))
      (if index
          (look-up abc (modulo (+ index steps) abc-len))
          (string c)))))

(define shift-char (make-shifter shift))

;; Leser ett tegn om gangen fra fila, bytter det og skriver det ut med en
;; gang. Da trenger vi aldri hele teksten i en streng, og dermed heller
;; ikke å vite hvor lang den er. Stopper når fila er tom.
(define (shift-file port)
  (let ((c (read-char port)))
    (cond ((eof-object? c) (close-input-port port))
          (else (display (shift-char c))
                (shift-file port)))))

(shift-file (open-input-file path))
