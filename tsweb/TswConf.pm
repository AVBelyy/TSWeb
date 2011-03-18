# TS-Web configuration file
$tswroot = 'c:/xampp/htdocs/tsweb';
$cgiroot = '/tsweb';
$cssurl = '/tsweb.css';
$favicon = '/favicon.ico';
$charset = 'cp1251';
$tswlogsdir = "$tswroot/logs";
$tswlog = "$tswlogsdir/tsw.log";
$maxpostsize = 1048576;
$allow_anonymous_login = 0;
$browse_itemsperpage = 30;
$default_title = 'TestSys on the Web';
$allow_any_ctype = 1;
$allow_printsol = 0;
$allow_contid = 1;
$contlist_mask = 1;
# wait three seconds if testsys reports an error
$ErrorDelay = 3;
if ($at_home) { require TswConfHome; } else { $read_conf = 1; }
