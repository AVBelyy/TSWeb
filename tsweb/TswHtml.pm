require TswConf;
require TswAuth;
require TswUtil;

$POSTMETHOD = $at_home ? 'GET' : 'POST';

sub start_html {
    return if $started_html;
    $started_html = 1;
  my $arg = join ("\n", @_);
  $arg .= "\n" if ($arg ne '');
  my $cook = http_cookies();
  print qq~Content-type: text/html; charset=$charset
Pragma: no-cache
Expires: now
$cook$arg
~ unless $no_http;
}

sub output_html_header {
    return if $header_output;
    $header_output = 1;
    my ($title, $class) = @_;
    start_html ();
  $title = $default_title unless ($title ne '');
  $keep_title = $title;
  my $link = $class ne 'none' ? 
    "<LINK HREF=$cssurl REL=stylesheet TYPE=text/css>\n" : '';
  my $icon = $favicon ne '' ?
      "<LINK HREF=$favicon REL='shortcut icon' TYPE=image/x-icon>\n" : '';
  $class = " CLASS=$class" unless ($class eq '' || $class eq 'none');
  print "<HTML><HEAD><TITLE>$title</TITLE>\n$link$icon";
  if ($no_http) {
    print qq|<META HTTP-EQUIV=Content-Type CONTENT='text/html; charset=$charset'>\n|;
    }
  print "</HEAD><BODY$class>\n";
#  <H2>Unfortunately, tsweb is temporarily down for maintenance (new academic year). We expect the system to be up at 19:00. Or, you can try to solve some tasks at TTS (it's already up).</H2>
}

sub output_html_title {
    return if $title_output;
    $title_output = 1;
    my $title = $_[0] ? $_[0] : $keep_title;
    output_html_header (@_);
    print "<H1>$title</H1>\n";
}

sub output_html_end {
    return if $html_end or !$started_html;
    $html_end = 1;
    print "</BODY></HTML>\n";
}

sub error {
  my $msg = shift;
  $msg = 'POST format parse error' unless $msg;
  $msg = &b_encode ($msg);
  output_html_header ('Error', 'err');
  print <<ERR;
<H2>Error</H2>
<SPAN CLASS=errm>$msg</SPAN><BR /><BR />
<A HREF=$loccgiroot/index.html>Main page</A>
ERR
  output_html_end();
  exit;
}

sub login_error {
    my $msg = shift;
    $msg = 'Login error: session data missing or expired';
    $msg = &b_encode ($msg);
    output_html_header ('Authentification Error', 'err');
    print <<ERR;
<H2>Error</H2>
<SPAN CLASS=errm>$msg</SPAN><BR /><BR />
Click <A HREF=$loccgiroot/index>here</A> to log in.
ERR
    output_html_end();
    exit;
}

sub testsys_error {
    my $msg = &b_encode (shift);
    my $f = $msg eq 'incorrect team id or password' ||
	    $msg eq 'invalid team id or password';
    $msg = $msg ne '' ? 
	"TestSys reports following error: <I>$msg</I>" :
	"TestSys reports unknown error (connection lost?)";
    output_html_header ('TestSys Error', 'err');
    print <<ERR;
<H2>Error</H2>
<SPAN CLASS=errm>$msg</SPAN><BR /><BR />
<A HREF=$loccgiroot/index>Main page</A>
ERR
    print "&nbsp;&nbsp;<A HREF=index?op=logout>Log out</A>\n" if $f;
    output_html_end();
    exit;
}
    

sub output_empty_redir {
  my $url = shift;
  $url = 'index' unless $url;
  start_html ("Refresh: 0;URL=$cgiroot/$url");
  output_html_header();
  output_html_end();
  exit;
}

1;
