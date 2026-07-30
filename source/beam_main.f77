      PROGRAM BEAM
C
C     REINFORCED CONCRETE BEAM ANALYSIS AND DESIGN
C     TO BS 8110:1997
C
C     ANALYSIS OF STATICALLY DETERMINATE AND INDETERMINATE
C     BEAMS USING THE CLAPEYRON'S THREE MOMENTS EQUATIONS.
C
C     THIS PROGRAM CAN HANDLE A MAXIMUM OF 20 BEAMS OF
C     20 SPANS EACH.
C
C     THE PROGRAM DETERMINES THE JOINT MOMENTS, SPAN MOMENTS,
C     SHEAR AND REACTIONS AND DESIGNS THE BEAM TO BS 8110:1997.
C
C     PROGRAM DEVELOPED AND WRITTEN BY V.O. OYENUGA
C     JANUARY, 1999
C
      CHARACTER*20 JOB, ENGR, DATE, FNAME1, FNAME2
      CHARACTER NDD*2, BN*30, NQS*2, ANS1*1,
     +          NOUT*1, BNS*30, PASS*3
      DIMENSION BN(20), NDD(20,21), NDS(21)
C
      REAL L(20,20), IV(20), B(20), BF(20), H(20), HF(20),
     +     CLD1(20), CMT1(20), CLD2(20), CMT2(20),
     +     UD(20,20), WT(20,20)
      REAL WB(20,20), AB(20,20), P(20,20,10), AP(20,20,10)
      REAL LS(20), UDS(20), WTS(20), WBS(20), ABS(20),
     +     PS(20,10), APS(20,10)
      INTEGER M(20,20), NPL(20,20), MS(20), NPS(20),
     +        NS(20), NM(20)
      INTEGER TS1, TS2, TY1(20), TY2(20)
C
      OPEN(6, FILE='CON')
      WRITE(6,403)
      WRITE(6,9) 'WELCOME TO BEAM ANALYSIS AND DESIGN'
      WRITE(6,9) 'TO BS 8110'
      WRITE(6,19) 'PROGRAM DEVELOPED AND WRITTEN BY'
      WRITE(6,19) 'V.O. OYENUGA'
      WRITE(6,29) 'JANUARY, 1999'
      WRITE(6,403)
C
    9 FORMAT(5X,A34)
   19 FORMAT(5X,A34)
   29 FORMAT(5X,A34)
C
      WRITE(6,39) 'INPUT IS EXPECTED VIA SCREEN OR FILE'
      WRITE(6,49) 'Please Enter the letter - T - if the',
     +            ' Input is via the Terminal'
      WRITE(6,49) 'Please Enter the letter - F - if the',
     +            ' Input is via External File'
      WRITE(6,403)
      READ(6,899) ANS1
  899 FORMAT(A1)
C
      IF ((ANS1 .EQ. 'T') .OR. (ANS1 .EQ. 't')) THEN
        NI = 6
      ELSE
        WRITE(6,79) 'Enter the INPUT file name'
        READ(6,59) FNAME1
        OPEN(1, FILE=FNAME1)
        NI = 1
      END IF
C
   39 FORMAT(5X,A34)
   49 FORMAT(5X,A34)
   59 FORMAT(A20)
   79 FORMAT(5X,A25)
C
      WRITE(6,404)
      WRITE(6,404)
      WRITE(6,39) 'OUTPUT IS EXPECTED VIA PRINTER OR FILE'
      WRITE(6,49) 'Please Enter the letter - P - if the',
     +            ' Output is via the Printer'
      WRITE(6,49) 'Please Enter the letter - F - if the',
     +            ' Output is via External File'
      WRITE(6,403)
      READ(6,899) NOUT
C
      IF ((NOUT .EQ. 'P') .OR. (NOUT .EQ. 'p')) THEN
        NO = 4
        OPEN(2, FILE='LPT1')
      ELSE
        WRITE(6,79) 'Enter the Output FILE name'
        READ(6,59) FNAME2
        NO = 4
      END IF
C
  403 FORMAT(2(/))
  404 FORMAT(7(/))
C
      IF (NI .EQ. 1) THEN
        READ(1,59) JOB
        READ(1,59) ENGR
        READ(1,59) DATE
        READ(1,*) NB, FCU, FY, FYV
      ELSE
        WRITE(6,139) 'ENTER JOB REFERENCE'
        READ(6,59) JOB
        WRITE(6,139) 'ENTER DESIGN ENGINEER'
        READ(6,59) ENGR
        WRITE(6,139) 'ENTER DESIGNING DATE'
        READ(6,59) DATE
        WRITE(6,159) 'ENTER NO. OF BEAMS, CONCRETE,',
     +               ' STEEL AND STIRRUP STRESSES'
        READ(6,*) NB, FCU, FY, FYV
      END IF
C
  139 FORMAT(5X,A30)
  159 FORMAT(5X,A40)
C
      DO 27 I = 1, NB
        WRITE(6,606) 'Reading for Beam No. ', I
C
        IF (NI .EQ. 1) THEN
          READ(1,599) BN(I)
          READ(1,*) NS(I), NM(I)
          READ(1,919) (NDD(I,J), J=1,NS(I))
          READ(1,*) B(I), BF(I), H(I), HF(I)
          IF (H(I) .LT. 75.0) H(I) = 75.0
          READ(1,*) TY1(I), CLD1(I), CMT1(I)
          READ(1,*) TY2(I), CLD2(I), CMT2(I)
C
          DO 17 J = 1, NM(I)
            READ(1,*) M(I,J), L(I,J), UD(I,J), WT(I,J),
     +                WB(I,J), AB(I,J), NPL(I,J)
            IF (NPL(I,J) .NE. 0) THEN
              READ(1,*) (P(I,J,K), K=1,NPL(I,J)),
     +                  (AP(I,J,K), K=1,NPL(I,J))
            END IF
   17     CONTINUE
        ELSE
          WRITE(6,399) 'Enter Beam ID. No.'
          READ(6,599) BN(I)
          WRITE(6,69) 'Enter No. of Supports, Members'
          READ(6,*) NS(I), NM(I)
          WRITE(6,399) 'Enter Supports Grid Numbers -',
     +                 ' 2 Spaces for each'
          READ(6,919) (NDD(I,J), J=1,NS(I))
          WRITE(6,169) 'Enter B, BF, H, HF'
          READ(6,*) B(I), BF(I), H(I), HF(I)
          IF (H(I) .LT. 75.0) H(I) = 75.0
          WRITE(6,169) 'Enter TY1, CLD1, CMT1'
          READ(6,*) TY1(I), CLD1(I), CMT1(I)
          WRITE(6,169) 'Enter TY2, CLD2, CMT2'
          READ(6,*) TY2(I), CLD2(I), CMT2(I)
C
          DO 18 J = 1, NM(I)
            WRITE(6,179) 'Enter M, L, UD, WT, WB, AB,',
     +                   ' NPL for Member ', J
            READ(6,*) M(I,J), L(I,J), UD(I,J), WT(I,J),
     +                WB(I,J), AB(I,J), NPL(I,J)
            IF (NPL(I,J) .NE. 0) THEN
              WRITE(6,179) 'Enter P and AP for Member ', J
              READ(6,*) (P(I,J,K), K=1,NPL(I,J)),
     +                  (AP(I,J,K), K=1,NPL(I,J))
            END IF
   18     CONTINUE
        END IF
C
  599   FORMAT(A30)
  606   FORMAT(1X,/,15X,A20,2X,I2)
  919   FORMAT(20(A2))
   69   FORMAT(5X,A30)
  169   FORMAT(5X,A30)
  179   FORMAT(5X,A30,I2)
  399   FORMAT(5X,A30)
C
        BNS = BN(I)
        NSS = NS(I)
        NMS = NM(I)
        DO 37 J = 1, NS(I)
   37   NDS(J) = NDD(I,J)
        BS = B(I)
        BFS = BF(I)
        HS = H(I)
        HFS = HF(I)
        TS1 = TY1(I)
        CLS1 = CLD1(I)
        CMS1 = CMT1(I)
        TS2 = TY2(I)
        CLS2 = CLD2(I)
        CMS2 = CMT2(I)
C
        DO 47 J = 1, NM(I)
          MS(J) = M(I,J)
          LS(J) = L(I,J)
          UDS(J) = UD(I,J)
          WTS(J) = WT(I,J)
          WBS(J) = WB(I,J)
          ABS(J) = AB(I,J)
          NPS(J) = NPL(I,J)
          DO 57 K = 1, NPL(I,J)
            PS(J,K) = P(I,J,K)
   57     APS(J,K) = AP(I,J,K)
   47   CONTINUE
C
        CALL BMADE(JOB, ENGR, DATE, FCU, FY, FYV,
     +             BNS, NSS, NMS, NDS, BS, BFS, HS,
     +             HFS, TS1, TS2, CLS1, CLS2, CMS1,
     +             CMS2, MS, LS, UDS, WTS, WBS, ABS,
     +             NPS, PS, APS, NO, FNAME2, I, NB)
C
   27 CONTINUE
C
      STOP
      END
