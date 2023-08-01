Crossing Horizon DT
===================

Calculates the difference between the timestamp `header_date` of the T80S observation FITS file `filename` and the real crossing time of the RA and DEC at the ALT recorded at HEADER. For this, it uses `~astroplan.Observer` class. At the end, calculates rise and set crossing the required ALT three times 
using `delta_time`:

ALT_DT = TIMESTAMP[`header_date`] - delta_time<br>
ALT_DT = TIMESTAMP[`header_date`]<br>
ALT_DT = TIMESTAMP[`header_date`] + delta_time<br>


At the end, it chooses the lowest

abs(ALT_DT - TIMESTAMP[`header_date`]) time.

The text output of the program is a csv row:

	FILENAME,OBJNAME,FILTER,DATETIME,DIFFTIME

	DATETIME is the UTC timestamp found for the event (object at the Alt)
	DIFFTIME is DATETIME - header_date

In order to check the fit, run the script with --plot command active in order to create a nice plot showing the fit and the values for the altitude and azimuth.

Usage
-----

**Crossing Horizon DT** usage:

	usage: crossing_horizon_dt.py [-h] [--header_date HEADERCARD] [--plot]
								[--delta_time MINUTES] [--n_grid_points INT]
								FITSFILE

	Calculates the difference between the timestamp `header_date` of the T80S 
	observation FITS file `filename` and the real crossing time of the RA 
	and DEC at the ALT recorded at HEADER. For this, it uses `~astroplan.Observer` 
	class. At the end, calculates rise and set crossing the required ALT three times 
	using `delta_time`:

		ALT_DT = TIMESTAMP[`header_date`] - delta_time
		ALT_DT = TIMESTAMP[`header_date`]
		ALT_DT = TIMESTAMP[`header_date`] + delta_time

	At the end, it chooses the lowest
		
		abs(ALT_DT - TIMESTAMP[`header_date`]) time.
		
	The text output of the program is a csv row:

		FILENAME,OBJNAME,FILTER,DATETIME,DIFFTIME

		DATETIME is the UTC timestamp found for the event (object at the Alt)
		DIFFTIME is DATETIME - header_date

	In order to check the fit, run the script with --plot command active in order to create
	a nice plot showing the fit and the values for the altitude and azimuth.

	positional arguments:
	  FITSFILE              Observed Image FITS filename.

	options:
	  -h, --help            show this help message and exit
	  --header_date HEADERCARD, -D HEADERCARD
							FITS header card used to get datetime. Defaults to DATE-OBS.
	  --plot, -p            Plot the ALT/AZ datetime fit. Defaults to False.
	  --delta_time MINUTES, -T MINUTES
							Creates the timeline centred in header card used to retrieve the datetime. Defaults to 10 min.
	  --n_grid_points INT, -n INT
							Number of bins passed to astroplan module for the timeline creation. Defaults to 1800

Contact
-------
	
Contact us: [dhubax@gmail.com](mailto:dhubax@gmail.com).
