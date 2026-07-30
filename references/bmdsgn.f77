      PROGRAM BMDSGN
      REAL MMT, K, LA
C Program for the design of a rectangular beam
C Input is via the terminal and output via printer.
      OPEN (1, FILE ='CON')
      OPEN (2, FILE ='PRN')
C SPAN - beam length, UDL - Beam load, MMT -Beam moment and SHR - beam shear
C D-Beam effective depth, B-Beam width, FCU - concrete stress and FY -steel stress,
C FYV - steel stress (stirrups).
C Read in all the necessary data.
   25 READ(1,*) SPAN, UDL, D, B, FCU, FY, FYV
C Calculate the bending moment and shearing force.
      MMT = 0.125 * UDL * SPAN ** 2.0
      SHR = 0.5 * UDL * SPAN
C Carry out all necessary design checks.
      K = (MMT * 1.0E06) / (FCU * B * D ** 2.0)
      IF (K .LE. 0.156) GO TO 35
      D = D + 50.0
      GO TO 25
   35 LA = 0.5 + (0.25 - K / 0.9) ** 0.5
      IF (LA .GT. 0.95) LA = 0.95
C Calculate steel area.
      AS = (MMT * 1.0E06) / (0.95 * FY * LA * D)
C Check and design for shear.
      VS = (SHR * 1.0E03) / (B * D)
      STPER = (100.0 * AS) / (B * D)
      READ(1,*) VC, ASV
      IF (VC .GT. VS) GO TO 45
      SV = (0.95 * FYV * ASV) / (B * (VS - VC))
      GO TO 55
   45 SV = 300.00
C Write out the results.
   55 WRITE(2, 101) 'MOMENT =', MMT, 'kN.m.'
  101 FORMAT(1X, A8, F7.3, A5)
      WRITE(2, 102) 'SHEAR FORCE = ', SHR, 'kN.'
  102 FORMAT(1X, A14, F7.3, A3)
      WRITE(2, 103) 'STEEL REQUIRED = ', AS, '(sq.mm)'
  103 FORMAT(1X, A17, F6.1, A6)
      WRITE(2, 104) 'LINK SPACING = ', SV, 'mm c/c'
  104 FORMAT(1X, A15, F6.1, A6)
      END
