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

# define a Handler which writes INFO messages or higher to the sys.stderr
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logger.addHandler(console)
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
monitor_list = []
groupID = ''
def checkGroups():
    global cursor
    global groupID

    cursor.execute("""SELECT
        ID, Name, ParentId
    FROM
        Groups
    WHERE
        Name = 'check'""")
    if not cursor.rowcount:
        cursor.execute("""INSERT INTO Groups ('Name') VALUES ('check')""")
        mydb.commit()
        cursor.execute("""SELECT ID FROM Groups WHERE Name = 'check'""")
        for (ID) in cursor:
            cursor.execute("""INSERT INTO Groups ('Name','ParentId') VALUES ('24',%s)""",ID)
            mydb.commit()
        cursor.execute("""SELECT ID FROM Groups WHERE Name = '24'""")
        for (ID) in cursor:
            groupID = ID
        return 1
    else:
        return 0

def getMonitorList():
    global cursor
    global monitor_list

    cursor.execute("""SELECT m.ID FROM Monitors m WHERE m.ENABLED = 1 AND m.FUNCTION = 'Modect'""")
    result = cursor.fetchall()
    if not cursor.rowcount:
        logger.debug("No monitors")
        return 0
    else:
        for (x) in result:
                monitor_list.append(x[0])

def addGroupMonitor():
    global cursor
    global monitor_list
    global groupID
    for x in monitor_list:
        cursor.execute("""INSERT INTO Groups_Monitors ('GroupId','MonitorId') VALUES (%s,%s)""",(groupID,x))
        mydb.commit()
    logger.info("24 hour group added to Monitors : %s" % monitor_list)
if __name__ == "__main__":
    monitors = getMonitorList()
    if monitors == 1:
        groups = checkGroups()
        if groups == 1:
            logger.info("24 hour group added to Monitors: %s" % monitor_list)
