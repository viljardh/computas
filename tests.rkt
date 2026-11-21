#lang racket/base

;; Tester for caesar.rkt.
;; Kjør med: raco test tests.rkt   (eller bare: racket tests.rkt)

(require rackunit
         racket/file
         racket/runtime-path
         "caesar.rkt"    ; shift-string og abc-len er eksportert
         "api.rkt")      ; caesar-api og max-text-length

;; Resten av funksjonene i caesar.rkt er ikke eksportert. Vi henter dem ut av modulens
;; namespace i stedet for å endre caesar.rkt bare for å kunne teste den.
;; caesar.rkt har egne length, map og apply, så vi gir dem andre navn her.
(define-runtime-path caesar-path "caesar.rkt")
(dynamic-require caesar-path #f)
(define caesar-ns (module->namespace caesar-path))
(define (fra-caesar navn) (eval navn caesar-ns))

(define abc (fra-caesar 'abc))
(define c-length (fra-caesar 'length))
(define c-map (fra-caesar 'map))
(define c-apply (fra-caesar 'apply))
(define mod (fra-caesar 'mod))
(define look-up (fra-caesar 'look-up))
(define find-index (fra-caesar 'find-index))
(define make-shifter (fra-caesar 'make-shifter))


;; ---------------------------------------------------------------- alfabetet

(test-case "alfabetet har 30 tegn: a-z, æ, ø, å og mellomrom"
  (check-equal? (c-length abc) 30)
  (check-equal? abc-len 30)
  (check-equal? (car abc) "a")
  (check-equal? (list-ref abc 25) "z")
  (check-equal? (list-ref abc 26) "æ")
  (check-equal? (list-ref abc 27) "ø")
  (check-equal? (list-ref abc 28) "å")
  (check-equal? (list-ref abc 29) " "))


;; ---------------------------------------------------------------- length

(test-case "length"
  (check-equal? (c-length '()) 0)
  (check-equal? (c-length '(a)) 1)
  (check-equal? (c-length '(a b c d)) 4))


;; ---------------------------------------------------------------- map

(test-case "map"
  (check-equal? (c-map add1 '(1 2 3)) '(2 3 4))
  (check-equal? (c-map string-upcase '("a" "b")) '("A" "B"))
  (check-equal? (c-map add1 '()) '()))


;; ---------------------------------------------------------------- apply

(test-case "apply"
  (check-equal? (c-apply + '(1 2 3 4)) 10)
  (check-equal? (c-apply + '(7)) 7)
  (check-equal? (c-apply + '()) 0)
  (check-equal? (c-apply string-append '("a" "b" "c")) "abc")
  (check-equal? (c-apply string-append '()) ""))


;; ---------------------------------------------------------------- mod

(test-case "mod"
  (check-equal? (mod 5 3) 2)
  (check-equal? (mod 3 3) 0)
  (check-equal? (mod 0 30) 0)
  (check-equal? (mod 29 30) 29)
  (check-equal? (mod 30 30) 0)
  (check-equal? (mod 61 30) 1))

(test-case "mod med negative tall (den vi glemte først)"
  (check-equal? (mod -1 30) 29)
  (check-equal? (mod -30 30) 0)
  (check-equal? (mod -31 30) 29))

(test-case "mod gir det samme som innebygde modulo"
  (for ([x (in-range -100 101)])
    (check-equal? (mod x 30) (modulo x 30))))


;; ---------------------------------------------------------------- look-up

(test-case "look-up"
  (check-equal? (look-up '(a b c) 0) 'a)
  (check-equal? (look-up '(a b c) 2) 'c)
  (check-equal? (look-up abc 29) " "))

(test-case "look-up utenfor lista gir feil"
  (check-exn exn:fail? (lambda () (look-up '(a b) 5))))


;; ---------------------------------------------------------------- find-index

(test-case "find-index"
  (check-equal? (find-index "a" abc 0) 0)
  (check-equal? (find-index "z" abc 0) 25)
  (check-equal? (find-index "å" abc 0) 28)
  (check-equal? (find-index " " abc 0) 29))

(test-case "find-index teller fra oppgitt startplass"
  (check-equal? (find-index "c" '("a" "b" "c") 10) 12))

(test-case "find-index gir #f for tegn som ikke er i lista"
  (check-false (find-index "A" abc 0))     ; store bokstaver er ikke med
  (check-false (find-index "!" abc 0))
  (check-false (find-index "1" abc 0))
  (check-false (find-index "a" '() 0)))


;; ---------------------------------------------------------------- make-shifter

(test-case "make-shifter flytter framover"
  (check-equal? ((make-shifter 3) #\a) "d")
  (check-equal? ((make-shifter 1) #\z) "æ")
  (check-equal? ((make-shifter 0) #\e) "e"))

(test-case "make-shifter går rundt i alfabetet, og mellomrom er et vanlig tegn"
  (check-equal? ((make-shifter 1) #\å) " ")
  (check-equal? ((make-shifter 1) #\space) "a")
  (check-equal? ((make-shifter 30) #\k) "k")      ; en hel runde
  (check-equal? ((make-shifter 33) #\a) "d"))     ; 33 er det samme som 3

(test-case "make-shifter flytter bakover med negative tall"
  (check-equal? ((make-shifter -1) #\b) "a")
  (check-equal? ((make-shifter -1) #\a) " ")
  (check-equal? ((make-shifter -3) #\d) "a"))

(test-case "make-shifter lar tegn utenfor alfabetet stå"
  (check-equal? ((make-shifter 5) #\A) "A")
  (check-equal? ((make-shifter 5) #\!) "!")
  (check-equal? ((make-shifter 5) #\7) "7")
  (check-equal? ((make-shifter 5) #\newline) "\n"))


;; ---------------------------------------------------------------- shift-string

(test-case "shift-string koder"
  (check-equal? (shift-string "hei" 3) "khl")
  (check-equal? (shift-string "xyz" 3) "æøå")      ; går over i æ, ø, å
  (check-equal? (shift-string "å" 1) " ")
  (check-equal? (shift-string " " 1) "a"))

(test-case "shift-string dekoder med negative tall"
  (check-equal? (shift-string "khl" -3) "hei")
  (check-equal? (shift-string "a" -1) " "))

(test-case "shift-string: tom streng og forskyvning 0 eller 30 gir det samme tilbake"
  (check-equal? (shift-string "" 7) "")
  (check-equal? (shift-string "hei på deg" 0) "hei på deg")
  (check-equal? (shift-string "hei på deg" 30) "hei på deg"))

(test-case "shift-string flytter hele alfabetet ett hakk"
  (check-equal? (shift-string "abcdefghijklmnopqrstuvwxyzæøå " 1)
                "bcdefghijklmnopqrstuvwxyzæøå a"))

(test-case "shift-string lar tegn utenfor alfabetet stå, mellomrom flyttes"
  (check-equal? (shift-string "A b" 1) "Aac")      ; A blir stående, mellomrom blir a
  (check-equal? (shift-string "a1!" 1) "b1!")
  (check-equal? (shift-string "a\nb" 1) "b\nc"))

(test-case "koding og dekoding med samme tall gir tilbake originalen"
  (for* ([n '(-31 -5 0 1 7 13 29 30 61)]
         [s '("hei på deg" "" "æøå " "a b c" "Store Bokstaver, tegn og tall 123!")])
    (check-equal? (shift-string (shift-string s n) (- n)) s)))


;; ---------------------------------------------------------------- api.rkt (logikken bak /api/caesar)

;; caesar-api gir to verdier, status og svar. Vi samler dem i en liste for å sammenligne.
(define (api body)
  (call-with-values (lambda () (caesar-api body)) list))

(define (ok output) (list 200 (hasheq 'output output)))
(define (feil melding) (list 400 (hasheq 'error melding)))

(test-case "caesar-api koder og dekoder"
  (check-equal? (api (hasheq 'text "hei" 'shift 3 'mode "encode")) (ok "khl"))
  (check-equal? (api (hasheq 'text "khl" 'shift 3 'mode "decode")) (ok "hei"))
  (check-equal? (api (hasheq 'text "" 'shift 5 'mode "encode")) (ok "")))

(test-case "caesar-api tåler negative og enorme forskyvninger"
  (check-equal? (api (hasheq 'text "abc" 'shift -2 'mode "encode")) (ok "å a"))
  (check-equal? (api (hasheq 'text "abc" 'shift (+ (expt 10 30) 1) 'mode "encode")) (ok "lmn")))

(test-case "caesar-api gir 400 med riktig melding"
  (check-equal? (api #f) (feil "text must be a string"))                                  ; ugyldig JSON
  (check-equal? (api '(1 2 3)) (feil "text must be a string"))                            ; JSON som ikke er et objekt
  (check-equal? (api (hasheq 'shift 1 'mode "encode")) (feil "text must be a string"))
  (check-equal? (api (hasheq 'text 5 'shift 1 'mode "encode")) (feil "text must be a string"))
  (check-equal? (api (hasheq 'text "a" 'shift 1.5 'mode "encode")) (feil "shift must be an integer"))
  (check-equal? (api (hasheq 'text "a" 'shift "1" 'mode "encode")) (feil "shift must be an integer"))
  (check-equal? (api (hasheq 'text "a" 'shift 1 'mode "rot")) (feil "mode must be encode or decode"))
  (check-equal? (api (hasheq 'text "a" 'shift 1)) (feil "mode must be encode or decode")))

(test-case "caesar-api: teksten kan ha opptil max-text-length tegn"
  (check-equal? (car (api (hasheq 'text (make-string max-text-length #\a) 'shift 1 'mode "encode"))) 200)
  (check-equal? (api (hasheq 'text (make-string (+ max-text-length 1) #\a) 'shift 1 'mode "encode"))
                (feil "text too long")))


;; ---------------------------------------------------------------- eksempelfilene

;; c13.txt er klartekst, og s13.txt er den samme teksten kodet med 13
(define-runtime-path c13-path "c13.txt")
(define-runtime-path s13-path "s13.txt")

(test-case "c13.txt kodet med 13 er s13.txt, og omvendt"
  (check-equal? (shift-string (file->string c13-path) 13) (file->string s13-path))
  (check-equal? (shift-string (file->string s13-path) -13) (file->string c13-path)))
