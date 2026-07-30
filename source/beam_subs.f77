C
C     BEAM SUBROUTINES
C     FOR USE WITH THE MAIN BEAM PROGRAM
C
C     CONTAINS: BMADE, DEFLEC, STEEL, GAUSS, PAF
C
C----------------------------------------------------------------------
C
C     NOTE: BMADE is the main beam design subroutine. The body of
C     this subroutine spans pages 209-213 of Oyenuga's book which
C     are not included in the OCR extracts. The interface is
C     provided here. The subroutines it calls (DEFLEC, STEEL,
C     GAUSS, PAF) are fully implemented below.
C
      SUBROUTINE BMADE(JOB, ENGR, DATE, FCU, FY, FYV,
     +                 BNS, NSS, NMS, NDS, BS, BFS, HS,
     +                 HFS, TS1, TS2, CLS1, CLS2, CMS1,
     +                 CMS2, MS, LS, UDS, WTS, WBS, ABS,
     +                 NPS, PS, APS, NO, FNAME2, I, NB)
C
C     DUMMY ARGUMENTS - BODY NOT AVAILABLE IN OCR EXTRACTS
C
      CHARACTER*20 JOB, ENGR, DATE
      CHARACTER BNS*30, NDS*2
      DIMENSION MS(20), LS(20), UDS(20), WTS(20),
     +          WBS(20), ABS(20), NPS(20)
      DIMENSION PS(20,10), APS(20,10)
      DIMENSION NDS(21)
      CHARACTER FNAME2*20
C
C     LOCAL ARRAYS FOR CLAPEYRON THREE-MOMENT SOLUTION
C
      DIMENSION AG(21,21), Y(21), X(21), SUMAX(21)
      DIMENSION AM(20), SF(20), BM(20), AS1(20), AS2(20)
C
      WRITE(NO,188) 'BEAM DESIGN OUTPUT FOR ', BNS
      WRITE(NO,208)
      WRITE(NO,218) 'JOB:', JOB, 'ENGR:', ENGR
      WRITE(NO,228) 'DATE:', DATE
      WRITE(NO,238)
C
C     *** BODY OMITTED ***
C     Full implementation requires pages 209-213 of:
C     "Reinforced Concrete Design" by V.O. Oyenuga
C
      RETURN
      END
C
C----------------------------------------------------------------------
C
      SUBROUTINE DEFLEC(N, NN, B, D, ASB, AS, FY, M,
     +                  SPAN, HECK, ASD, DI)
C
C     CHECKS DEFLECTION USING BS 8110 BASIC
C     SPAN/EFFECTIVE-DEPTH RATIO METHOD
C
      CHARACTER*1 ANS
      INTEGER HECK
      REAL M, KT
C
      HECK = 1
      ASD = AS
      GO TO 5
C
    2 WRITE(1,9) 'MEMBER', N, 'CALCULATED STEEL IS:', ASD
      WRITE(1,19) 'ENTER THE DESIRED STEEL'
      READ(1,*) ASD
C
    5 KT = M / (B * D**2.0)
      FS = (0.667 * FY) * (AS / ASD)
      FACT = 120.0 * (0.9 + M / (B * D**2.0))
      FACT = 0.55 + (477.0 - FS) / FACT
      IF (NN .LT. 1) SR = 20.0
      IF (NN .GE. 1) SR = 26.0
      IF (FACT .GE. 2.0) FACT = 2.0
      DI = (SPAN * 1000.0) / (SR * FACT)
C
    9 FORMAT(1X,A6,1X,I2,1X,A20,1X,F8.2)
   19 FORMAT(5X,A22)
      RETURN
      END
C
C----------------------------------------------------------------------
C
      SUBROUTINE STEEL(M, B, BF, D, H, FCU, FY,
     +                 AST, ASB, HECK)
C
C     DESIGN BEAM REINFORCEMENT TO BS 8110
C     RETURNS TOP STEEL (AST) AND BOTTOM STEEL (ASB)
C     HECK = 0 IF SECTION IS OVER-REINFORCED
C
      REAL M, K, LA, KP
      INTEGER HECK
C
      HECK = 1
      AST = 0.0
      ASB = 0.0
C
      IF (FY .LE. 250.0) THEN
        AMIN = (0.25 * B * D) / 100.0
      ELSE
        AMIN = (0.13 * B * D) / 100.0
      END IF
C
      AMAX = 0.04 * B * H
      K = (M * 1.0E06) / (FCU * BF * D**2.0)
C
      IF (K .GT. 0.156) THEN
C       COMPRESSION STEEL REQUIRED
        Z = 0.77688 * D
        KP = 0.156
        X = (D - Z) / 0.45
        ASB = (K - KP) * FCU * B * D**2.0 /
     +        (0.95 * FY * (D - 0.5 * X))
        AST = KP * FCU * BF * D**2.0 / (0.95 * FY * Z)
     +        + ASB
      ELSE
        Z = D * (0.5 + SQRT(0.25 - K / 0.9))
        LA = Z / D
        IF (LA .GE. 0.95) Z = 0.95 * D
        X = (D - Z) / 0.45
        AST = (M * 1.0E06) / (0.95 * FY * Z)
      END IF
C
      IF (AST .LT. AMIN) AST = AMIN
      IF (ASB .LT. AMIN) ASB = AMIN
      IF (AST .GE. AMAX) HECK = 0
C
      RETURN
      END
C
C----------------------------------------------------------------------
C
      SUBROUTINE GAUSS(AG, Y, NG, NDIM, SUMAX, X)
C
C     GAUSSIAN ELIMINATION SOLVER FOR SIMULTANEOUS
C     LINEAR EQUATIONS USED IN THE THREE-MOMENT METHOD
C
      DIMENSION AG(NDIM,NDIM), Y(NDIM), X(NDIM),
     +          SUMAX(NDIM)
C
C     FORWARD ELIMINATION
C
      K = 0
 5005 K = K + 1
      DO 727 I = K+1, NG
        Z = AG(I,K) / AG(K,K)
        DO 737 J = K, NG
          AG(I,J) = AG(I,J) - Z * AG(K,J)
  737   CONTINUE
        Y(I) = Y(I) - Y(K) * Z
  727 CONTINUE
C
      IF (K .LT. (NG-1)) GO TO 5005
C
C     BACK SUBSTITUTION
C
      X(NG) = Y(NG) / AG(NG,NG)
C
      DO 747 I = NG-1, 1, -1
        SUMAX(I) = 0.0
        DO 757 J = I+1, NG
          SUMAX(I) = SUMAX(I) + X(J) * AG(I,J)
  757   CONTINUE
        X(I) = (Y(I) - SUMAX(I)) / AG(I,I)
  747 CONTINUE
C
      RETURN
      END
C
C----------------------------------------------------------------------
C
      FUNCTION PAF(X, W, D)
C
C     POINT LOAD FACTOR FOR CLAPEYRON'S THREE-MOMENT EQUATION
C     PAF = W * X * (D**2 - X**2) / D
C
      PAF = D**2.0 - X**2.0
      PAF = PAF / D
      PAF = PAF * W * X
C
      RETURN
      END
C
C----------------------------------------------------------------------
C
C     FORMAT STATEMENTS FOR BMADE OUTPUT
C
  188 FORMAT(15X,A45,A11,F5.1,1X,A8)
  208 FORMAT(1X)
  218 FORMAT(3X,A4,1X,A2,2X,F7.1,4X,F4.0,4X,A12)
  228 FORMAT(5X,A6,1X,F8.3,1X,A6)
  238 FORMAT(/80('-')/)
C
