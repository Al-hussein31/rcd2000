      PROGRAM SAMPLE
C     THIS PROGRAM ILLUSTRATES THE USE OF OPEN STATEMENTS TO
C     OPEN THE TERMINAL, PRINTER, AND FILE.
      CHARACTER*20 FNAMEI, FNAME2
      CHARACTER*1 INP, OTP
C
      OPEN (1, FILE='CON')
      OPEN (2, FILE='PRN')
C
      WRITE (1, 49) 'Please Enter letter -T- if the input is via
     + the Terminal'
      WRITE (1, 49) 'Please Enter letter -F- if the input is via
     + an External File'
      READ (1, 239) INP
C
      IF ((INP .EQ. 'F') .OR. (INP .EQ. 'f')) THEN
          WRITE (1, 59) 'Please Enter the Input File name'
          NI = 3
          READ (1, 249) FNAMEI
          OPEN (3, FILE=FNAMEI)
      ELSE
          NI = 1
          WRITE (1, 49) 'Please Enter letter -P- if the output is
     + via the Printer'
          WRITE (1, 49) 'Please Enter letter -F- if the output is
     + via an External File'
          READ (1, 239) OTP
          IF ((OTP .EQ. 'F') .OR. (OTP .EQ. 'f')) THEN
              NO = 4
              WRITE (1, 59) 'Please Enter the Output file name'
              READ (1, 249) FNAME2
              OPEN (4, FILE=FNAME2)
          ELSE
              NO = 2
          END IF
      END IF
C
49    FORMAT (15X, A)
59    FORMAT (15X, A)
239   FORMAT (A1)
249   FORMAT (A20)
C
      END
