      PROGRAM TESTCL
      INTEGER HECK
      REAL NNU, MMU
      OPEN(5, FILE='test_cl_out.txt')
C
C     ---- Test 1: AXIAL ----
C     300x300 column, fcu=25, fy=460, P=1000kN, PS=6%, AG=90000
      AG = 300.0 * 300.0
      CALL AXIAL(1, 1000.0, 6.0, 25.0, 460.0, AG, HECK, AST)
      AMIN = 0.4 * AG / 100.0
      WRITE(5,10) '===== AXIAL TEST ====='
      WRITE(5,20) 'AG (sq.mm):', AG
      WRITE(5,20) 'AST (sq.mm):', AST
      WRITE(5,20) 'AMIN (sq.mm):', AMIN
      WRITE(5,30) 'HECK:', HECK
      WRITE(5,40) 'STEEL %:', AST/AG*100.0
C
C     ---- Test 2: UNIAX ----
C     P=1000kN, M=50kN.m, 300x300, fcu=25, fy=460, PS=6%, D/H=0.9
      CALL UNIAX(1000.0, 6.0, 25.0, 460.0, 90000.0, 0.9,
     +           300.0, 300.0, 50.0, NNU, MMU, HECK, ASC)
      WRITE(5,10) '===== UNIAX TEST ====='
      WRITE(5,20) 'ASC (sq.mm):', ASC
      WRITE(5,20) 'NU (kN):', NNU
      WRITE(5,20) 'MU (kN.m):', MMU
      WRITE(5,30) 'HECK:', HECK
      WRITE(5,40) 'STEEL %:', ASC/90000.0*100.0
   10 FORMAT(/A)
   20 FORMAT(A,F12.2)
   30 FORMAT(A,I5)
   40 FORMAT(A,F8.2)
      STOP
      END
C
      SUBROUTINE STEEL(E, FY, FT)
      ES = FY / 210000.0
      IF (E .LE. ES) FT = E * 200000.0
      IF (E .GT. ES) FT = 0.95 * FY
      RETURN
      END
C
      SUBROUTINE AXIAL(I, P, PS, FCU, FY, AG, HECK, AST)
      INTEGER HECK
      HECK = 0
      AST = (P * 1000.0) - (0.35 * FCU * AG)
      AST = AST / (0.7 * FY - 0.35 * FCU)
      AMIN = 0.4 * AG / 100.0
      AMAX = PS * AG / 100.0
      IF (AST .LT. AMIN) AST = AMIN
      IF (AST .GT. AMAX) HECK = 1
      RETURN
      END
C
      SUBROUTINE UNIAX(P, PS, FCU, FY, AR, DH, H, B,
     +                 M, NNU, MMU, HECK, ASC)
      INTEGER HECK
      REAL NU(10,50), MU(10,50), KI, K2, AS(10,100),
     +     NNU, MMU, M
      ASC = 0.0
      NNU = 0.0
      MMU = 0.0
      HECK = 0
      KI = 0.4 * FCU
      K2 = 0.45
      AT = 0.0
      XH = 0.1
      NN = INT(PS / 0.1)
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
      DD = 0.0
      ANBH = P * 1000.0 / (B * H)
      AMBH = M * 1.0E06 / (B * H**2.0)
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
      IF (DD .EQ. 1.0) GO TO 47
      IF ((ANBH .GT. NU(9,NN)) .OR.
     +    (AMBH .GT. MU(9,NN))) THEN
        ASC = 0.0
        HECK = 1
        GO TO 5
      END IF
   47 AMIN = 0.4 * AR / 100.0
      AMAX = PS * AR / 100.0
      IF (ASC .LT. AMIN) ASC = AMIN
      IF (ASC .GT. AMAX) HECK = 1
    5 RETURN
      END
