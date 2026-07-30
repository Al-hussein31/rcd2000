C PROGRAM BASE
C
C COLUMN BASE (ISOLATED FOOTING AND COMBINED) DESIGN
C TO BS8110. THE PROGRAM ANALYSES AND DESIGN UP TO
C 20 DIFFERENT BASES AND EACH COMBINED BASE MAY BE
C UP TO 20 SPANS.

      PARAMETER (PI = 3.14159265)
      CHARACTER*20 FNAME1, FNAME2
      CHARACTER*20 JOB, ENGR, DATE
      CHARACTER*20 BN(20)
      CHARACTER*1 ANS1, ANS2
      CHARACTER*1 TITLE, OVER*5, PASS*2, T
      INTEGER TY(20), BT(20), BTC(20,20), HECK, CT(20),
     +  CTC(20,20)
      REAL L1, L2, MT(20), MS(20), M1, M2, ML, MR, MWC,
     +  MAT(20,20)
      DIMENSION W(20), WC(20,20), A(20,20), A1(20), A2(20),
     +  DIA(20), ACI(20,20), AC2(20,20), DIAC(20,20),
     +  DWC(20,20), DW(20), NC(20), FM(20), SPAN(20),
     +  SUMAX(20), RHS(20), XMT(20), SH1(20), SHR(20),
     +  AS(20), AT(20), RS(20), SS(20), RT(20), ST(20)

      OPEN(1,FILE='CON')
      OPEN(2,FILE='LPT1')

      WRITE(1,999)
      WRITE(1,404)
      WRITE(1,404)
      WRITE(1,9) 'WELCOME TO BASE ANALYSIS AND DESIGN TO BS8110'
      WRITE(1,19) 'PROGRAM DEVELOPED AND WRITTEN BY ASROS LTD.'
      WRITE(1,29) 'JANUARY 1991'
      WRITE(1,403)

      WRITE(1,39) 'INPUT IS EXPECTED VIA SCREEN OR FILE'
      WRITE(1,49) 'Please Enter the letter - T - if the Input is',
     +  'via the Terminal'
      WRITE(1,49) 'Please Enter the letter - F - if the Input is',
     +  'via External File'
      WRITE(1,403)
      READ(1,59) ANS1
      IF((ANS1 .EQ. 'F') .OR. (ANS1 .EQ. 'f')) THEN
        WRITE(1,79) 'Enter the INPUT filename'
        READ(1,59) FNAME1
        OPEN(3, FILE=FNAME1)
        NI=3
      ELSE
        NI=1
      END IF

      IF(NI .EQ. 1) THEN
        WRITE(1,89) 'Enter JOB REFERENCE'
        READ(1,59) JOB
        WRITE(1,89) 'Enter DESIGN ENGINEER'
        READ(1,59) ENGR
        WRITE(1,89) 'Enter DESIGNING DATE'
        READ(1,59) DATE
        WRITE(1,99) 'Enter No. of BASES, PRESSURE, CONCRETE AND STEEL
     +STRESSES'
        READ(1,*) NB, PB, FCU, FY
        DO 27 I = 1, NB
          WRITE(1,219) 'FOR BASE', I
          WRITE(1,109) 'Enter BASE IDENTIFICATION NO:'
          READ(1,59) BN(I)
          WRITE(1,919) 'Enter Base TYPE - 1:SQUARE, 2:RECT, 3:COMBINED'
          READ(1,*) TY(I)
          IF(TY(I) .NE. 3) THEN
            WRITE(1,119) 'Enter base COL.TYPE - 1:RECT, 2:CIRC.'
            READ(1,*) CT(I)
            WRITE(1,129) 'Enter Col. LOAD, DIMENSIONS AND DOWEL
     +DIAMETER'
            IF(CT(I) .EQ. 1) READ(1,*) W(I), A1(I), A2(I), DW(I)
            IF(CT(I) .EQ. 2) READ(1,*) W(I), DIA(I), DW(I)
          ELSE IF(TY(I) .EQ. 3) THEN
            WRITE(1,139) 'Enter Total No. of COLUMNS on the BASE'
            READ(1,*) NC(I)
            WRITE(1,149) 'Enter Column TYPES for each COLUMN'
            READ(1,*) (CTC(I,J), J = 1, NC(I))
            DO 37 J = 1, NC(I)
              WRITE(1,159) 'For BASE', I, 'COLUMN', J, 'Enter:'
              WRITE(1,169) 'LOAD, DIST. From Col.1, DIMENSIONS AND
     +DOWEL DIA:'
              IF(CTC(I,J) .EQ. 1)
     +          READ(1,*) WC(I,J), A(I,J), ACI(I,J), AC2(I,J),
     +          DWC(I,J)
              IF(CTC(I,J) .EQ. 2)
     +          READ(1,*) WC(I,J), A(I,J), DIAC(I,J), DWC(I,J)
   37       CONTINUE
          END IF
   27   CONTINUE
      ELSE IF(NI .EQ. 3) THEN
        READ(3,59) JOB
        READ(3,59) ENGR
        READ(3,59) DATE
        READ(3,*) NB, PB, FCU, FY
        READ(3,*) (TY(I), I = 1, NB)
        DO 7 I = 1, NB
          READ(3,59) BN(I)
          IF(TY(I) .NE. 3) THEN
            READ(3,*) CT(I)
            IF(CT(I) .EQ. 1) READ(3,*) W(I), A1(I), A2(I), DW(I)
            IF(CT(I) .EQ. 2) READ(3,*) W(I), DIA(I), DW(I)
          ELSE IF(TY(I) .EQ. 3) THEN
            READ(3,*) NC(I)
            READ(3,*) (CTC(I,J), J = 1, NC(I))
            DO 17 J = 1, NC(I)
              IF(CTC(I,J) .EQ. 1)
     +          READ(3,*) WC(I,J), A(I,J), ACI(I,J), AC2(I,J),
     +          DWC(I,J)
              IF(CTC(I,J) .EQ. 2)
     +          READ(3,*) WC(I,J), A(I,J), DIAC(I,J), DWC(I,J)
   17       CONTINUE
          END IF
    7   CONTINUE
      END IF

      WRITE(1,404)
      WRITE(1,404)
      WRITE(1,404)
      WRITE(1,39) 'OUTPUT IS EXPECTED VIA PRINTER OR FILE'
      WRITE(1,49) 'Please Enter the letter - P - if the output is',
     +  'via the Printer'
      WRITE(1,49) 'Please Enter the letter - F - if the output is',
     +  'via External File'
      WRITE(1,403)
      READ(1,59) ANS2
      IF((ANS2 .EQ. 'F') .OR. (ANS2 .EQ. 'f')) THEN
        WRITE(1,79) 'Enter the OUTPUT filename'
        READ(1,59) FNAME2
        OPEN(4, FILE=FNAME2)
        NO=4
      ELSE
        NO=2
      END IF

      WRITE(1,404)
      WRITE(1,69) 'About to read - press <ENTER> when ready...'
      WRITE(1,404)
      PAUSE

    9 FORMAT(5X,A34)
   19 FORMAT(5X,A34)
   29 FORMAT(5X,A9,1X,A20,12X,A8,1X,A20)
   39 FORMAT(15X,A9,1X,A20,12X,A8,1X,A16)
   49 FORMAT(/5X,A9,1X,F6.0,1X,A2,1X,F6.0,1X,A2,13X,A8,1X,F5.0,
     +  1X,A2)
   59 FORMAT(5X,A9,33X,A8,1X,F8.3,1X,A4)
   69 FORMAT(/15X,A16,1X,F5.0,A21)
   79 FORMAT(5X,A21,1X,F8.3,1X,A5)
   89 FORMAT(15X,A9,1X,A1,F3.0,2X,A1,2X,F4.0,A14)
   99 FORMAT(5X,10X,A15/)
  109 FORMAT(/15X,A11/)
  119 FORMAT(5X,A26,1X,F4.2,1X,A8)
  129 FORMAT(//50X/)
  139 FORMAT(5X,A6,1X,F4.1,1X,A8,21X,A6,1X,F5.1,1X,A8/)
  149 FORMAT(3(/))
  159 FORMAT(5X,A9,33X,A23,1X,I2)
  169 FORMAT(5X,A31)
  219 FORMAT(/15X,A23)
  403 FORMAT(2(/))
  404 FORMAT(7(/))
  829 FORMAT(5X,A34)
  919 FORMAT(5X,A34)
  999 FORMAT(1X)

      END
