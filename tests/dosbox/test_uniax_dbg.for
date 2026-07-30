      PROGRAM TSTUDBG
      INTEGER HECK
      REAL NNU, MMU
      OPEN(5, FILE='dbg_out.txt')
      OPEN(6, FILE='table_out.txt')
C
      CALL UNIAX(1000.0, 6.0, 25.0, 460.0, 90000.0, 0.9,
     +           300.0, 300.0, 50.0, NNU, MMU, HECK, ASC)
      WRITE(5,10) 'ASC=', ASC
      WRITE(5,10) 'NU=', NNU
      WRITE(5,10) 'MU=', MMU
      WRITE(5,20) 'HECK=', HECK
   10 FORMAT(A,F12.4)
   20 FORMAT(A,I5)
      CLOSE(5)
      CLOSE(6)
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
      SUBROUTINE UNIAX(P, PS, FCU, FY, AR, DH, H, B,
     +                 M, NNU, MMU, HECK, ASC)
      INTEGER HECK
      REAL NU(10,60), MU(10,60), KI, K2, AS(10,100),
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
C
      DO 71 I = 1, 9
        XH = XH + 0.1
        WRITE(6,99) 'XH=', XH
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
          IF (J .EQ. 1 .OR. J .EQ. NN/2 .OR. J .EQ. NN) THEN
            WRITE(6,98) ' J=',J,' AT=',AT,' NU=',NU(I,J),
     +                  ' MU=',MU(I,J)
          END IF
   17   CONTINUE
        AT = 0.003
   71 CONTINUE
C
      ANBH = P * 1000.0 / (B * H)
      AMBH = M * 1.0E06 / (B * H**2.0)
      WRITE(5,96) 'ANBH=', ANBH, 'AMBH=', AMBH
   96 FORMAT(2(A,F12.4))
C
      DD = 0.0
      DO 37 J = 1, NN
        DO 371 I = 1, 9
          IF ((NU(I,J) .GE. ANBH) .AND.
     +        (MU(I,J) .GE. AMBH)) THEN
            NNU = (NU(I,J) * B * H) / 1000.0
            MMU = (MU(I,J) * B * H**2.0) / 1.0E06
            ASC = AS(I,J) * B * H
            DD = 1.0
            WRITE(5,97) 'MATCH I=',I,' J=',J,' AS=',AS(I,J),
     +                  ' NU=',NU(I,J),' MU=',MU(I,J)
   97       FORMAT(A,I4,A,I4,4(A,F12.4))
            GO TO 47
          END IF
  371   CONTINUE
   37 CONTINUE
C
      IF (DD .EQ. 0.0) THEN
        IF ((ANBH .GT. NU(9,NN)) .OR.
     +      (AMBH .GT. MU(9,NN))) THEN
          ASC = 0.0
          HECK = 1
          GO TO 5
        END IF
      END IF
C
   47 AMIN = 0.4 * AR / 100.0
      AMAX = PS * AR / 100.0
      IF (ASC .LT. AMIN) ASC = AMIN
      IF (ASC .GT. AMAX) HECK = 1
    5 RETURN
   99 FORMAT(A,F8.4)
   98 FORMAT(A,I4,A,F10.4,A,F10.4,A,F10.4)
      END
