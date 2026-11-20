#lang racket/base

;; Koder eller dekoder en fil med cæsar-chiffer.
;; Bruk: racket caesar.rkt -e TALL FIL   (koder)
;;       racket caesar.rkt -d TALL FIL   (dekoder)

(provide shift-string abc-len)

;; Tror dette var ca alfabetet, jeg må fortsatt synge for å huske
(define abc '("a" "b" "c" "d" "e" "f" "g" "h" "i" "j" "k" "l" "m" "n" "o"
              "p" "q" "r" "s" "t" "u" "v" "w" "x" "y" "z" "æ" "ø" "å" " "))

;; Hjelpefunksjon listelengde
(define (length lst)
  (if (null? lst)
      0
      (+ 1 (length (cdr lst)))))
;; Kjekt å ha i tilfelle vi vil konvertere mellom div alfabeter
(define abc-len (length abc))


;; Hjelpefunksjon map
(define (map proc items)
  (if (null? items)
      '()
      (cons (proc (car items))
            (map proc (cdr items)))))


;; Hjelpefunksjon apply
(define (apply proc items)
  (cond ((null? items) (proc))
        ((null? (cdr items)) (proc (car items)))
        (else (proc (car items)
                    (apply proc (cdr items))))))



;; Hjelpefunksjon modulo
;; Glemte å håndtere negative tall lmao 
(define (mod x y)
  (cond ((< x 0) (mod (+ x y) y))
        ((< x y) x)
        (else (mod (- x y) y))))


;; Hjelpefunksjon listeoppslag
(define (look-up lst i)
  (if (= i 0)
      (car lst)
      (look-up (cdr lst) (- i 1))))


;; Finner plassen til et tegn i lista, #f hvis det ikke er der.
(define (find-index c lst pos)
  (cond ((null? lst) #f)
        ((string=? c (car lst)) pos)
        (else (find-index c (cdr lst) (+ pos 1)))))


;; Tegn utenfor alfabetet blir værende (store bokstaver, tegn, linjeskift)
;; make-shifter tar inn hvor mye vi skal flytte og gir tilbake en prosedyre
;; som flytter i alfabetet, let lar oss huske plassen når prosedyren lages
(define (make-shifter steps)
  (lambda (c)
    (let ((index (find-index (string c) abc 0)))
      (if index
          (look-up abc (mod (+ index steps) abc-len))
          (string c)))))


;; Eksportfunksjon til JS
(define (shift-string str steps)
  (apply string-append (map (make-shifter steps) (string->list str))))


;; Resten er kommandolinjeverktøyet, det kjører bare med racket caesar.rkt
(module+ main
  ;; Konvertere input til liste fordi hva i f er en vektor=???
  (define args (vector->list (current-command-line-arguments)))
  ;; Sjekke lengde, gi feilmeldinger og sånt
  (cond ((not (= (length args) 3))
         (error 'test "usage: racket test.rkt -e|-d OFFSET file.txt")))


  ;; Hente ut ant plasser, håper bruker gir noe som faktisk er et tall!
  (define n (string->number (cadr args)))
  ;; Sjekker just in case
  (cond ((not (exact-integer? n))
         (error 'test "expected an integer")))


  ;; Hente ut filnavn
  (define path (caddr args))


  ;; Koding går framover i alfabetet, dekoding bakover
  ;; Ellers kunne du også bare hatt length-n, hvem bryr seg
  (define shift
    (cond ((string=? (car args) "-e") n)
          ((string=? (car args) "-d") (- n))
          (else (error 'test "expected -e or -d"))))


  ;; Lager en prosedyre som forskyver alfabetet ønsket antall plasser
  (define shift-char (make-shifter shift))


  ;; Leser input-fil tegn for tegn, printer forskyvet tegn, 
  ;; stopper når det ikke er flere tegn å lese
  (define (shift-file port)
    (let ((c (read-char port)))
      (cond ((eof-object? c) (close-input-port port))
            (else (display (shift-char c))
                  (shift-file port)))))


  ;; Kjører greia
  (shift-file (open-input-file path)))
