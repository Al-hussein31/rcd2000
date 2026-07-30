C      ............................................................
C      039 - DISCTF - Function Subprogram Example
C      From: Oyenuga, "Computer Programming: Reinforced Concrete Design"
C      Cleaned from OCR-scraped source.
C      ............................................................
C
C      MAIN PROGRAM
C      Calculate discount through FUNCTION DISCTF
C
      PROGRAM DISCTF
      REAL SALES, AMOUNT, DISCTF

      WRITE(6,*) 'ENTER SALES AMOUNT'
      READ(5,*) SALES

      AMOUNT = SALES - DISCTF(SALES)

      WRITE(6,23) 'CUSTOMER TO PAY N', AMOUNT
   23 FORMAT(A, F10.2)

      STOP
      END

C
C      FUNCTION SUBPROGRAM: DISCTF
C      Returns discount on given sales amount.
C
      REAL FUNCTION DISCTF(SALES)
      REAL SALES

      IF (SALES .GT. 10000.0) THEN
         DISCTF = 0.15 * SALES
      ELSE IF (SALES .GT. 5000.0) THEN
         DISCTF = 0.10 * SALES
      ELSE
         DISCTF = 0.05 * SALES
      END IF

      RETURN
      END
