require TswConf;

# get path info
$pathinfo = $ENV{'PATH_INFO'};
if ($bigsubm == 2) {
  $bigsubm = !($pathinfo !~ m[/(submit)([/\?\#].*)?$]);
}
$reqmethod = $ENV{'REQUEST_METHOD'};
$cookies = $ENV{'HTTP_COOKIE'};
$loccgiroot = $cgiroot;
$parseerr = '';
$maxpostsize = 16384 unless $maxpostsize;
$query = $ENV{'QUERY_STRING'};
# get query
if ($reqmethod eq 'POST') { 
  $clength = $ENV{'CONTENT_LENGTH'};
  read(STDIN, $bigsubm ? $sdata : $query1, $clength);
}
$query .= "&$query1" unless $bigsubm;
# parse command-line parameters
while (my $i = shift (@ARGV)) {
  $query = shift (@ARGV) if ($i eq '-q');
  $pathinfo = shift (@ARGV) if ($i eq '-p');
  $cookies = shift (@ARGV) if ($i eq '-c');
  $at_home = 1 if ($i eq '-h');
  $no_http = 1 if ($i eq '-n');
  $trivauth = 1 if ($i eq '-t');
  $NetDebug = 1 if ($i eq '-d');
  if ($i eq '-l') {
    binmode(STDIN);
    $clength1 = read (STDIN, $sdata, $clength = shift (@ARGV));
    die "cannot read $clength bytes" unless ($clength1 == $clength);
    $reqmethod = 'POST'; }
}

$reqmethod = 'GET' if $at_home && !$reqmethod;
if ($read_conf == 1 && $at_home) { require TswConfHome; }

$remote_ip = $ENV{'REMOTE_ADDR'} unless $at_home;
$full_ip = $ip = $remote_ip;

$have_big_arg = length ($sdata);

# split into pairs (name,value)
@pairs = split(/&/, $query);
foreach $pair (@pairs) {
   my ($name, $value) = split(/=/, $pair);
   $FORM{'botva'} = $value;
   $value =~ tr/+/ /;
   $value =~ s/<([^>]|\n)*>//g;
   $value =~ s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
   $value =~ s/<!--(.|\n)*-->//g;
   $FORM{$name} = $value if $name ne '';
}
# now $FORM{'var-name'} is equal to the corresponding value

%COOKIE = ();
for (split (/;\s+/, $cookies)) {
  if (/^([A-Za-z0-9\_\-\.]+)\=(.*)$/) {
    my ($n, $v) = ($1, $2);
    $v = $1 if $v =~ /^\s*"(.*)"\s*$/;
    $COOKIE{$n} = $v;
    $CookieArg{$n} = [ split (/\|/, $v) ];
  }
}

sub p_error { $error = $_[0] unless defined $error;  $ex = 1; }

sub parse_arg {
  my $bnd = shift @slines;
  p_error ("Incorrect boundary $bnd") unless ($bnd eq $boundary);
  my $line = shift @slines;
  p_error ("Content-Disposition expected in $line") 
    unless ($line =~ /^content-disposition: form-data; name="(\w+)"\s*(.*)$/i);
  $paradd = $2;
  return $parname = $1;
}

sub get_arg_body {
  my $i = 0;
  while ($slines[$i] ne $boundary && $slines[$i] ne $e_boundary) {
    if (++$i >= @slines) {
      p_error ("Unexpected end of input stream while reading $parname");
      return; } }
  my $data = join ("\r\n", @slines[0 .. $i-1]);
  @slines = @slines[$i .. $#slines];
  return $data;
}

sub parse_big_arg {
  @slines = split (/\n/, $sdata);
  %FORM = ();
  $boundary = $slines[0];
  $e_boundary = "$boundary--";
  p_error ("Incorrect boundary: $boundary")
    unless $boundary =~ /^\-\-[A-Za-z0-9\(\)\-\.\'\+\_\,\/\:\=\?]{1,70}$/ && $boundary !~ /\s$/;
  return if $ex;
  while (@slines > 2) {
    parse_arg();
    if ($paradd =~ /^; filename="([\x20\x21\x23-\xff]*)"$/) {
      $FORM{$parname} = $filepath = $1;
      p_error ('Filename too long') unless (length $filepath <= 127);
      return if $ex;
      $line = shift @slines;
      if ($line =~ /^content-type: (.*)$/i) {
        $CONTTYPE{$parname} = $conttype = $1;
#      p_error ("Unsupported content type `$1'")
#	  unless ($conttype eq 'application/octet-stream' || 
#		  $conttype =~ /^text\/plain(; charset=(.*))?$/ ||
#		  $conttype eq 'text/x-csrc');
        $chset = $2;
        p_error ('Empty line expected') unless (shift @slines eq '');
        return if $ex;
      } else {
        p_error ('Empty line expected') unless ($line eq '');
        return if $ex;
      };
      my $t = get_arg_body();
      if ($filepath eq '') { p_error ('Empty filename') if ($t ne ''); }
      else { $FILE{$fparname = $parname} = $filedata = $t; }
      p_error ('File too long') if (length ($t) > $maxpostsize);
      return if $ex;
    } else {
      p_error ('Empty line expected instead of '.$x) unless (($x = shift @slines) eq '');
      return if $ex; 
      $FORM{$parname} = get_arg_body();
      return if $ex;
    }
  }
  p_error ('Last line must be boundary') unless (shift @slines eq $e_boundary);
}

parse_big_arg() if ($have_big_arg);

1;
