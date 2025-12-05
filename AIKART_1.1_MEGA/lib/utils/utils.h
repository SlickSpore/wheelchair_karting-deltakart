/*
Wheelchair Karting® AIKART_1® Rev 1.0

=== =============== STEERING LIBRARY ============== ===

    Utility Library, contains macroes and constan-
    ts used in all of the environment.

    Written by Ettore and Danilo Caccioli
                                        5/12/2025
=======================================================
*/


/* Serial R/W Macroes */
#define S_PNT(a) Serial.print(a)
#define S_PNT_LN(a) Serial.println(a)
#define S_PNT_TB(a) S_PNT(a); S_PNT("\t")
#define S_GCH(a) a = Serial.read()

/* Pin Modes Macroes */
#define PIN_M(a, b) pinMode(a, b)
#define PIN_DW(a, b)   digitalWrite(a, b)