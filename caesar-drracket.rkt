#lang racket/base

;; DrRacket-versjon av caesar.rkt: alt ligger på toppnivå, så alle funksjonene
;; er tilgjengelige i Interactions-panelet.
;;
;; Bruk: trykk Run, og skriv så i Interactions:
;;       (define offset 7)
;;       (define path "c7.txt")
;;       (encode offset path)    eller    (decode offset path)
;; Relative filnavn regnes fra mappa filen ligger i (DrRacket sin standard).

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


;; Leser input-fil tegn for tegn, printer forskyvet tegn,
;; stopper når det ikke er flere tegn å lese
(define (shift-file port shift-char)
  (let ((c (read-char port)))
    (cond ((eof-object? c) (close-input-port port))
          (else (display (shift-char c))
                (shift-file port shift-char)))))

;; Koding går framover i alfabetet, dekoding bakover
(define (encode offset path)
  (shift-file (open-input-file path) (make-shifter offset)))

(define (decode offset path)
  (shift-file (open-input-file path) (make-shifter (- offset))))
