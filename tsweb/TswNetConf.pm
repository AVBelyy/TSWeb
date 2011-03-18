$TestsysIP = '127.0.0.1';
$NetDebug = 0 unless defined $NetDebug;
if ($ARGV[0] eq '-d') { shift @ARGV;  $NetDebug = 1; }
elsif ($ARGV[0] =~ /^-d(\d)$/) { shift @ARGV;  $NetDebug = $1; }
# One second testsys response timeout.
$Timeout = 10.0;
$SendTimeout = $Timeout;

1;
