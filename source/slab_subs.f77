      SUBROUTINE TWOWAY(N, LX, LY, U, CN, HN, FCU, FY, SR, MS, AS,
     +                  MT, AT, ML, AL, MG, AG, AR, WL, WS, DN, FS,
     +                  FT, FL, FG, ASP, FF, FX)
      REAL LX, LY, K, MT, MS, MG, ML
      INTEGER CN, O, HECK
      DIMENSION DG(9), DL(9), DT(9), DS(9)
      DATA DG / 0.032, 0.037, 0.037, 0.047, 0.00, 0.045, 0.00,
     +          0.057, 0.00 /
      DATA DL / 0.024, 0.028, 0.028, 0.035, 0.035, 0.035, 0.043,
     +          0.043, 0.05 /
C
      K = LY / LX
      DS(1) = -0.0384 + 0.0816 * K - 0.0190 * K ** 2.0
      DT(1) = -0.0431 + 0.0970 * K - 0.0216 * K ** 2.0
      DS(2) = -0.0254 + 0.0691 * K - 0.0153 * K ** 2.0
      DT(2) = -0.0332 + 0.0914 * K - 0.0205 * K ** 2.0
      DS(3) = -0.0471 + 0.0945 * K - 0.0195 * K ** 2.0
      DT(3) = -0.0620 + 0.1254 * K - 0.0260 * K ** 2.0
      DS(4) = -0.0321 + 0.0843 * K - 0.0169 * K ** 2.0
      DT(4) = -0.0467 + 0.1184 * K - 0.0248 * K ** 2.0
      DS(5) = -0.0003 + 0.0438 * K - 0.0090 * K ** 2.0
      DT(5) = -0.0079 + 0.0680 * K - 0.0149 * K ** 2.0
      DS(6) = -0.0726 + 0.1356 * K - 0.0277 * K ** 2.0
      DT(6) = 0.00
      DS(7) = -0.0314 + 0.0970 * K - 0.0225 * K ** 2.0
      DT(7) = -0.0385 + 0.1250 * K - 0.0287 * K ** 2.0
      DS(8) = -0.0628 + 0.1337 * K - 0.0271 * K ** 2.0
      DT(8) = 0.00
      DS(9) = -0.0612 + 0.1509 * K - 0.0335 * K ** 2.0
      DT(9) = 0.00
C
C DESIGN - SHORT SPAN
C
      MS = DS(CN) * U * LX ** 2.0
      FS = DS(CN)
      D = HN - 25.0
      CALL STEEL(MS, D, FCU, FY, HECK, AST)
      IF (HECK .EQ. 0) HN = HN + 25
      IF (HECK .EQ. 0) GO TO 5
      AS = AST
      MT = DT(CN) * U * LX ** 2.0
      FT = DT(CN)
      CALL STEEL(MT, D, FCU, FY, HECK, AST)
      IF (HECK .EQ. 0) HN = HN + 25
      IF (HECK .EQ. 0) GO TO 5
      AT = AST
C
C DESIGN - LONG SPAN
C
      ML = DL(CN) * U * LX ** 2.0
      FL = DL(CN)
      D = D - 14.0
      CALL STEEL(ML, D, FCU, FY, HECK, AST)
      IF (HECK .EQ. 0) HN = HN + 25
      IF (HECK .EQ. 0) GO TO 5
      AL = AST
      MG = DG(CN) * U * LX ** 2.0
      FG = DG(CN)
      CALL STEEL(MG, D, FCU, FY, HECK, AST)
      IF (HECK .EQ. 0) HN = HN + 25
      IF (HECK .EQ. 0) GO TO 5
      AG = AST
C
C CHECK FOR DEFLECTION
C
      D = D + 14
      HECK = 1
      CALL DEFLEC(N, 4, D, AS, FY, LX, MS, SR, HECK, DN, ASN, ASP,
     +            FF, FX)
      AS = ASN
      IF (HECK .EQ. 0) HN = HN + 25
      IF (HECK .EQ. 0) GO TO 5
C
C TORSIONAL STEEL
C
      AR = 0.75 * AS
      AM = 0.25 * 1000. * HN / 100.0
      IF (AR .LT. AM) THEN
         AR = AM
      END IF
C
C CALCULATE EQUIVALENT BEAM LOADS
C
      WS = (1.0 / 3.0) * U * LX
      WL = (0.5 * U * LX) * (1.0 - (1.0 / (3.0 * K ** 2.0)))
C
      RETURN
      END
C
      SUBROUTINE TWTYPE
      OPEN (1, FILE = 'CON')
      WRITE (1, 9) 'ENTER -1- FOR INTERIOR PANEL'
      WRITE (1, 9) 'ENTER -2- FOR ONE SHORT DISCONTINUOUS'
      WRITE (1, 9) 'ENTER -3- FOR ONE LONG DISCONTINUOUS'
      WRITE (1, 9) 'ENTER -4- FOR TWO ADJACENT EDGES DISCONTINUOUS'
      WRITE (1, 9) 'ENTER -5- FOR TWO SHORT EDGES DISCONTINUOUS'
      WRITE (1, 9) 'ENTER -6- FOR TWO LONG EDGES DISCONTINUOUS'
      WRITE (1, 9) 'ENTER -7- FOR THREE EDGES DISCONT. - 1 LONG CONT.'
      WRITE (1, 9) 'ENTER -8- FOR THREE EDGES DISCONT. - 1 SHORT CONT.'
      WRITE (1, 9) 'ENTER -9- FOR FOUR EDGES DISCONTINUOUS'
9     FORMAT (15X, A50)
      RETURN
      END
C
      SUBROUTINE STYPE(IC, BC)
      CHARACTER BC * 3
      OPEN (1, FILE = 'CON')
      WRITE (1, 19) 'ENTER PANEL NO. NO.'
      READ (1, 29) BC
      WRITE (1, 9) 'ENTER -1- FOR CANTILEVER SLAB'
      WRITE (1, 9) 'ENTER -2- FOR S. SUPPORTED SLAB'
      WRITE (1, 9) 'ENTER -3- FOR CONTINUOUS SLAB'
      WRITE (1, 9) 'ENTER -4- FOR TWO WAY SLAB'
      READ (1, *) IC
9     FORMAT (/5X, A32)
19    FORMAT (5X, A19)
29    FORMAT (A3)
      RETURN
      END
C
      SUBROUTINE STEEL(M, D, FCU, FY, HECK, AST)
      REAL M, K, LA, H
      INTEGER HECK
      H = D + 25
      HECK = 1
      AST = 0.00
      K = (M * 1.E06) / (FCU * 1000. * D ** 2.0)
      IF (K .GT. 0.156) HECK = 0
      IF (HECK .EQ. 0) GOTO 35
      LA = 0.5 + SQRT(0.25 - K / 0.9)
      IF (LA .GE. 0.95) LA = 0.95
      AST = (M * 1.0E06) / (0.95 * FY * LA * D)
C
C MINIMUM STEEL CHECK
C
      IF (FY .LE. 250) C = 0.24
      IF (FY .GT. 250) C = 0.13
      AM = (C * 1000. * H) / 100.0
      IF (AM .GT. AST) AST = AM
35    RETURN
      END
C
      SUBROUTINE DEFLEC(N, I, D, AS, FY, SPAN, M, SR, HECK, DI, ASD,
     +                  A, FS, FACT)
      CHARACTER*1 ANS
      INTEGER HECK
      REAL M, KT
      OPEN (1, FILE = 'CON')
      HECK = 1
      ASD = AS
      GOTO 5
C
15    WRITE (1, 9) 'PANEL ', N, ': CALCULATED/CHOSEN STEEL IS: ', ASD
      WRITE (1, 19) 'ENTER THE DESIRED STEEL'
      READ (1, *) ASD
C
5     KT = M / (1000.00 * D ** 2.0)
      PS = (0.667 * FY) * (AS / ASD)
      FACT = 120.00 * (0.9 + KT)
      FACT = 0.55 + (477.00 - PS) / FACT
      IF (FACT .GT. 2.0) FACT = 2.0
      DI = (SPAN / (SR * FACT)) * 1000.
      IF (DI .GT. D) THEN
         DPS = D + 25
         WRITE (1, 79) 'Present total depth of slab = ', DPS, 'mm'
         WRITE (1, 39) 'Deflection not OK - Increase Steel? - Y/N'
         WRITE (1, 29) 'Enter Y for YES and N for NO'
25       READ (1, 49) ANS
         IF ((ANS .EQ. 'n') .OR. (ANS .EQ. 'N')) HECK = 0
         IF (HECK .EQ. 0) GO TO 35
         IF ((ANS .EQ. 'Y') .OR. (ANS .EQ. 'y')) GOTO 15
      END IF
C
9     FORMAT (/5X, A5, 2X, I2, 1X, A27, 2X, F6.1)
19    FORMAT (/5X, A24)
29    FORMAT (/5X, A28)
39    FORMAT (15X, A41)
49    FORMAT (A1)
79    FORMAT (/10X, A30, F4.0, A2)
35    RETURN
      END
C
      SUBROUTINE CANTI(N, FCU, FY, L, HN, U, NPL, PL, APC, SR, MC,
     +                 ACT, V, DN, AXP, FF, FX)
      REAL MC, L
      INTEGER HECK
      DIMENSION PL(20), APC(20)
      V = U * L
      MC = U * L ** 2.0 / 2.0
      IF (NPL .NE. 0) THEN
         DO 7 I = 1, NPL
            MC = MC + PL(I) * APC(I)
7           V = V + PL(I)
      END IF
5     D = HN - 25.0
      HECK = 1
      CALL STEEL(MC, D, FCU, FY, HECK, AST)
      IF (HECK .EQ. 0) HN = HN + 25
      IF (HECK .EQ. 0) GO TO 5
      RETURN
      END
