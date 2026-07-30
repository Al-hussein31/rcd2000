      PROGRAM SLAB
C
C THIS PROGRAM ANALYSES AND DESIGN SLAB TO BS 8110
C 1997. THE PROGRAM DESIGNS UP TO 20 DIFFERENT PANELS -
C COMPRISING OF CANTILEVERS, SIMPLY SUPPORTED, CONTINUOUS
C AND TWO-WAY SLAB.
C
C PROGRAM DEVELOPED AND WRITTEN BY ENGR. V.O. OYENUGA.
C NOVEMBER 1998
C
      REAL LCAN(20), LSS(20), LCON(20,20), LX(20),
     +     LY(20), LC, LCO(20), LC1, LC2, MS, MT, MG, ML,
     +     MSC(20), MTC(20), MSS, MC, MSP(20)
      INTEGER O, IN, NP, PT(20), NPL(20), NSPAN(20),
     +        NPLC(20,20), CS, CASE(20), PC, PCO(20), IX
      CHARACTER*20 FNAME1, FNAME2, JOB, ENGR, DATE
      CHARACTER*3 BX, SPN, BN(20), INP, OTP
      CHARACTER*1 PASS
      DIMENSION H(20), UDL(20), PL(20,6), A(20,6),
     +          UDLC(20,20), UCO(20), PLC(20,20,6),
     +          AC(20,20,6), RCC(20,6), PCCO(20,6),
     +          PCC(20), ASC(20), ATC(20), RCT(20),
     +          APC(20), API(20), APCC(20,20),
     +          CANTMT(20,20), CANTLD(20,20),
     +          CTM(20), CTL(20), NS(20), ASP(20), SO(20)
C
      OPEN (1, FILE = 'CON')
      OPEN (2, FILE = 'LPT1')
C
      WRITE (1, 404)
      WRITE (1, 9) 'WELCOME TO SLAB ANALYSIS AND DESIGN TO BS 8110'
      WRITE (1, 19) 'PROGRAM DEVELOPED AND WRITTEN BY ENGR. V.O.',
     +              'OYENUGA.'
      WRITE (1, 29) 'NOVEMBER 1998'
      WRITE (1, 403)
C
      WRITE (1, 39) 'INPUT IS EXPECTED VIA SCREEN OR FILE'
      WRITE (1, 49) 'Please Enter letter -T- if the input is',
     +              'via the Terminal'
      WRITE (1, 49) 'Please Enter letter -F- if the input is',
     +              'via External File'
      READ (1, 239) INP
239   FORMAT (A1)
      IF ((INP .EQ. 'F') .OR. (INP .EQ. 'f')) THEN
         IN = 3
         WRITE (1, 59) 'Please Enter the Input Filename'
         READ (1, 699) FNAME1
         OPEN (3, FILE = FNAME1)
      ELSE
         IN = 1
      END IF
C
      WRITE (1, 404)
C
C FORMAT STATEMENTS
C
9     FORMAT (5X, A34)
19    FORMAT (5X, A41)
29    FORMAT (5X, A13)
39    FORMAT (5X, A38)
49    FORMAT (5X, A43, 1X, A18)
59    FORMAT (5X, A34)
239   FORMAT (A1)
403   FORMAT (3(/))
404   FORMAT (7(/))
699   FORMAT (A20)
C
      END
