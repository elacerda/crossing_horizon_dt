import io
import sys
import glob
import warnings
import numpy as np
import argparse as ap
import astropy.units as u
from astroplan import Observer
from astropy.io.fits import getheader
from contextlib import redirect_stdout
from datetime import datetime, timezone
from os.path import basename, join, isfile, isdir
from astroplan.exceptions import TargetNeverUpWarning
from astropy.coordinates import EarthLocation, Angle, SkyCoord

###
### CONSTANTS
###
__script_name__ = basename(sys.argv[0])
__script_desc__ = """
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
"""

# TIMEZONES
T80S_TZ_STR = 'America/Santiago'
UTC_TZ = timezone.utc

def parse_arguments():
    parser = ap.ArgumentParser(prog=__script_name__, description=__script_desc__, formatter_class=ap.RawTextHelpFormatter)
    parser.add_argument('--filename', '-f', metavar='FITSFILE', type=str, help='Observed Image FITS filename.')
    parser.add_argument('--input_dir', '-d', 
                        metavar='DIR', default=None, type=str, 
                        help='Check all FITS files from the same directory. If --filename is passed, --date will be ignored.')
    parser.add_argument('--header_date', '-D', metavar='HEADERCARD', default='DATE-OBS', type=str, 
                        help='FITS header card used to get datetime. Defaults to DATE-OBS.')
    parser.add_argument('--plot', '-p', action='store_true', default=False, 
                        help='Plot the ALT/AZ datetime fit. Defaults to False.')
    parser.add_argument('--delta_time', '-T', metavar='MINUTES', type=int, default=10,
                        help='Creates the timeline centred in header card used to retrieve the datetime. Defaults to 10 min.')
    parser.add_argument('--n_grid_points', '-n', metavar='INT', type=int, default=1800,
                        help='Number of bins passed to astroplan module for the timeline creation. Defaults to 1800')
    parser.add_argument('--output', '-o', metavar='FILENAME', default=None, help='Outputs to file (open mode will be set to append). Defaults to None.')
    args = parser.parse_args(args=sys.argv[1:])

    # Parse arguments
    if ((args.filename is None) & (args.input_dir is None)):
        parser.print_help()
        print(f'{__script_name__}: need --filename FILENAME or --input_dir DIR')
        sys.exit(2)

    if args.filename is not None:
        if not isfile(args.filename):
            raise FileNotFoundError(f'{__script_name__}: {args.filename}: file not exists')
        if 'bias' in args.filename:            
            raise NotImplementedError(f'{__script_name__}: {args.filename}: bias file')
        if 'skyflat' in args.filename:            
            raise NotImplementedError(f'{__script_name__}: {args.filename}: skyflat file')

    if args.input_dir is not None:
        if not isdir(args.input_dir):
            print(f'{__script_name__}: {args.input_dir}: directory does not exists')
            sys.exit(2)
        args.imgwildcard = join(args.input_dir, '*.fits.fz')
        args.imgglob = glob.glob(args.imgwildcard)
        nfiles = len(args.imgglob)
        if nfiles == 0:
            print(f'{__script_name__}: {args.imgwildcard}: files not found')
            sys.exit(2)
        args.imgglob = [x for x in args.imgglob if not (('bias' in x) | ('skyflat' in x))]

    if args.output is None:
        args.output = sys.stdout

    args.delta_time *= u.min
    return args

def get_alt_dt(filename, dt_card=None, delta_time=None, n_grid_points=None, plot=False):
    """
    Calculates the difference between the timestamp `dt_card` of the T80S 
    observation FITS file `filename` and the real crossing time of the RA 
    and DEC at the ALT recorded at HEADER. For this, it uses 
    `~astroplan.Observer` class.
    At the end, `get_alt_dt` calculates rise and set crossing the required
    ALT three times using `delta_time`:

    ALT_DT = TIMESTAMP[dt_card] - delta_time
    ALT_DT = TIMESTAMP[dt_card]
    ALT_DT = TIMESTAMP[dt_card] + delta_time

    At the end, it chooses the lowest
    
    abs(ALT_DT - TIMESTAMP[dt_card])

    Parameters
    ----------
    filename: str
        FITS Filename
    
    dt_card: str, optional
        FITS header card used to get datetime. Defaults to DATE-OBS.
    
    delta_time: `~astropy.units.Quantity`
        The function will search the altitude cross three times:

        t80s_Time - delta_time
        t80s_Time
        t80s_Time + delta_time

        This is neede because astroplan make the time grid for horizon 
        crossing in jd, this causes differences between the real initial
        time of the grid and the initial bin calculated.
        
        Defaults to 10 minutes.

    n_grid_points: int, optional
        Number of bins passed to `~astroplan.Observer.target_rise_time` and 
        `~astroplan.Observer.target_set_time` for the timeline creation.
    
    plot: bool, optional
        Plots the result. Defaults to False.

    Returns
    -------
    str
        FILENAME,OBJECT_NAME,FILTER,TARGET_DT_UTC,DIFF_TIME
    """
    import pytz

    delta_time = 10*u.min if delta_time is None else delta_time
    n_grid_points = 1800 if n_grid_points is None else n_grid_points

    # HEADER
    hdr = getheader(filename, 1)

    # LOCATION
    T80S_LAT = hdr.get('HIERARCH T80S TEL GEOLAT')  #'-30.1678638889 degrees'
    T80S_LON = hdr.get('HIERARCH T80S TEL GEOLON')  #'-70.8056888889 degrees'
    T80S_HEI = eval(hdr.get('HIERARCH T80S TEL GEOELEV'))  #2187
    t80s_lat = Angle(T80S_LAT, 'deg')
    t80s_lon = Angle(T80S_LON, 'deg')
    t80s_hei = T80S_HEI*u.m
    t80s_EL = EarthLocation(lat=t80s_lat, lon=t80s_lon, height=t80s_hei)
    t80s_tz = pytz.timezone(T80S_TZ_STR)

    t80s_obs = Observer(location=t80s_EL, timezone=t80s_tz)

    # DATETIME
    if dt_card is None:
        dt_card = 'DATE-OBS'
    dt_obs = pytz.utc.localize(datetime.fromisoformat(hdr.get(dt_card)))
    t80s_Time = t80s_obs.datetime_to_astropy_time(dt_obs)

    # TARGET
    target_coords = SkyCoord(ra=hdr.get('CRVAL1'), dec=hdr.get('CRVAL2'), unit=(u.deg, u.deg))
    try:
        _alt = hdr.get('ALT', None)
    except:
        _alt = hdr.get('HIERARCH T80S TEL EL START', None)
    if _alt is None:
        return f'{filename},{hdr.get("OBJECT")},{hdr.get("FILTER")},None,None'
    
    target_input_alt = Angle(_alt, 'deg')

    warnings.filterwarnings('error')
    _times = []
    _difftimes = []
    for _T in [t80s_Time-delta_time, t80s_Time, t80s_Time+delta_time]:
        try:
            rtime = t80s_obs.target_rise_time(
                _T,
                target_coords,
                horizon=target_input_alt,
                which='nearest',
                n_grid_points=n_grid_points,
            )
            _times.append(rtime)
            _difftimes.append((rtime - t80s_Time).sec)
        except TargetNeverUpWarning as e:
            print(e)
        try:            
            stime = t80s_obs.target_set_time(
                _T,
                target_coords,
                horizon=target_input_alt,
                which='nearest',
                n_grid_points=n_grid_points,
            )
            _times.append(stime)
            _difftimes.append((stime - t80s_Time).sec)
        except TargetNeverUpWarning as e:
            print(e)
    warnings.filterwarnings('default')

    target_dt_utc = None
    diff_time = None
    if len(_difftimes):
        i_min = np.argmin(np.abs(_difftimes)) 
        target_dt_utc = _times[i_min].datetime
        diff_time = _difftimes[i_min]

    final_message = f'{filename},{hdr.get("OBJECT")},{hdr.get("FILTER")},{target_dt_utc},{diff_time}'

    if plot:
        import matplotlib
        matplotlib.use('qtagg')
        from matplotlib import pyplot as plt

        deltat = 50
        nt = 2*deltat + 1
        while diff_time > (nt - 1):
            deltat *= 2
            nt = 2*deltat + 1
        timeline = t80s_Time + u.second*np.linspace(-deltat, deltat, nt)
        t_altaz = t80s_obs.altaz(timeline, target=target_coords)

        f, ax = plt.subplots()
        ax.plot(timeline.value, t_altaz.alt, c='k')
        ax.set_title(f'CROSS TIME: {target_dt_utc} (diff: {diff_time:.1f} s)', color='b')
        ax.axvline(x=target_dt_utc, c='b', ls='--', lw=2, label=None)
        ax.axvline(x=t80s_Time.datetime, c='g', ls=':', label=f'{dt_card}: {t80s_Time.datetime}')
        ax.axhline(y=target_input_alt.value, c='orange', ls='--', label=f'{target_input_alt:.4f}')
        ax.set_xlabel('TIME (UTC) [HH:MM:SS]')
        ax.set_ylabel('ALT (deg)')
        ax.legend(frameon=False, loc='best')
        plt.setp(ax.get_xticklabels(), rotation=30)
        f.set_layout_engine('tight')
        plt.pause(1)
        plt.show(block=True)
        plt.close(f)

    return final_message

if __name__ == '__main__':
    args = parse_arguments()

    if args.filename is not None:
        final_message = get_alt_dt(
            filename=args.filename, 
            dt_card=args.header_date, 
            delta_time=args.delta_time, 
            n_grid_points=args.n_grid_points,
            plot=args.plot,
        )
        print(final_message)
    else:
        close_f = True
        if isinstance(args.output, io.TextIOWrapper):
            f = args.output
            close_f = False
        else:
            f = open(args.output, 'a')
        with redirect_stdout(f):
            print('FILENAME,OBJNAME,FILTER,DATETIME,DIFFTIME')
            for filename in args.imgglob:
                final_message = get_alt_dt(
                    filename=filename, 
                    dt_card=args.header_date, 
                    delta_time=args.delta_time, 
                    n_grid_points=args.n_grid_points,
                    plot=args.plot,
                )
                print(final_message)
        if close_f:
            f.close()

