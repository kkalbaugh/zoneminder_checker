#!/bin/bash
{
	python3 -m pip install mysql-connector
	python3 -m pip install smtplib
	python3 -m pip install boto3
	if [ ! -d /usr/share/zm_checker ];
	then
		echo "Creating zh_checker directory";
		mkdir /usr/share/zm_checker
		echo "Copying files over";
		rsync -v *.py /usr/share/zm_checker/
	else
		echo "Copying files over";
		#cp -R *.py!(config.py) /usr/share/zm_checker/
		rsync -v --exclude='config.py' *.py /usr/share/zm_checker/
	fi		
	if [ ! -d /var/local/zm_checker/ ];
	then
		echo "Creating lastseen directory";
		mkdir /var/local/zm_checker/
		touch /var/local/zm_checker/lastsent
		chmod 755 /var/local/zm_checker/lastsent
	fi
		
	chown root:root -R /usr/share/zm_checker
	chmod 755 -R /usr/share/zm_checker

	echo '*/30 * * * * root /usr/bin/python3 /usr/share/zm_checker/zoneminder_checker.py &' > /etc/cron.d/zoneminder_checker
	echo "Added zoneminder_checker.py to /etc/cron.d/zoneminder_checker"
}
