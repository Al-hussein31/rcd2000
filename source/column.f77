      PROGRAM COLUMN
C
C     REINFORCED CONCRETE COLUMN ANALYSIS AND DESIGN
C     TO BS 8110:1997
C
C     THIS PROGRAM ANALYSES AND DESIGNS AXIAL, UNIAXIAL,
C     AND BIAXIALLY LOADED COLUMNS. IT CAN HANDLE UP TO
C     40 COLUMNS.
C
C     TY(I) = 1:  AXIALLY LOADED
C     TY(I) = 2:  UNIAXIALLY LOADED
C     TY(I) = 3:  BIAXIALLY LOADED
C     CS(I) = 1:  RECTANGULAR SECTION
C     CS(I) = 2:  CIRCULAR SECTION
C
C     PROGRAM DEVELOPED AND WRITTEN BY V.O. OYENUGA
C     APRIL, 1999
C
      IMPLICIT REAL(L-N)
C
      DIMENSION
     + L(40), LE(40), M(40), MX(40), MY(40), MADD(40),
     + LEX(40), LEY(40), CID(40), MIX(40), MIY(40),
     + MI(40), PC(40)
      DIMENSION W(40), AX(40), AY(40), DIA(40),
     + ASC(40), SRX(40), SRY(40), BX(40), BY(40),
     + AG(40), NU(40), MUX(40), MUY(40)
C
      COMMON AX, AY, DIA
C
      INTEGER TY(40), CS(40), HECK, BRC(40), UC(40),
     +        NCOL, NO
      CHARACTER*20 FNAME1, FNAME2, JOB, ENGR, DATE
      CHARACTER*40 CID(40), TYPE(40)
      CHARACTER ANS1*1, SLEN*1, DECIDE*1, NOUT*1,
     +          PASS*2
C
      PARAMETER (PI = 3.1415927)
C
C     -----------------------------------------------------------------
C     INITIALIZE MOMENT ARRAYS
C     -----------------------------------------------------------------
C
      DO 777 I = 1, 40
        MX(I) = 0.0
  777 MY(I) = 0.0
C
C     -----------------------------------------------------------------
C     GENERAL STATEMENTS - WELCOME BANNER
C     -----------------------------------------------------------------
C
      OPEN(1, FILE='CON')
      WRITE(1,403)
      WRITE(1,9) 'WELCOME TO COLUMN ANALYSIS AND DESIGN'
      WRITE(1,9) 'TO BS 8110'
      WRITE(1,19) 'PROGRAM DEVELOPED AND WRITTEN BY'
      WRITE(1,19) 'V.O. OYENUGA'
      WRITE(1,29) 'APRIL, 1999'
      OPEN(2, FILE='LPT1')
      WRITE(1,403)
      WRITE(1,403)
C
    9 FORMAT(5X,A34)
   19 FORMAT(5X,A34)
   29 FORMAT(5X,A34)
  403 FORMAT(2(/))
  404 FORMAT(7(/))
C
C     -----------------------------------------------------------------
C     INPUT ROUTING - TERMINAL OR FILE
C     -----------------------------------------------------------------
C
      WRITE(1,39) 'INPUT IS EXPECTED VIA SCREEN OR FILE'
      WRITE(1,49) 'Please Enter the letter - T - if the',
     +            ' Input is via the Terminal'
      WRITE(1,49) 'Please Enter the letter - F - if the',
     +            ' Input is via External File'
      WRITE(1,403)
      READ(1,599) ANS1
  599 FORMAT(A1)
C
      IF ((ANS1 .EQ. 'T') .OR. (ANS1 .EQ. 't')) THEN
        NI = 1
      ELSE
        WRITE(1,79) 'Enter the INPUT file name'
        READ(1,59) FNAME1
        OPEN(3, FILE=FNAME1)
        NI = 3
      END IF
C
   39 FORMAT(5X,A34)
   49 FORMAT(5X,A34)
   59 FORMAT(A20)
   79 FORMAT(5X,A25)
C
C     -----------------------------------------------------------------
C     OUTPUT ROUTING - PRINTER OR FILE
C     -----------------------------------------------------------------
C
      WRITE(1,404)
      WRITE(1,404)
      WRITE(1,39) 'OUTPUT IS EXPECTED VIA PRINTER OR FILE'
      WRITE(1,49) 'Please Enter the letter - P - if the',
     +            ' Output is via the Printer'
      WRITE(1,49) 'Please Enter the letter - F - if the',
     +            ' Output is via External File'
      WRITE(1,403)
      READ(1,599) NOUT
C
      IF ((NOUT .EQ. 'P') .OR. (NOUT .EQ. 'p')) THEN
        NO = 2
      ELSE
        WRITE(1,79) 'Enter the Output FILE name'
        READ(1,59) FNAME2
        OPEN(4, FILE=FNAME2)
        NO = 4
      END IF
C
C     -----------------------------------------------------------------
C     READ GENERAL DESIGN DATA
C     -----------------------------------------------------------------
C
      IF (NI .EQ. 3) THEN
        READ(3,59) JOB
        READ(3,59) ENGR
        READ(3,59) DATE
        READ(3,*) PCU, FY, NCOL, PS, DH
        READ(3,*) (TY(I), I=1,NCOL)
        READ(3,*) (CS(I), I=1,NCOL)
      ELSE
        WRITE(1,139) 'ENTER JOB REFERENCE'
        READ(1,59) JOB
        WRITE(1,139) 'ENTER DESIGN ENGINEER'
        READ(1,59) ENGR
        WRITE(1,139) 'ENTER DESIGNING DATE'
        READ(1,59) DATE
        WRITE(1,159) 'ENTER CONCRETE, STEEL STRESSES,',
     +               ' NO. OF COLUMNS, MAX STEEL %, D/H'
        READ(1,*) PCU, FY, NCOL, PS, DH
        WRITE(1,139) 'ENTER COLUMN TYPES (1=AXIAL,',
     +               ' 2=UNIAXIAL, 3=BIAXIAL)'
        READ(1,*) (TY(I), I=1,NCOL)
        WRITE(1,139) 'ENTER COLUMN SHAPES (1=RECT,',
     +               ' 2=CIRCULAR)'
        READ(1,*) (CS(I), I=1,NCOL)
      END IF
C
  139 FORMAT(5X,A30)
  159 FORMAT(5X,A40)
C
C     -----------------------------------------------------------------
C     MAIN COLUMN DESIGN LOOP
C     -----------------------------------------------------------------
C
      DO 525 I = 1, NCOL
        WRITE(1,606) 'COLUMN NO. ', I
C
        IF (NI .EQ. 3) THEN
          READ(3,59) CID(I)
          READ(3,*) W(I), BX(I), BY(I), H(I), L(I),
     +              LE(I), LEX(I), LEY(I), M(I),
     +              MX(I), MY(I)
        ELSE
          WRITE(1,69) 'ENTER COLUMN ID'
          READ(1,59) CID(I)
          WRITE(1,69) 'ENTER W, BX, BY, H, L, LE,',
     +                ' LEX, LEY, M, MX, MY'
          READ(1,*) W(I), BX(I), BY(I), H(I), L(I),
     +              LE(I), LEX(I), LEY(I), M(I),
     +              MX(I), MY(I)
        END IF
C
  606   FORMAT(1X,/,15X,A12,2X,I2)
   69   FORMAT(5X,A30)
C
        IF (CS(I) .EQ. 1) THEN
C         RECTANGULAR COLUMN
          AX(I) = BX(I)
          AY(I) = BY(I)
          AG(I) = AX(I) * AY(I)
        ELSE
C         CIRCULAR COLUMN
          AG(I) = PI * (DIA(I)**2.0) / 4.0
        END IF
C
        IF (TY(I) .EQ. 1) THEN
C         AXIALLY LOADED
          CALL AXIAL(I, W(I), PS, PCU, FY, AG(I),
     +               HECK, ASC(I))
        ELSE IF (TY(I) .EQ. 2) THEN
C         UNIAXIALLY LOADED
          CALL UNIAX(W(I), PS, PCU, FY, AG(I), DH,
     +               H(I), BX(I), M(I), NU(I), MUX(I),
     +               HECK, ASC(I))
        ELSE IF (TY(I) .EQ. 3) THEN
C         BIAXIALLY LOADED
C         CHECK BIAXIAL MOMENT CAPACITY
          CALL UNIAX(W(I), PS, PCU, FY, AG(I), DH,
     +               H(I), BX(I), M(I), NU(I), MUX(I),
     +               HECK, ASC(I))
          CALL UNIAX(W(I), PS, PCU, FY, AG(I), DH,
     +               BY(I), H(I), M(I), NU(I), MUY(I),
     +               HECK, ASC(I))
C         BIAXIAL CHECK: (MX/MUX)^ALPHA + (MY/MUY)^ALPHA <= 1
        END IF
C
        IF (HECK .EQ. 1) THEN
C         SECTION INADEQUATE - CALL SIZE SUBROUTINE
          CALL SIZE(I, CS(I), H(I), BX(I), NCOL,
     +              AX(I), AY(I), DIA(I))
        END IF
C
        WRITE(NO, 5255) CID(I), I, ASC(I)
C
  525 CONTINUE
C
 5255 FORMAT(1X,A40,2X,I2,2X,F10.2)
C
      STOP
      END
C
C=======================================================================
C                     SUBROUTINES
C=======================================================================
C
      SUBROUTINE SIZE(I, CS, H, B, NCOL, AX, AY, DIA)
C
C     PROMPTS USER FOR NEW DIMENSIONS WHEN A COLUMN
C     SECTION IS INADEQUATE
C
      DIMENSION AX(NCOL), AY(NCOL), CS(NCOL), DIA(NCOL)
      INTEGER CS
C
      OPEN(1, FILE='CON')
      WRITE(1,9) 'FOR COLUMN NO.', I
      IF (CS(I) .EQ. 1) THEN
C       RECTANGULAR
        WRITE(1,19) 'SIZE OF ', H, ' BY ', B, 'mm NOT',
     +              ' ADEQUATE PLEASE'
        WRITE(1,29) 'Enter new DIMENSIONS - DEPTH AND WIDTH'
        READ(1,*) AX(I), AY(I)
      ELSE
C       CIRCULAR
        WRITE(1,39) 'SIZE OF ', DIA(I), 'mm DIA. NOT',
     +              ' ADEQUATE PLEASE'
        WRITE(1,29) 'Enter new DIMENSION - DIAMETER'
        READ(1,*) DIA(I)
      END IF
C
    9 FORMAT(1X,/,5X,A14,1X,I2)
   19 FORMAT(/,5X,A7,1X,F8.0,1X,A2,1X,F8.0,1X,A24)
   29 FORMAT(/,5X,A38/)
   39 FORMAT(/,5X,A7,1X,F8.0,1X,A27/)
C
      RETURN
      END
C
C=======================================================================
C
      SUBROUTINE STEEL(E, FY, FT)
C
C     CALCULATES STEEL STRESS (FT) FROM STRAIN (E)
C     USING BILINEAR STRESS-STRAIN MODEL TO BS 8110
C
      ES = FY / 210000.0
      IF (E .LE. ES) FT = E * 200000.0
      IF (E .GT. ES) FT = 0.95 * FY
      RETURN
      END
C
C=======================================================================
C
      SUBROUTINE AXIAL(I, P, PS, FCU, FY, AG, HECK, AST)
C
C     DESIGNS REINFORCEMENT FOR AXIALLY LOADED
C     COLUMN TO BS 8110
C
      INTEGER HECK
C
      HECK = 0
      AST = (P * 1000.0) - (0.35 * FCU * AG)
      AST = AST / (0.7 * FY - 0.35 * FCU)
C
      AMIN = 0.4 * AG / 100.0
      AMAX = PS * AG / 100.0
C
      IF (AST .LT. AMIN) AST = AMIN
      IF (AST .GT. AMAX) HECK = 1
C
      RETURN
      END
C
C=======================================================================
C
      SUBROUTINE UNIAX(P, PS, FCU, FY, AR, DH, H, B,
     +                 M, NNU, MMU, HECK, ASC)
C
C     DESIGNS REINFORCEMENT FOR UNIAXIALLY LOADED
C     COLUMN USING THE BS 8110 DESIGN CHART APPROACH
C
C     GENERATES NU/MU INTERACTION CURVES FROM FIRST
C     PRINCIPLES (STRAIN COMPATIBILITY) THEN SEARCHES
C     FOR THE REQUIRED STEEL AREA
C
      INTEGER HECK
      REAL NU(10,50), MU(10,50), KI, K2, AS(10,100),
     +     NNU, MMU, M
C
      OPEN(1, FILE='CON')
C
      ASC = 0.0
      NNU = 0.0
      MMU = 0.0
      HECK = 0
C
      KI = 0.4 * FCU
      K2 = 0.45
      AT = 0.0
      XH = 0.1
      NN = INT(PS / 0.1)
C
C     GENERATE NU/MU TABLE FOR 9 NEUTRAL AXIS DEPTHS
C     (XH = 0.2 TO 1.0) AND NN STEEL RATIOS
C
      DO 71 I = 1, 9
        XH = XH + 0.1
        DO 17 J = 1, NN
          AT = AT + 0.001
          AS(I,J) = AT
          HX = 1.0 / XH
          ESC = (1.0 - 0.1 * HX) * 0.0035
          ES = (0.9 * HX - 1.0) * 0.0035
          CALL STEEL(ESC, FY, FSC)
          CALL STEEL(ES, FY, FS)
          NU(I,J) = KI * XH + FSC * AT - FS * AT
          MU(I,J) = KI * XH * (0.5 - K2 * XH)
     +              + FSC * AT * (DH - 0.5)
          MU(I,J) = MU(I,J) - FS * AT * (0.5 - DH)
   17   CONTINUE
        AT = 0.003
   71 CONTINUE
C
C     SEARCH TABLE FOR REQUIRED STEEL AREA
C
      DD = 0.0
      ANBH = P * 1000.0 / (B * H)
      AMBH = M * 1.0E06 / (B * H**2.0)
C
      DO 37 J = 1, NN
        DO 371 I = 1, 9
          IF ((NU(I,J) .GE. ANBH) .AND.
     +        (MU(I,J) .GE. AMBH)) THEN
            NNU = (NU(I,J) * B * H) / 1000.0
            MMU = (MU(I,J) * B * H**2.0) / 1.0E06
            ASC = AS(I,J) * B * H
            DD = 1.0
          END IF
  371   CONTINUE
   37 CONTINUE
C
      IF (DD .EQ. 1.0) GO TO 47
C
C     LOAD EXCEEDS TABLE MAXIMUM
      IF ((ANBH .GT. NU(9,NN)) .OR.
     +    (AMBH .GT. MU(9,NN))) THEN
        ASC = 0.0
        HECK = 1
        GO TO 5
      END IF
C
C     CHECK MINIMUM AND MAXIMUM STEEL
   47 AMIN = 0.4 * AR / 100.0
      AMAX = PS * AR / 100.0
      IF (ASC .LT. AMIN) ASC = AMIN
      IF (ASC .GT. AMAX) HECK = 1
C
    5 RETURN
      END
