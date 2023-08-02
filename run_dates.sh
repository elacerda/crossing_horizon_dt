d=$(TZ=UTC date "+%Y%m%d" -d "$1")
dtest=$(TZ=UTC date "+%s" -d "$d")
IMGPATH=/mnt/images
SCRIPT=crossing_horizon_dt.py

if [ -z $2 ]; then
    # NO FINAL DATE
    O_FILE=${d}.csv
    python3 $SCRIPT -d ${IMGPATH}/$d -o $O_FILE
else
    # FINAL DATE
    DT=$(TZ=UTC date "+%Y%m%d" -d "$2")
    DTtest=$(TZ=UTC date "+%s" -d "$DT")
    
    # LOOP INCREMENTING DAYS
    while [ $dtest -le $DTtest ]
    do
        O_FILE=${d}.csv
        python3 $SCRIPT -d ${IMGPATH}/$d -o $O_FILE
        d=$(TZ=UTC date "+%Y%m%d" -d "$d + 1 day")
        dtest=$(TZ=UTC date "+%s" -d "$d")
    done
fi