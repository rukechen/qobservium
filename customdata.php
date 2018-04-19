<?php

/**
 * Observium
 *
 *   This file is part of Observium.
 *
 * @package    observium
 * @subpackage webinterface
 * @author     Adam Armstrong <adama@observium.org>
 * @copyright  (C) 2006-2013 Adam Armstrong, (C) 2013-2016 Observium Limited
 *
 */

include_once("includes/sql-config.inc.php");

$port   = get_port_by_id($argv[2]);

$device = device_by_id_cache($argv[1]);
$auth   = TRUE;

$time = time();
$HC   = ($port['port_64bit'] ? 'HC' : '');

$data = snmp_get_multi($device, "if${HC}InOctets.".$port['ifIndex']." if${HC}OutOctets.".$port['ifIndex'], "-OQUs", "IF-MIB", mib_dirs());
printf("%lf|%s|%s\n", $time, $data[$port['ifIndex']]["if${HC}InOctets"], $data[$port['ifIndex']]["if${HC}OutOctets"]);

// EOF
