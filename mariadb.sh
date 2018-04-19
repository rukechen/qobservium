#!/bin/bash
start_mysql(){
    /usr/bin/mysqld_safe --datadir=/config/databases > /dev/null 2>&1 &
    RET=1
    while [[ RET -ne 0 ]]; do
        mysql -uroot -e "status" > /dev/null 2>&1
        RET=$?
        sleep 1
    done
}

# If databases do not exist, create them
sv stop /etc/service/qobserviumweb
if [ -f /config/databases/observium/users.ibd ]; then
  echo "Database exists."
else
  echo "Initializing Data Directory."
  /usr/bin/mysql_install_db --datadir=/config/databases >/dev/null 2>&1
  echo "Installation complete."
  start_mysql
  echo "Creating user and database."
  mysql -uroot -e "CREATE DATABASE IF NOT EXISTS observium DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;"
  PW=$(cat /config/config.php | grep -m 1 "'db_pass'" | sed -r 's/.*(.{34})/\1/;s/.{2}$//')
  mysql -uroot -e "CREATE USER 'observium'@'localhost' IDENTIFIED BY '$PW'"
  echo "Database created. Granting access to 'observium' user for localhost."
  mysql -uroot -e "GRANT ALL PRIVILEGES ON observium.* TO 'observium'@'localhost'"
  mysql -uroot -e "FLUSH PRIVILEGES"
  cd /opt/observium
  #php includes/update/update.php
  php ./discovery.php -u
  php adduser.php observium observium 10
  echo "Shutting down."
  mysqladmin -u root shutdown
  sleep 1
  echo "chown time"
  chown -R nobody:users /config/databases
  chmod -R 755 /config/databases
  sleep 3
  tmp="$(hostname -I | sed 's/ *$//g')"
  export tmp=$tmp
  #curl -H "Content-Type:application/json" -X PUT -d '{"ID": "tmpID", "Name": "tmpName", "Address": "'"$tmp"'","Port": 4504, "Check":{"DeregisterCriticalServiceAfter":"2m", "HTTP":"http://'"$tmp"':4504/api/about", "Interval":"10s"}}' http://10.0.3.1:8500/v1/agent/service/register
  echo "Initialization complete."
fi

echo "Starting qobserviumweb..."
while ! ps aux | grep 'runsv qobserviumweb';do
    sleep 2
done

sv start /etc/service/qobserviumweb
sv start /etc/service/schedulerjob
tmp="$(hostname -I | sed 's/ *$//g')"
defaultroute="$(ip route | grep 'default via' | awk '{print $3}')"
export tmp=$tmp
export DEFAULTROUTE=$defaultroute
echo "Register service to consul..."
curl -H "Content-Type:application/json" -X PUT -d '{"ID": "tmpID", "Name": "tmpName", "Address": "'"$tmp"'", "Port": 4504, "Check":{"DeregisterCriticalServiceAfter":"2m", "HTTP":"http://'"$tmp"':4504/api/about", "Interval":"10s"}}' http://"$DEFAULTROUTE":8500/v1/agent/service/register &

echo "Starting MariaDB..."
/usr/bin/mysqld_safe --skip-syslog --datadir='/config/databases'
