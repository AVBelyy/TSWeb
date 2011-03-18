#!/usr/bin/perl

sub dos2koi {
    local $_ = shift;
    tr/\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1/áâ÷çäåöúéêëìíîïğòóôõæèãşûıÿùøüàñÁÂ×ÇÄÅÖÚÉÊËÌÍÎÏĞÒÓÔÕÆÈÃŞÛİßÙØÜÀÑ³£/;
    return $_;
}

sub koi2dos {
    local $_ = shift;
    tr/áâ÷çäåöúéêëìíîïğòóôõæèãşûıÿùøüàñÁÂ×ÇÄÅÖÚÉÊËÌÍÎÏĞÒÓÔÕÆÈÃŞÛİßÙØÜÀÑ³£/\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1/;
    return $_;
}

sub win2koi {
    local $_ = shift;
    tr{àáâãäåæçèéêëìíîïğñòóôõö÷øùúûüışÿÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏĞÑÒÓÔÕÖ×ØÙÚÛÜİŞß\xb8\xa8}
      {ÁÂ×ÇÄÅÖÚÉÊËÌÍÎÏĞÒÓÔÕÆÈÃŞÛİßÙØÜÀÑáâ÷çäåöúéêëìíîïğòóôõæèãşûıÿùøüàñ£³};
    return $_;
}


sub koi2win {
    local $_ = shift;
    tr{ÁÂ×ÇÄÅÖÚÉÊËÌÍÎÏĞÒÓÔÕÆÈÃŞÛİßÙØÜÀÑáâ÷çäåöúéêëìíîïğòóôõæèãşûıÿùøüàñ£³}
      {àáâãäåæçèéêëìíîïğñòóôõö÷øùúûüışÿÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏĞÑÒÓÔÕÖ×ØÙÚÛÜİŞß\xb8\xa8};
    return $_;
}

# ================== SUB win2dos ==================== #
sub win2dos 
{
    my $str = shift;
    $str =~ tr[\xC0-\xFF\xA8\xB8][\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8A\x8B\x8C\x8D\x8E\x8F\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9A\x9B\x9C\x9D\x9E\x9F\xA0\xA1\xA2\xA3\xA4\xA5\xA6\xA7\xA8\xA9\xAA\xAB\xAC\xAD\xAE\xAF\xE0\xE1\xE2\xE3\xE4\xE5\xE6\xE7\xE8\xE9\xEA\xEB\xEC\xED\xEE\xEF\xF0\xF1];
    return $str;
}
# ================== SUB dos2win ==================== #
sub dos2win
{
	my $str = shift;
    $str =~ tr[\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8A\x8B\x8C\x8D\x8E\x8F\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9A\x9B\x9C\x9D\x9E\x9F\xA0\xA1\xA2\xA3\xA4\xA5\xA6\xA7\xA8\xA9\xAA\xAB\xAC\xAD\xAE\xAF\xE0\xE1\xE2\xE3\xE4\xE5\xE6\xE7\xE8\xE9\xEA\xEB\xEC\xED\xEE\xEF\xF0\xF1][\xC0-\xFF\xA8\xB8];
    return $str;
}


# encode a form value to be written into file, and viceversa
sub a_encode {
  my $s = $_[0];
  $s =~ s/\\/\\\\/g;
  $s =~ s/<[bB][rR]>/\\b/g;
  $s =~ s/\r//g;
  $s =~ s/\n/\\n/g;
  $s =~ s/\r/\\r/g;
  $s =~ s/\t/\\t/g;
  $s =~ s/\|/\\\!/g;
  $s =~ s/\</\\\</g;
  $s =~ s/\>/\\\>/g;
  return $s;
}

sub a_decode {
  my $s = $_[0];
  $s =~ s/\\n/\n/g;
  $s =~ s/\\r/\r/g;
  $s =~ s/\\t/\t/g;
  $s =~ s/\\\!/\|/g;
  $s =~ s/\\\\/\\/g;
  $s =~ s/\\\>/\>/g;
  return $s;
}

# encode a string to be output into html
sub b_encode {
  my $s = $_[0];
  $s =~ s/\"/&quot;/g;
  $s =~ s/</&lt;/g;
  $s =~ s/>/&gt;/g;
  $s =~ s/\n/<br>\n/g unless ($_[1]);
#  $s =~ s/\\b/<br>\n/g;
  return $s;
}

# a variant of b_encode() for form parameter values
sub parm_encode {
  my $s = &b_encode;
  return $s ? " value=\"$s\"" : '';
}

sub chkbox_encode { $_[0] ? ' CHECKED' : ''; }

# encodes a string as a value of query, as in ...?str=...
sub query_encode {
  $_ = shift;
  s{([^\x20A-Za-z0-9\.\,\_\-\:/\\\+\<\>])}{sprintf('%%%02x',ord($1))}eg;
  s{\x20}{+}g;
  $_;
}

sub query_encode_robust {
  $_ = shift;
  s{([^\x20A-Za-z0-9\.\_\-])}{sprintf('%%%02x',ord($1))}eg;
  s{\x20}{+}g;
  $_;
}

# get host name
sub get_host {
  my ($ip_address,$ip_number,@numbers);
  if ($ENV{'REMOTE_HOST'}) {
    $host = $ENV{'REMOTE_HOST'};
  } else { 
    $ip_address = $ENV{'REMOTE_ADDR'};
    @numbers = split(/\./, $ip_address);
    $ip_number = pack("C4", @numbers);
    $host = (gethostbyaddr($ip_number, 2))[0];
  }
  if ($host eq "") {$host = "IP: $ENV{'REMOTE_ADDR'}";
  } else { $host = "Host: $host"; }
}

# check whether the string is a valid e-mail
sub is_email {
  return $_[0] =~ /[._a-z0-9-]+\@[._a-z0-9-]+\.[a-z]{2,3}$/i;
}

# convert unix time into string
sub conv_time0 {
my ($min,$hour,$mday,$mon,$year,$wday,@months,@days);
@months = ('January','February','March','April','May','June','July','August','September','October','November','December');
@days = ('Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday');
($min,$hour,$mday,$mon,$year,$wday) = (localtime($_[0]))[1,2,3,4,5,6];
$min = "0$min" if ($min < 10);
$hour = "0$hour" if ($hour < 10);
$mday = "0$mday" if ($mday < 10);
$year += 1900;
return $this_day = ("$days[$wday], $months[$mon] $mday, $year at $hour:$min");
}

# convert unix time into string
sub conv_time {
  return '' unless ($_[0] > 0);
  my ($sec, $min, $hour, $mday, $mon, $year, @rem) = (localtime ($_[0]));
  return sprintf ("%02d.%02d.%02d %02d:%02d:%02d", $mday, $mon+1, $year+1900,
    $hour, $min, $sec);
}

sub conv_time2 {
  my $z = shift;
  return '' unless ($z > 1e6);
  my ($sec, $min, $hour, $mday, $mon, $year, @rem) = (localtime ($z));
  $Time = time unless $Time;
  return $z < $Time - 80000 ? 
    sprintf ("%02d.%02d.%02d", $mday, $mon+1, $year+1900) :
    sprintf ("%02d:%02d:%02d", $hour, $min, $sec);
}

sub eng_num {
  return $_[0] == 1 ? '' : 's';
}

sub conv_timeper {
  my $t = int (shift);
  $t = 0 if $t <= 0;
  my ($h, $m, $r);
  $m = int($t/60);  $s = $t % 60;
  $h = int($m/60);  $m %= 60;
  if ($t < 60) { return "$t second".&eng_num($t); }
  if ($t < 300) {
    $r = "$m minute".&eng_num($m);
    $r .= " $s second".&eng_num($s) if $s;
  } elsif ($t < 3600) {
    return "$m minute".&eng_num($m);
  } else {
    $r = "$h hour".&eng_num($h);
    $r .= " $m minute".&eng_num($m) if $m;
  }
  return $r;
}


1;
