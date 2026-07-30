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
C----------------------------------------------------------------------
C
C     FORMAT STATEMENTS AND SHEAR LINK CALCULATIONS
C     (FROM PAGE 213)
C
  129 FORMAT(15X,A42)
    8 FORMAT(1X,23X,A34)
   18 FORMAT(23X,A34)
   28 FORMAT(5X,A9,1X,A20,12X,A8,1X,A20)
   38 FORMAT(/5X,A9,1X,A25,7X,A5,1X,F5.0,1X,A2,1X,F5.0,1X,A2)
   48 FORMAT(5X,A7,6(1X))
C
      WRITE(NO,188) 'NOTE: Spacing Based on 2 Legs 10mm Dia. Bar',
     +              'with FY = ', FYV, 'N/Sq.mm'
      WRITE(NO,238)
      WRITE(NO,218) 'SUPT', NDD(NS), CLD2, SVC2
C
      IF (NPL(I) .NE. 0) THEN
        WRITE(NO,278) (P(I,J), J = 1, NPL(I)),
     +                (AP(I,J), J = 1, NPL(I))
      END IF
 7007 CONTINUE
C
  285 FORMAT(5X,1X,A4,6X,A3,5X,A7,3X,A7,3X,A5,4X,A3,4X,A8)
  255 FORMAT(5X,A12)
  268 FORMAT(5X,A2,A4,A2,2X,F6.2,4X,F6.2,4X,F6.2,4X,F5.3,6X,I2)
  278 FORMAT(15X,12(F6.2,1X))
C
      WRITE(NO,658) 'A. MOMENTS'
      WRITE(NO,68) 'AAAAAAAAAAAAAAAA'
      WRITE(NO,78) 'SPAN REINFORCEMENTS'
      WRITE(NO,88) 'Span', 'Length', 'Moment', 'Steel (Sq. mm)',
     +             'Provide'
      WRITE(NO,98) 'S/N', '(m)', '(kN.m)', 'Bottom', 'Top'
C
      DO 907 I = 1, NM
  907   WRITE(NO,108) NX(I), '-', NY(I), L(I), SPMT(I), AS(I),
     +                ASC(I), 'T'
C
      WRITE(NO,118) 'SUPPORT REINFORCEMENTS'
      WRITE(NO,128) 'Supt', 'Reaction', 'Moment', 'Steel (Sq. mm)',
     +              'Provide'
      WRITE(NO,138) 'S/N', '(kN)', '(kN.m)', 'Top', 'Bottom'
C
      DO 917 I = 1, NS
  917   WRITE(NO,148) NDD(I), REACTN(I), MT(I), AT(I), ATC(I),
     +                'T'
C
      WRITE(NO,208)
      WRITE(NO,68) 'B. SHEAR'
      WRITE(NO,68) 'AAAAAAAAAAAAAAAA'
      WRITE(NO,158) 'SPAN', 'LEFT SUPPORT', 'RIGHT SUPPORT'
      WRITE(NO,168) 'S/N', 'Shear', 'Spacing', 'Provide', 'Shear',
     +              'Spacing', 'Provide'
C
      IF (CMT1 .NE. 0.00) THEN
        WRITE(NO,218) 'SUPT', NDD(1), CLD1, SVC1
      END IF
C
      DO 927 I = 1, NM
  927   WRITE(NO,178) NX(I), '-', NY(I), SFN1(I), SV1(I),
     +                SFN2(I), SV2(I)
C
      IF (CMT2 .NE. 0.00) THEN
        WRITE(NO,28) 'JOB REF: ', JOB, 'DATE: ', DATE
        WRITE(NO,402)
  402   FORMAT(1X)
        WRITE(NO,28) 'DESIGNED: ', ENGR, 'CHECKED: '
      END IF
C
      IF (IQ .NE. 1) THEN
        WRITE(NO,248) 'PAGE ', IQ, 'OF', NB
  248   FORMAT(56X,A4,1X,I2,1X,A2,1X,I2)
      END IF
C
      WRITE(NO,38) 'BEAM ID: ', BN, 'SIZE: ', H, 'BY', B, 'mm'
      WRITE(NO,48) 'SKETCH:'
      WRITE(NO,58) 'FCU = ', FCU, 'N/Sq.mm', 'FY = ', FY,
     +             'N/Sq.mm'
C
      MU = (0.156 * FCU * B * D**2.0) / 1.0E06
      WRITE(NO,228) 'Mu = ', MU, 'kN.m'
      WRITE(NO,258) 'Beam Loading'
      WRITE(NO,288) 'SPAN', 'UDL', 'TRIANG.', 'TRAPEZ.',
     +              'TR.DIST.', 'NPL', 'LOADS'
C
      DO 7007 I = 1, NM
        WRITE(NO,268) NX(I), '-', NY(I), UD(I), WT(I), WB(I),
     +                AB(I), NPL(I)
 7007 CONTINUE
C
      IF (IQ .EQ. 1) THEN
        WRITE(NO,8) 'BEAM ANALYSIS AND DESIGN BS 8110'
        WRITE(NO,18)
      END IF
C
C RESULTS OUTPUT
C
      WRITE(6,404)
      WRITE(6,404)
      WRITE(6,129) 'About to write - press <ENTER> when ready'
      WRITE(6,449) 'Beam Id. No. ', BN
  449 FORMAT(10X,A14,A30)
      WRITE(6,404)
      PAUSE
C
      AV2 = AT(I + 1)
      CALL SHEAR(V2, AV2, FYV, FCU, B, D, SV, HECK)
      IF (HECK .EQ. 0) H = H + 150
      IF (HECK .EQ. 0) GO TO 5
      SV2(I) = SV
C
C NOW FOR THE CANTILEVER ENDS
C
      IF (CMT1 .NE. 0.00) THEN
        VC = CLD1
        AVC = AT(1)
        CALL SHEAR(VC, AVC, FYV, FCU, B, D, SV, HECK)
        SVC1 = SV
        IF (HECK .EQ. 0) H = H + 150
        IF (HECK .EQ. 0) GO TO 5
      END IF
C
      IF (CMT2 .NE. 0.00) THEN
        VC = CLD2
        AVC = AT(NS)
        CALL SHEAR(VC, AVC, FYV, FCU, B, D, SV, HECK)
        SVC2 = SV
        IF (HECK .EQ. 0) H = H + 150
        IF (HECK .EQ. 0) GO TO 5
      END IF
C
C----------------------------------------------------------------------
C
C     SHEAR STRESS CHECK SUBROUTINE
C     (FROM PAGE 215)
C
      SUBROUTINE SHEAR(V, A, FY, FCU, B, D, SV, HECK)
      INTEGER HECK
C
      V = ABS(V)
      HECK = 1
C
      VV = (V * 1000.0) / (B * D)
      VM = 0.8 * SQRT(FCU)
      IF (VM .GT. 5.0) VM = 5.0
C
      IF (VV .GT. VM) THEN
        WRITE(1,9) 'PERMISSIBLE SHEAR STRESS EXCEEDED'
        WRITE(1,9) 'BEAM DEPTH INCREASED BY 50mm'
        HECK = 0
        GO TO 35
      END IF
C
      AC = (100.0 * A) / (B * D)
      IF (AC .GT. 3.00) AC = 3.00
      AC = AC**(1.0 / 3.0)
      DC = 400.0 / D
      IF (DC .LT. 1.0) DC = 1.0
      DC = DC**(1.0 / 4.0)
      VC = 0.63 * AC * DC
      HVC = 0.5 * VC
      PVC = VC + 0.40
C
      IF (VV .LT. HVC) SV = 0.75 * D
      IF ((HVC .LE. VV) .AND. (VV .LT. PVC)) THEN
        SV = (0.95 * FY * 157.0) / (0.4 * B)
      ELSE IF ((PVC .LE. VV) .AND. (VV .LE. VM)) THEN
        SV = (157.0 * 0.95 * FY) / (B * (VV - VC))
      END IF
C
      SP = 0.75 * D
      IF (SV .GT. SP) SV = SP
C
    9 FORMAT(/5X,A34/)
   35 RETURN
      END
C
