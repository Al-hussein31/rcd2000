      PROGRAM STAIR
C
C     STAIR - Reinforced Concrete Stair Design to BS 8110:1997
C     Straight flight stair (waist slab type, spanning longitudinally)
C     From: Oyenuga, "Simplified Reinforced Concrete Design"
C     Cleaned from OCR-scraped source.
C
      REAL MST(10), MHT(10), MQT(10),
     +MSB(10), MCS(10), MSP(10),
     +LST(10), LHT(10), LQT(10), LSB(10),
     +LCS(10), LSP(10), LLD(10),
     +M(10)
      DIMENSION TR(10), RS(10), UDL(10),
     +WAIST(10), SLF(10), ASST(10),
     +SPLD(10), WLD(10)
      CHARACTER COY*65, ANS*1,
     +TYPE(10)*25, INP*1, OTP*1,
     +ANSL(10)*1
      INTEGER CHECK, NTYPE(10), O, IN
      CHARACTER*30 FNAME1, FNAME2,
     +JOB, ENGR, DATE
C
      OPEN (1, FILE='CON')
  403 FORMAT (3/)
      WRITE (1,404)
  404 FORMAT (7/)
      WRITE (1,9) 'WELCOME TO STAIR'
    9 FORMAT (1X, A)
      WRITE (1,9) 'ANALYSIS AND DESIGN TO BS 8110'
      WRITE (1,19) 'PROGRAM DEVELOPED AND WRITTEN'
      WRITE (1,19) 'BY V O OYENUGA.'
   19 FORMAT (1X, A)
      WRITE (1,29) 'APRIL, 2000'
   29 FORMAT (1X, A)
      OPEN (2, FILE='LPT1')
      WRITE (1,403)
      WRITE (1,39) 'INPUT IS EXPECTED VIA SCREEN OR FILE'
   39 FORMAT (1X, A)
C
C     === INPUT SOURCE SELECTION ===
C
      WRITE (1,49) 'Please Enter letter -T - if the input is',
     +'via the Terminal'
   49 FORMAT (1X, A)
      WRITE (1,49) 'Please Enter letter -F - if the input is',
     +'via External File'
      READ (1,179) INP
  179 FORMAT (A1)
      IF ((INP .EQ. 'F') .OR. (INP .EQ. 'f')) THEN
        IN=3
        WRITE (1,59) 'Please Enter the Input Filename'
   59   FORMAT (1X, A)
        READ (1,69) FNAME1
   69   FORMAT (A30)
        OPEN (3, FILE=FNAME1)
      ELSE
        IN=1
      END IF
C
C     === OUTPUT DESTINATION SELECTION ===
C
      WRITE (1,404)
      WRITE (1,39) 'OUTPUT IS EXPECTED VIA PRINTER OR FILE'
      WRITE (1,49) 'Please Enter letter -P - if the output is',
     +'via the Printer'
      WRITE (1,49) 'Please Enter letter -F - if the output is',
     +'via External File'
      READ (1,179) OTP
      IF ((OTP .EQ. 'F') .OR. (OTP .EQ. 'f')) THEN
        O=4
        WRITE (1,59) 'Please Enter the Output File Name'
        READ (1,69) FNAME2
        OPEN (4, FILE=FNAME2)
      ELSE
        O=2
      END IF
C
C     === DATA INPUT ===
C
    5 CONTINUE
      IF (IN .EQ. 3) THEN
C
C       Read all input from data file (unit 3)
C
        READ (3,119) COY
  119   FORMAT (A65)
        READ (3,69) JOB
        READ (3,69) ENGR
        READ (3,69) DATE
        READ (3,*) FCU, FY
        READ (3,*) NSTAIR
        READ (3,*) (NTYPE(I), I=1,NSTAIR)
        DO 777 I=1,NSTAIR
          IF (NTYPE(I) .EQ. 1) THEN
            READ (3,*) LST(I), TR(I), RS(I), LLD(I)
            READ (3,179) ANSL(I)
            IF ((ANSL(I) .EQ. 'Y') .OR. (ANSL(I) .EQ. 'y')) THEN
              READ (3,*) SPLD(I), WLD(I)
            END IF
          END IF
  777   CONTINUE
      ELSE
C
C       Interactive keyboard input
C
        WRITE (1,109) 'Enter your Company Name'
  109   FORMAT (1X, A)
        READ (1,119) COY
        WRITE (1,129) 'Enter Job Reference'
  129   FORMAT (1X, A)
        READ (1,69) JOB
        WRITE (1,129) 'Enter Design Engineer'
        READ (1,69) ENGR
        WRITE (1,129) 'Enter Date of Design'
        READ (1,69) DATE
        WRITE (1,139) 'Enter Total No. of Stairs'
  139   FORMAT (1X, A)
        READ (1,*) NSTAIR
        WRITE (1,149) 'Enter Concrete and Steel Stresses'
  149   FORMAT (1X, A)
        WRITE (1,149) 'fcu, fy (N/mm2)'
        READ (1,*) FCU, FY
        WRITE (1,159) 'Are the above Info correct? - Y/N'
  159   FORMAT (1X, A)
        READ (1,179) ANS
        IF ((ANS .NE. 'Y') .AND. (ANS .NE. 'y')) THEN
          WRITE (1,169) 'Please re-enter the Input list'
  169     FORMAT (1X, A)
          GOTO 5
        END IF
C
        DO 7 I=1,NSTAIR
          WRITE (1,189) 'Please ensure correctness of entry',
     +    'before pressing the Enter Key'
  189     FORMAT (1X, A)
          WRITE (1,199) 'For Stair No.', I
  199     FORMAT (1X, A, I2)
          WRITE (1,209) 'Enter 1 for Straight Flight Stair'
  209     FORMAT (1X, A)
          READ (1,*) NTYPE(I)
    7   CONTINUE
      END IF
C
C     === ANALYSIS AND DESIGN ===
C
      WRITE (1,404)
      WRITE (1,219) 'PROGRAM READY TO ANALYSE AND DESIGN STAIRS'
  219 FORMAT (1X, A)
C
      DO 17 I=1,NSTAIR
        IF (NTYPE(I) .EQ. 1) THEN
          TYPE(I)='STRAIGHT FLIGHT STAIR'
          WRITE (1,229) 'No.', I, 'Stair is ', TYPE(I), 'Please Enter'
  229     FORMAT (1X, A, I2, A, A, A)
C
          IF (IN .EQ. 1) THEN
            WRITE (1,39) 'Enter Span (m), Tread (mm), Rise (mm)'
            WRITE (1,39) 'Imposed Load (kN/m2)'
            READ (1,*) LST(I), TR(I), RS(I), LLD(I)
            WRITE (1,39) 'Enter superimposed dead load (kN/m2)',
     +      'and WLD (kN/m3)'
            WRITE (1,39) 'If none, enter 0, 0'
            READ (1,*) SPLD(I), WLD(I)
          END IF
C
C         Design calculations for Straight Flight Stair
C         Waist slab type, spanning longitudinally (BS 8110)
C
          SLF(I)=25.0
          TM=TR(I)/1000.0
          RM=RS(I)/1000.0
C
C         Assume waist thickness = span / 20
          WAIST(I)=LST(I)/20.0
          IF (WAIST(I) .LT. 0.100) WAIST(I)=0.100
C
C         Self-weight of waist slab (sloping) on plan:
C         25 * h * sqrt(t^2 + r^2) / t
          SWS=SLF(I)*WAIST(I)*SQRT(TM**2+RM**2)/TM
C
C         Self-weight of steps = 0.5 * rise * 25
          STS=0.5*RM*SLF(I)
C
C         Finishes (1.0 kN/m2)
          FIN=1.0
C
C         Total dead load on plan (kN/m2)
          GKS=SWS+STS+FIN+SPLD(I)
C
C         Total ultimate load (kN/m run)
C         BS 8110: 1.4 Gk + 1.6 Qk
          UDL(I)=1.4*GKS+1.6*LLD(I)
C
C         Design moment - simply supported
C         Mmax = w * l^2 / 8
          MSB(I)=UDL(I)*LST(I)**2/8.0
C
C         Effective depth d (assume h=175, cover=20, bar=8)
          MCS(I)=175.0-20.0-8.0
C
C         K = M / (b * d^2 * fcu)
          K=MSB(I)*1.0E6/(1000.0*MCS(I)**2*FCU)
          MQT(I)=K
C
C         Lever arm factor z/d
          IF (K .LT. 0.156) THEN
            MSP(I)=0.5+SQRT(0.25-K/0.9)
          ELSE
            MSP(I)=0.5+SQRT(0.25-0.156/0.9)
          END IF
          IF (MSP(I) .GT. 0.95) MSP(I)=0.95
C
C         Lever arm z (mm)
          LHT(I)=MSP(I)*MCS(I)
C
C         Area of tension steel As = M / (0.87 * fy * z)
          ASST(I)=MSB(I)*1.0E6/(0.87*FY*LHT(I))
C
C         ---- Output Results ----
C
          WRITE (O,239) 'STAIR DESIGN - Straight Flight'
  239     FORMAT (1X, A)
          WRITE (O,239) 'Company: ', COY
          WRITE (O,239) 'Job: ', JOB
          WRITE (O,239) 'Engineer: ', ENGR
          WRITE (O,239) 'Date: ', DATE
          WRITE (O,239) '---'
          WRITE (O,249) 'Stair No.', I
  249     FORMAT (1X, A, I2)
          WRITE (O,239) 'Type: ', TYPE(I)
          WRITE (O,259) 'Span', LST(I), 'm'
          WRITE (O,259) 'Waist thickness', WAIST(I)*1000.0, 'mm'
          WRITE (O,259) 'Total ultimate load', UDL(I), 'kN/m'
          WRITE (O,259) 'Design moment', MSB(I), 'kNm/m'
          WRITE (O,259) 'Effective depth', MCS(I), 'mm'
          WRITE (O,259) 'K-value', MQT(I), ''
          WRITE (O,259) 'Lever arm factor z/d', MSP(I), ''
          WRITE (O,259) 'Lever arm z', LHT(I), 'mm'
          WRITE (O,259) 'Required As', ASST(I), 'mm2/m'
  259     FORMAT (1X, A, F10.3, 1X, A)
        END IF
   17 CONTINUE
C
      STOP
      END
C
C     ============================================================
C     Sample input data file format (unit 3):
C
C     'Company Name'
C     'Job Reference'
C     'Engineer Name'
C     'Design Date'
C     25.0, 460.0      ! fcu, fy (N/mm2)
C     2                ! Number of stairs
C     1, 1             ! NTYPE for each stair
C     3.5, 250.0, 175.0, 1.5   ! Stair 1: span, tread, rise, imposed
C     Y                ! ANSL - include SPLD/WLD?
C     0.5, 0.0         ! SPLD, WLD
C     2.8, 250.0, 175.0, 1.5   ! Stair 2: span, tread, rise, imposed
C     N                ! ANSL - no extra loads
C     ============================================================
