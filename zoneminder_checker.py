from datetime import timedelta, datetime, timezone
import time
import os.path
import logging
from logging.handlers import RotatingFileHandler
import mysql.connector
import MySQLdb.cursors
import config

# Check what email system to use
if config.email_type == "aws":
    import aws as email
if config.email_type == "smtp":
    import smtp as email

try:
    logLevel = config.logLevel
except:
    logLevel = 'DEBUG'

# Create Logging Object
logger = logging.getLogger('zmchecker')
log_level = logging.getLevelName(logLevel)
logger.setLevel(log_level)

# Setup Logging Handlers & Level
log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
ttd_handler = RotatingFileHandler(config.logFile, mode='a', maxBytes=5*1024*1024,backupCount=2, encoding=None, delay=0)
ttd_handler.setFormatter(log_formatter)

logger.addHandler(ttd_handler)

try:
    mydb = mysql.connector.connect(
      host= config.db_host,
      user= config.db_user,
      passwd= config.db_passwd,
      database= config.db_database
    )
except Exception as e:
    logger.error("Database Exception occurred", exc_info=True)

cursor = mydb.cursor()
monitor_list = ''

now = datetime.now().timestamp()
alarmResendWaitTime = int(now) - 60 * 60 * config.email_resend  # email_resend in hours

def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)

def sendagain():
    if not os.path.isfile(config.lastsentfile):
        print("Need to create file")
        logger.info("%s doesn't exist.  Need to create file" % config.lastsentfile)
        return 1
    else:
        fp = open(config.lastsentfile,"r")
        line = fp.readline()
        fp.close()
        if line !="":
            lastEmailSent = int(line)
        else:
            lastEmailSent = 0
        if lastEmailSent > alarmResendWaitTime:
            print("Already sent less than %s hours ago" % config.email_resend)
            logger.info("Already sent less than %s hours ago" % config.email_resend)
            lastsend_obj = datetime.fromtimestamp(int(line))
            lastsend_str = lastsend_obj.strftime("%Y-%m-%d %I:%M:%S %p")
            return lastEmailSent
        elif lastEmailSent == 0:
            print("Zoneminder Wasn't In Alarm")
            logger.debug("Zoneminder Wasn't In Alarm")
            return 1
        else:
            print("Ready to send again")
            logger.info("Ready to Send Again")
            return 1

def checkDatabase():
    global cursor
    global monitor_list

    cursor.execute("""SELECT
        m.ID, m.Name,g.NAME
    FROM
        Monitors m
        LEFT OUTER JOIN
            Groups_Monitors gm ON gm.MonitorId = m.ID
        LEFT OUTER JOIN
            Groups g ON g.ID = gm.GroupId
            LEFT OUTER JOIN
        Events e ON (e.MonitorID = m.ID AND e.StartTime  > NOW() - INTERVAL g.NAME HOUR)
    WHERE
        m.ENABLED = 1 AND m.FUNCTION = 'Modect'
            AND e.ID IS NULL AND g.ParentId IS NOT NULL""")

    result = cursor.fetchall()
    if not cursor.rowcount:
        print("No monitors in alarm")
        logger.debug("No monitors in alarm")
        return 0
    else:
        for x in result:
            monitor_list += "Monitor #%s (%s) - Last Event Was %s\n\n" % (x[0],x[1],getLastEvent(x[0]))
        print("Monitors listed in alarm:\n\n%s" % monitor_list)
        logger.info("Monitors listed in alarm: %s" % monitor_list)
        return 1

def getLastEvent(monitor):
    global cursor
    var = (str(monitor),)
    cursor.execute("""SELECT
                    StartTime
                FROM
                    Events
                WHERE
                    MonitorId = %s
                ORDER BY StartTime DESC
                LIMIT 1""",var)
    try:
        for (StartTime) in cursor:
            lastevent = datetime.strftime(StartTime[0], "%Y-%m-%d %I:%M:%S %p")
            logger.info("Last Event Found for %s was at %s" % (monitor, lastevent))
            print(lastevent)
            return lastevent
    except:
        print("No Prior Event Found")
        logger.info("No Prior Event Found for  %s" % monitor)
        return "No Prior Event Found"


if __name__ == "__main__":
    logger.info("Started Program")
    if not os.path.isfile(config.lastsentfile):
        logger.error("Last Sent Tracking File %s doesn't exist." % config.lastsentfile)
        try:
            ts = open(config.lastsentfile, 'w')
            ts.write("0")
            ts.close()
        except:
            logger.error("Error creating %s" % config.lastsentfile,exc_info=True)
            email.sendemail("Last Sent Tracking File Doesn't Exist and Couldn't Be Created" ,"ZMChecker Error")
    else:
        try:
            results = checkDatabase()
        except Exception as e:
            logger.error("Exception occurred", exc_info=True)
        except:
            logger.error("Couldn't Open Database")

        try:
            if results == 0:
                print("Status is OK")
                ready = sendagain();
                if ready > 2:
                    text = "Zoneminder Monitor(s) Are Working Again!"
                    subject = "Zoneminder - All Monitors Back Online"
                    print(text)
                    email.sendemail(text,subject)
                    ts = open(config.lastsentfile, 'w')
                    ts.write("0")
                    ts.close()
                else:
                    print("Not ready to send")

            else:
                print("Status is NOT Ok")
                logger.info("Status is NOT Ok")
                ready = sendagain();
                if ready == 1:
                    text = "The following Zoneminder monitor(s) are not working.\n\n"
                    text += monitor_list
                    subject = "Zoneminder - Monitor Problem!"
                    print(text)
                    email.sendemail(text,subject)
                    ts = open(config.lastsentfile, 'w')
                    ts.write(str(int(now)))
                    ts.close()
                else:
                    print("Not ready to send.  Sent Already")
                    logger.info("Not ready to send.  Sent Already")

        except Exception as e:
            logger.error("Exception occurred", exc_info=True)

    exit()
