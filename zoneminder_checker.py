import smtplib
from datetime import timedelta, datetime, timezone
import time
import os.path
import aws
import logging
from logging.handlers import RotatingFileHandler
import mysql.connector


log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')

logFile = 'zm_checker.log'

ttd_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5*1024*1024, 
                                 backupCount=2, encoding=None, delay=0)
ttd_handler.setFormatter(log_formatter)
ttd_handler.setLevel(logging.INFO)

app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)

app_log.addHandler(ttd_handler)

mydb = mysql.connector.connect(
  host="localhost",
  user="zmuser",
  passwd="zmpass",
  database="zm"
)

lastsentfile = 'lastsent.txt'

subject = ''
text = ''
cursor = ''
monitors = ''
results = ''
rowcount = ''

now = datetime.now().timestamp()
alarmResendWaitTime = int(now) - 60 * 60 * 8

def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

def sendagain():
    if not os.path.isfile(lastsentfile):
        print("Need to create file")
        app_log.info("%s doesn't exist.  Need to create file" % lastsentfile)
        return 1
    else:
        try:
            with open(lastsentfile) as fp:  
                line = fp.readline()
                lastEmailSent = int(line)
                fp.close()
                if lastEmailSent > alarmResendWaitTime:
                    print("Already sent less than 8 hours ago")
                    lastsend_obj = datetime.fromtimestamp(int(line))
                    lastsend_str = lastsend_obj.strftime("%Y-%m-%d %I:%M:%S %p")
                    return lastEmailSent
                elif lastEmailSent == 0:
                    print("TTD Wasn't In Alarm")
                    return 1
                else:
                    print("Ready to send again")
                    return 1
        except:
            app_log.error("Unable to open %s" % lastsentfile)

def checkDatabase():
    global cursor
    global monitors
    global rowcount
    
    cursor = mydb.cursor()
    cursor.execute("""SELECT 
        m.ID
    FROM
        Monitors m
            LEFT OUTER JOIN
        Events e ON e.MonitorID = m.ID AND e.StartTime  > NOW() - INTERVAL 1 DAY
    WHERE
        m.ENABLED = 1 AND m.FUNCTION = 'Modect'
            AND e.ID IS NULL""")

    result = cursor.fetchall()
    if not cursor.rowcount:
        print("No results found")
        return 0
    else:
        print("Results found")
        rowcount = cursor.rowcount;
        monitors = ' '.join(str(e) for e in result)
        return 1
    
    
if __name__ == "__main__":
    app_log.info("Started Program")
    subject = "BDFD TwoToneDetect "
    try:
        results = checkDatabase()
    except:
        app_log.error("Couldn't Open Database")
    print("Monitors listed in alarm: %s" % monitors)
    print(monitors)

    print("Rowcount: %s" % rowcount)
    if results == 0:        
        print("Status is OK")
        ready = sendagain();
        if ready > 2:
            text = "Zoneminder Monitor(s) Are Working Again!"
            subject = "All Monitors Back Online"
            print(text)
            aws.sendawsemail(text,subject)
            ts = open(lastsentfile, 'w')
            ts.write("0")
            ts.close()       
        else:
            print("Not ready to send")

    else:
        print("Status is NOT Ok")
        ready = sendagain();

        if ready == 1:
            text = "The following Zoneminder monitor(s) are not working." 
            text += "Monitor: %s" % monitors
            subject = "Zoneminder Monitor Problem!"
            print(text)
            aws.sendawsemail(text,subject)
            ts = open(lastsentfile, 'w')
            ts.write(str(int(now)))
            ts.close()       
        else:
            print("Not ready to send.  Sent Already")
    exit()
