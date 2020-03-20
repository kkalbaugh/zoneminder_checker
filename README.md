# zoneminder_checker
Emails if a monitor doesn't have an event based on the monitor's group memembership.

1.  run ./install.sh
2.  Create modify or create additional subgroup(s) linked to the 'check' group.  By default all monitors are added to the 24 hour group which will email when a monitor hasn't generated an event for more than 24 hours.
    1.  Make the name the number of hours you would expect the monitor to have an event with. ie "48"
    2.  Add the monitors to the group that should have an event in this period of time.
