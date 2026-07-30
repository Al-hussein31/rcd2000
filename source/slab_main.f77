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
C OUTPUT FILE SELECTION
C
      WRITE (1, 49) 'Please Enter letter -F- if the output is',
     +              'via the File'
      WRITE (1, 49) 'Please Enter letter -P- if the output is',
     +              'via the Printer'
      READ (1, 239) OTP
      IF ((OTP .EQ. 'F') .OR. (OTP .EQ. 'f')) THEN
         O = 4
         WRITE (1, 59) 'Please Enter the Output File Name'
         READ (1, 699) FNAME2
         OPEN (4, FILE = FNAME2)
      ELSE
         O = 2
      END IF
C
C INITIAL INPUT - JOB REFERENCE, ENGINEER, DATE, MATERIALS
C
      IF (IN .EQ. 1) THEN
         WRITE (1, 404)
         WRITE (1, 404)
         WRITE (1, 404)
         WRITE (1, 209) 'ENTER JOB REFERENCE'
         READ (1, 699) JOB
         WRITE (1, 209) 'ENTER DESIGN ENGINEER'
         READ (1, 699) ENGR
         WRITE (1, 209) 'ENTER DESIGNING DATE'
         READ (1, 699) DATE
         WRITE (1, 79) 'ENTER CONCRETE & STEEL CHARACTERISTICS STRESS'
         READ (1, *) FCU, FY
      END IF
C
C PANEL COUNT AND TYPE INPUT
C
      IF (IN .EQ. 1) THEN
         WRITE (1, 89) 'ENTER TOTAL NO. OF PANELS'
         READ (1, *) NP
      END IF
      DO 7 I = 1, NP
         WRITE (1, 99) 'FOR INPUT NO.', I
         CALL STYPE(IX, BX)
         PT(I) = IX
         BN(I) = BX
 7    CONTINUE
C
C PANEL GEOMETRY INPUT
C
      DO 17 I = 1, NP
         WRITE (1, 929) 'FOR PANEL NO.', BN(I)
         IF (PT(I) .EQ. 1) THEN
            WRITE (1, 109) 'ENTER CANTILEVER SPAN, UDL, DEPTH AND',
     +                     'NO. OF POINT LOADS'
            READ (1, *) LCAN(I), UDL(I), H(I), NPL(I)
            IF (NPL(I) .NE. 0) THEN
               DO 27 J = 1, NPL(I)
                  WRITE (1, 129) 'FOR POINT LOAD', J,
     +                           'ENTER LOAD AND DIST. FROM FIXED END'
                  READ (1, *) PL(I,J), A(I,J)
 27            CONTINUE
            END IF
         ELSE IF (PT(I) .EQ. 2) THEN
            WRITE (1, 109) 'ENTER SLAB SPAN, UDL, DEPTH AND',
     +                     'NO. OF POINT LOADS'
            READ (1, *) LSS(I), UDL(I), H(I), NPL(I)
            IF (NPL(I) .NE. 0) THEN
               DO 37 J = 1, NPL(I)
                  WRITE (1, 159) 'FOR POINT LOAD ', J,
     +                     'ENTER LOAD AND DIST. FROM LEFT SUPPORT'
                  READ (1, *) PL(I,J), A(I,J)
 37            CONTINUE
            END IF
         ELSE IF (PT(I) .EQ. 3) THEN
            WRITE (1, 149) 'ENTER TOTAL NO OF SPANS AND SLAB DEPTH'
            READ (1, *) NSPAN(I), H(I)
            NS(I) = NSPAN(I) + 1
            WRITE (1, 119) 'ENTER END CANTILEVER MOMENTS AND LOADS'
            READ (1, *) CANTMT(I,1), CANTLD(I,1),
     +                  CANTMT(I,NS(I)), CANTLD(I,NS(I))
            DO 47 J = 1, NSPAN(I)
               WRITE (1, 169) 'FOR SPAN', J,
     +                 'ENTER SPAN LENGTH, UDL AND',
     +                 'NO. OF POINT LOADS'
               READ (1, *) LCON(I,J), UDLC(I,J), NPLC(I,J)
               IF (NPLC(I,J) .NE. 0) THEN
                  DO 57 K = 1, NPLC(I,J)
                     WRITE (1, 189) 'FOR POINT LOAD', J, ',', K,
     +                              'ENTER LOAD AND',
     +                              'DIST. FROM LEFT SUPT.'
                     READ (1, *) PLC(I,J,K), AC(I,J,K)
 57               CONTINUE
               END IF
 47         CONTINUE
         ELSE IF (PT(I) .EQ. 4) THEN
            WRITE (1, 199) 'ENTER THE SLAB LX, LY, UDL, DEPTH &',
     +                     'SPAN/DEPTH RATIO'
            READ (1, *) LX(I), LY(I), UDL(I), H(I), SD(I)
            IF (LX(I) .GT. LY(I)) THEN
               XL = LX(I)
               LX(I) = LY(I)
               LY(I) = XL
            END IF
            CALL TWTYPE
            WRITE (1, 209) 'ENTER SLAB CASE NUMBER'
            READ (1, *) CASE(I)
         END IF
 17   CONTINUE
C
C READ FROM EXTERNAL FILE IF APPLICABLE
C
      IF (IN .EQ. 3) THEN
         READ (3, *) (BN(I), I = 1, NP)
         READ (3, *) (PT(I), I = 1, NP)
         DO 67 I = 1, NP
            WRITE (1, 609) 'Reading for Slab SIN', I
            IF (PT(I) .EQ. 1) THEN
               READ (3, *) LCAN(I), H(I), UDL(I), NPL(I)
               IF (NPL(I) .NE. 0) THEN
                  READ (3, *) (PL(I,J), J = 1, NPL(I)),
     +                        (A(I,J), J = 1, NPL(I))
               END IF
            ELSE IF (PT(I) .EQ. 2) THEN
               READ (3, *) LSS(I), H(I), UDL(I), NPL(I)
               IF (NPL(I) .NE. 0) THEN
                  READ (3, *) (PL(I,J), J = 1, NPL(I)),
     +                        (A(I,J), J = 1, NPL(I))
               END IF
            ELSE IF (PT(I) .EQ. 3) THEN
               READ (3, *) NSPAN(I), H(I)
               NS(I) = NSPAN(I) + 1
               READ (3, *) CANTMT(I,1), CANTLD(I,1),
     +                     CANTMT(I,NS(I)), CANTLD(I,NS(I))
               DO 77 J = 1, NSPAN(I)
                  READ (3, *) LCON(I,J), UDLC(I,J), NPLC(I,J)
                  IF (NPLC(I,J) .NE. 0) THEN
                     READ (3, *) (PLC(I,J,K), K = 1, NPLC(I,J)),
     +                           (AC(I,J,K), K = 1, NPLC(I,J))
                  END IF
 77            CONTINUE
            ELSE IF (PT(I) .EQ. 4) THEN
               READ (3, *) LX(I), LY(I), H(I), UDL(I), CASE(I), SD(I)
               IF (LX(I) .GT. LY(I)) THEN
                  XL = LX(I)
                  LX(I) = LY(I)
                  LY(I) = XL
               END IF
            END IF
 67      CONTINUE
      END IF
C
C ANALYSIS AND DESIGN OF ALL PANELS
C
      DO 87 I = 1, NP
         WRITE (1, 339) 'PROGRAM NOW EXECUTING IN SLAB PANEL', BN(I)
         IF (PT(I) .EQ. 1) THEN
            LC = LCAN(I)
            HN = H(I)
            UC = UDL(I)
            PC = NPL(I)
            IF (PC .NE. 0) THEN
               DO 97 K = 1, PC
                  APC(K) = A(I,K)
                  PCC(K) = PL(I,K)
 97            CONTINUE
            END IF
            SR = 7.0
            CALL CANTI(I, FCU, FY, LC, HN, UC, PC, PCC, APC, SR, MC,
     +                 ACT, V, DN, AXP, FF, FX)
         ELSE IF (PT(I) .EQ. 2) THEN
            LC = LSS(I)
            HN = H(I)
            UC = UDL(I)
            PC = NPL(I)
            IF (PC .NE. 0) THEN
               DO 107 K = 1, PC
                  API(K) = A(I,K)
                  PCC(K) = PL(I,K)
 107           CONTINUE
            END IF
            SR = 20.0
            CALL SIMPLY(I, FCU, FY, LC, HN, UC, PC, PCC, API, SR, MSS,
     +                  V, VB, ASS, DN, AXP, FF, FX)
         ELSE IF (PT(I) .EQ. 3) THEN
            NSP = NSPAN(I)
            HN = H(I)
            DO 117 K = 1, NSP
               LCO(K) = LCON(I,K)
               UCO(K) = UDLC(I,K)
               PCO(K) = NPLC(I,K)
               IF (PCO(K) .NE. 0) THEN
                  DO 127 J = 1, PCO(K)
                     PCCO(K,J) = PLC(I,K,J)
                     ACC(K,J) = AC(I,K,J)
 127              CONTINUE
               END IF
 117        CONTINUE
            CTM(1) = CANTMT(I,1)
            CTL(1) = CANTLD(I,1)
            CTM(NS(I)) = CANTMT(I,NS(I))
            CTL(NS(I)) = CANTLD(I,NS(I))
            SR = 26.0
            CALL CONTI(I, NSP, LCO, HN, UCO, PCO, PCCO, ACC, FCU, FY,
     +                 CTM, CTL, SR, SPN, MSC, ASC, MTC, ATC, RCT, DN,
     +                 ASP, FF, FX)
         ELSE IF (PT(I) .EQ. 4) THEN
            LC1 = LX(I)
            LC2 = LY(I)
            HN = H(I)
            UC = UDL(I)
            CS = CASE(I)
            SR = SD(I)
            CALL TWOWAY(I, LC1, LC2, UC, CS, HN, FCU, FY, SR, MS, AS,
     +                  MT, AT, ML, AL, MG, AG, AR, WL, WS, DN, FS,
     +                  FT, FL, FG, ASP, FF, FX)
            YX = LC2 / LC1
         END IF
 87   CONTINUE
C
C OUTPUT SECTION - RESULTS DISPLAY
C
      DO 187 I = 1, NP
         IF (O .EQ. 2) THEN
            WRITE (1, 404)
            WRITE (1, 404)
            WRITE (1, 219) 'About to write - press <ENTER> to continue'
            PAUSE
         END IF
         IF (O .EQ. 4) WRITE (O, 308)
         IF (I .EQ. 1) THEN
            WRITE (O, 8) 'SLAB ANALYSIS AND DESIGN - BS8110'
            WRITE (O, 18) '==================='
            WRITE (O, 28) 'JOB REF:', JOB, 'DATE:', DATE
             WRITE (O, 28) 'DESIGNED:', ENGR, 'CHECKED:'
          END IF
         IF (I .NE. 1) THEN
            WRITE (O, 606) 'PAGE', I, 'OF', NP
         END IF
         IF (PT(I) .EQ. 1) THEN
            WRITE (O, 168) 'PANEL NO.', BN(I),
     +                     'TYPE: CANTILEVER SLAB'
            WRITE (O, 48) 'SKETCH:', 'DEPTH:', HN, 'mm'
            WRITE (O, 1148) 'Cantilever Span = ', LCAN(I), 'm'
            WRITE (O, 1248) 'Cantilever UDL = ', UDL(I), 'kN/m'
            WRITE (O, 1348) 'No. of Point Loads = ', NPL(I)
            IF (NPL(I) .NE. 0) THEN
               WRITE (O, 1448) 'Point Loads & Dist. = ',
     +                         (PL(I,J), ':', A(I,J), J = 1, NPL(I))
            END IF
            WRITE (O, 1548)
            WRITE (O, 68) 'FCU = ', FCU, 'N/SQ.mm', 'FY = ',
     +                    FY, 'N/SQ.mm'
            WRITE (O, 178) 'MOMENT = ', MC, 'kN.M'
            WRITE (O, 188) 'STEEL REQUIRED = ', ACT, 'SQ.mm'
            CALL RODDIA(ACT, FY, T, RD, SV)
            WRITE (O, 198) 'PROVIDE ', T, RD, ' @', SV, 'mm c/c TOP'
            WRITE (O, 208) 'SHEAR LOAD ON BEAM = ', V, 'kN/m'
            WRITE (O, 308)
         ELSE IF (PT(I) .EQ. 2) THEN
            WRITE (O, 218) 'PANEL NO.', BN(I),
     +                     'TYPE: SIMPLY SUPPORTED'
            WRITE (O, 48) 'SKETCH:', 'DEPTH:', HN, 'mm'
            WRITE (O, 1148) 'Span Length = ', LSS(I), 'm'
            WRITE (O, 1248) 'Span UDL = ', UDL(I), 'kN/m'
            WRITE (O, 1348) 'No. of Point Loads = ', NPL(I)
            IF (NPL(I) .NE. 0) THEN
               WRITE (O, 1448) 'Point Loads & Dist. = ',
     +                         (PL(I,J), ':', A(I,J), J = 1, NPL(I))
            END IF
            WRITE (O, 1548)
            WRITE (O, 68) 'FCU = ', FCU, 'N/SQ.mm', 'FY = ',
     +                    FY, 'N/SQ.mm'
            WRITE (O, 178) 'MOMENT = ', MSS, 'kN.M'
            WRITE (O, 188) 'STEEL REQUIRED = ', ASS, 'SQ.mm'
            CALL RODDIA(ASS, FY, T, RD, SV)
            WRITE (O, 198) 'PROVIDE ', T, RD, ' @', SV,
     +                     'mm c/c BTM'
            WRITE (O, 208) 'LEFT SHEAR ON BEAM = ', V, 'kN/m'
            WRITE (O, 308)
            WRITE (O, 208) 'RIGHT SHEAR ON BEAM = ', VB, 'kN/m'
            WRITE (O, 308)
         ELSE IF (PT(I) .EQ. 3) THEN
            WRITE (O, 228) 'PANEL NO.', BN(I),
     +                     'TYPE: CONTINUOUS SLAB'
            WRITE (O, 48) 'SKETCH:', 'DEPTH:', HN, 'mm'
            WRITE (O, 2148) 'LOADING ON THE SLAB:-'
            WRITE (O, 2248) 'Span', 'UDL', 'Number of',
     +                     'Point Loads and'
            WRITE (O, 2248) 'S/N', 'kN/m', 'Pt. Loads',
     +                     'Distance'
            DO 7070 J = 1, NSPAN(I)
               IF (NPLC(I,J) .NE. 0) THEN
                  WRITE (O, 2348) J, UDLC(I,J), NPLC(I,J),
     +                     (PLC(I,J,K), ':', AC(I,J,K),
     +                     K = 1, NPLC(I,J))
               ELSE
                  WRITE (O, 2448) J, UDLC(I,J), NPLC(I,J)
               END IF
 7070       CONTINUE
            WRITE (O, 68) 'FCU = ', FCU, 'N/SQ.mm', 'FY = ',
     +                    FY, 'N/SQ.mm'
            WRITE (O, 1548)
            WRITE (O, 238) 'SPAN DETAILS'
            WRITE (O, 238) '-----------'
            WRITE (O, 248) 'SPAN', 'LENGTH', 'MOMENT',
     +                     'STEEL', 'PROVIDE'
             WRITE (O, 248) 'S/N', 'm', 'kN.m',
      +                     'Sq.mm'
            DO 907 J = 1, NSPAN(I)
               AKS = ASC(J)
               CALL RODDIA(AKS, FY, T, RD, SV)
               WRITE (O, 258) J, LCON(I,J), MSC(J), ASC(J),
     +                        T, RD, '@', SV, 'mm clc B'
 907        CONTINUE
            WRITE (O, 268) 'SUPPORT DETAILS'
         ELSE IF (PT(I) .EQ. 4) THEN
            WRITE (O, 38) 'PANEL NO.', BN(I), 'TYPE: TWO WAY CASE',
     +                    CASE(I)
            WRITE (O, 48) 'SKETCH:', 'DEPTH:', HN, 'mm'
            WRITE (O, 58) 'LX =', LC1, 'm', 'LY =', LC2, 'm',
     +                    'Ly/Lx =', YX
            WRITE (O, 518) 'SHORT SPAN COEFF. -', FS, '&', FT,
     +                     'LONG SPAN',
     +                     'COEFF. -', FG, '&', FL
            WRITE (O, 68) 'FCU =', FCU, 'N/SQ.mm', 'FY =',
     +                    FY, 'N/SQ.mm'
            WRITE (O, 618) 'UNIFORMLY DISTRIBUTED LOAD = ',
     +                     UDL(I), 'kN/m'
            IF (O .EQ. 2) THEN
               WRITE (1, 404)
               WRITE (1, 404)
               WRITE (1, 219) 'About to write - press <ENTER>', 
     +                        'to continue'
               PAUSE
            END IF
            IF (O .EQ. 4) WRITE (O, 308)
            IF (I .EQ. 1) THEN
               WRITE (O, 8) 'SLAB ANALYSIS AND DESIGN - BS8110'
               WRITE (O, 18) '==================='
            END IF
            WRITE (O, 318) '====================='
            WRITE (O, 78) 'SHORT SPAN'
            WRITE (O, 78) '=========='
            WRITE (O, 88) 'SECTION', 'MOMENT (kN.m)',
     +                     'STEEL(SQ.mm)', 'PROVIDE'
            CALL RODDIA(AS, FY, T, RD, SV)
            WRITE (O, 98) 'SPAN', MS, AS, T, RD, '@', SV, 'mm clc B'
            CALL RODDIA(AT, FY, T, RD, SV)
            WRITE (O, 98) 'CONT. EDGE', MT, AT, T, RD, '@', SV,
     +                    'mm clc'
            WRITE (O, 108) 'EQUIVALENT UDL ON BEAM = ', WS, 'kN/m'
            WRITE (O, 78) 'LONG SPAN'
            WRITE (O, 78) '========='
            WRITE (O, 88) 'SECTION', 'MOMENT (kN.m)',
     +                     'STEEL(SQ.mm)', 'PROVIDE'
            CALL RODDIA(AL, FY, T, RD, SV)
            WRITE (O, 98) 'SPAN', ML, AL, T, RD, '@', SV, 'mm clc B'
            CALL RODDIA(AG, FY, T, RD, SV)
            WRITE (O, 98) 'CONT. EDGE', MG, AG, T, RD, '@', SV,
     +                    'mm clc'
            WRITE (O, 108) 'EQUIVALENT UDL ON BEAM = ', WL, 'kN/m'
            WRITE (O, 118) 'TORSIONAL BARS, IF ANY, IS ', AR, 'SQ.mm'
            CALL RODDIA(AR, FY, T, RD, SV)
            WRITE (O, 128) 'PROVIDE', T, RD, '@', SV, 'mm clc'
         END IF
C
C DEFLECTION OUTPUT
C
         WRITE (O, 138) 'DEFLECTION'
         WRITE (O, 138) '=========='
         IF (PT(I) .EQ. 1) THEN
            WRITE (O, 1138) 'Span/Depth =', SR, '%As =', AXP,
     +                     'Fs =', FF, 'Mod. Factor =', FX
            WRITE (O, 1238) 'Effective Depth of slab Reqd. =', DN, 'mm'
         ELSE IF (PT(I) .EQ. 2) THEN
            WRITE (O, 1138) 'Span/Depth =', SR, '%As =', AXP,
     +                     'Fs =', FF, 'Mod. Factor =', FX
            WRITE (O, 1238) 'Effective Depth of slab Reqd. =', DN, 'mm'
         ELSE IF (PT(I) .EQ. 3) THEN
            WRITE (O, 1138) 'Span/Depth =', SR, '%As =', ASP,
     +                     'Fs =', FF, 'Mod. Factor =', FX
            WRITE (O, 1238) 'Effective Depth of slab Reqd. =', DN, 'mm'
         ELSE IF (PT(I) .EQ. 4) THEN
            WRITE (O, 1138) 'Span/Depth =', SR, '%As =', ASP,
     +                     'Fs =', FF, 'Mod. Factor =', FX
            WRITE (O, 1238) 'Effective Depth of slab Reqd. =', DN, 'mm'
         END IF
         WRITE (O, 148) 'END OF DESIGN'
 187  CONTINUE
C
C FORMAT STATEMENTS
C
 9    FORMAT (5X, A34)
 18   FORMAT (5X, A19)
 19   FORMAT (5X, A41)
 29   FORMAT (5X, A13)
 39   FORMAT (5X, A38)
 49   FORMAT (5X, A43, 1X, A18)
 59   FORMAT (5X, A34)
 28   FORMAT (5X, A8, 2X, A20, 5X, A5, 2X, A20)
 38   FORMAT (5X, A8, 2X, A3, 5X, A16, 2X, I2)
 48   FORMAT (5X, A7, 5X, A6, F4.0, A2)
 58   FORMAT (5X, A3, F6.3, A2, 5X, A3, F6.3, A2, 5X, A6, F4.2)
 68   FORMAT (5X, A5, F5.1, A9, 5X, A4, F5.1, A9)
 78   FORMAT (5X, A20)
 79   FORMAT (5X, A49)
 88   FORMAT (5X, A7, 5X, A15, 5X, A13, 5X, A7)
 89   FORMAT (5X, A22)
 98   FORMAT (5X, A9, 5X, F6.3, 5X, F6.3, 5X, A1, F3.0, A3, F4.0, A6)
 99   FORMAT (5X, A12, I2)
 108  FORMAT (5X, A22, F6.3, A5)
 109  FORMAT (5X, A45, /, 5X, A18)
 118  FORMAT (5X, A26, F6.3, A7)
 119  FORMAT (5X, A35)
 128  FORMAT (5X, A7, A1, F3.0, A3, F4.0, A6)
 129  FORMAT (5X, A12, I2, 2X, A32)
 138  FORMAT (5X, A20)
 148  FORMAT (5X, A13)
 149  FORMAT (5X, A34)
 158  FORMAT (5X)
 159  FORMAT (5X, A14, I2, 2X, A32)
 168  FORMAT (5X, A8, 2X, A3, 5X, A23)
 169  FORMAT (5X, A8, I2, 2X, A25, /, 5X, A19)
 178  FORMAT (5X, A8, F8.3, A5)
 188  FORMAT (5X, A15, F8.3, A5)
 189  FORMAT (5X, A12, I2, A1, I2, 2X, A18, /, 5X, A16)
 198  FORMAT (5X, A8, A1, F3.0, A3, F4.0, A10)
 199  FORMAT (5X, A35, /, 5X, A16)
 208  FORMAT (5X, A23, F8.3, A4)
 209  FORMAT (5X, A25)
 218  FORMAT (5X, A8, 2X, A3, 5X, A22)
 219  FORMAT (5X, A40, /, 5X, A17)
 228  FORMAT (5X, A8, 2X, A3, 5X, A22)
 238  FORMAT (5X, A20)
 239  FORMAT (A1)
 248  FORMAT (5X, A4, 7X, A6, 7X, A6, 7X, A7, 7X, A7)
 258  FORMAT (/6X, I2, 7X, F6.3, 7X, F6.2, 7X, F5.3, 3X, A1, F3.0,
     +        A3, F4.0, A8)
 268  FORMAT (5X, A16)
 278  FORMAT (5X, A8, 5X, A9, 5X, A6, 7X, A7)
 288  FORMAT (5X, A3, 7X, A4, 7X, A5, 5X, A5)
 298  FORMAT (/8X, I2, 11X, F6.3, 8X, F6.3, 5X, F5.3, 7X, A1, F3.0,
     +        A3, F4.0, A8)
 308  FORMAT (5X)
 318  FORMAT (5X, A21)
 339  FORMAT (15(1X), 15X, A28, 2X, A3)
 403  FORMAT (3(/))
 404  FORMAT (7(/))
 518  FORMAT (5X, A20, F5.3, 1X, A1, 1X, F5.3, 5X, A10, A9, F5.3,
     +        1X, A1, 1X, F5.3)
 606  FORMAT (56X, A4, 1X, I2, 1X, A2, 1X, I2)
 609  FORMAT (15X, A20, I2)
 618  FORMAT (5X, A33, F6.3, A5)
 699  FORMAT (A20)
 929  FORMAT (5X, A12, 2X, A3)
 1138 FORMAT (5X, A13, F4.1, 6X, A5, 1X, F4.2, 6X, A3, F5.1, 6X,
     +        A14, F4.2)
 1148 FORMAT (/5X, A22, F6.3, A1)
 1238 FORMAT (/5X, A32, 1X, F5.1, A2)
 1248 FORMAT (/5X, A22, F6.3, A5)
 1348 FORMAT (/5X, A22, I2)
 1448 FORMAT (5X, A22, 6(F5.1, A1, F6.3, 3X))
 1548 FORMAT (1X)
 2148 FORMAT (3(/), 30X, A21)
 2248 FORMAT (5X, A5, 7X, A5, 7X, A10, 7X, A15)
 2348 FORMAT (/6X, I2, 9X, F6.3, 10X, I2, 10X, 6(F5.1, A1, F6.3, 3X))
 2448 FORMAT (/6X, I2, 9X, F6.3, 10X, I2)
C
      END
