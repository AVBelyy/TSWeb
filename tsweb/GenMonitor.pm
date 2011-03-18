# generic monitor generator

$MonError = $MonLine = undef;

my $lno;  my @lines;  my $cmd;  my @args;


sub enc {$_ = shift;  s/&quot;/\"/g;  s/&/&amp;/g;  s/</&lt;/g;  s/>/&gt;/g;  s/\"/&quot;/g;  $_;}

sub m_error {
    return if $MonError;
    my $err = &enc;
    $_ = $err;  s/&/&amp;/g;  s/</&lt;/g;  s/>/&gt;/g;  
    $MonError = $_;
    $MonLine = $lno;
    return undef;
}

sub parse_line {
    my $cl;
    if ($Feedback) { $Feedback = 0;  return 2; }
    do {
	$cmd = '';  @args = ();
	return 0 unless ($cl = shift @lines);
	$lno++;
	$cl =~ /^\@([a-z]+)\s(.*)$/ || m_error ('@<command> expected');
	$cmd = $1;   $ast = "$2,";
    } while ($cmd eq 'comment');
    $ast =~ s/\\\"/&quot;/g;
    while ($ast ne '') {
	if ($ast =~ /^\"([^\"]*)\",(.*)$/) { $ast = $2;  push @args, $1; }
	elsif ($ast =~ /^([^,]*),(.*)$/) { $ast = $2;  push @args, $1; }
	else { m_error ('invalid parameters'); } }
# print $cmd, ':', join (';', @args), "\n";
    return 1;
}

sub put_back { $Feedback = 1; }

sub expect_comm {
    my ($arg, $pc) = @_;
    &parse_line;
    m_error ("\@$arg expected but \@$cmd found") unless ($cmd eq $arg);
    m_error ("invalid parameter count of \@$cmd") unless ($pc == @args);
    return @args;
}

sub testnum {
    my @a = @_;
    while ($_ = shift @a) {
	m_error ("Number expected instead of `$_'") unless /^\d+$/; }
    return @_;
}

sub expect_comm_num {
    return (testnum (expect_comm (shift, 1)))[0];
}

sub conv_submit_line {
    my $p = shift;
    my ($tim, $att, $rc, $tn, $tm, $pr) = @$p;
    return sprintf ('%d:%02d:%02d, team <B>%s</B> - <B>%s</B>, problem <B>%s</B>', 
		    int ($tim/3600), int($tim/60) % 60, $tim % 60, 
		    $Teams[$tm][0], $Teams[$tm][3], $Problems[$pr][0]);
}

sub GenMonitor {
    my ($data, $showtimes, $cutoff, $submco, $hideproblems) = @_;
    $MonError = $MonLine = undef;
    @lines = split (/\r?\n/, $data);
    $submco = 99999 if $submco <= 0;
    my $i = 0; 
    for ($i = 0; $i < @lines; $i++) {
	last if ($lines[$i] =~ /^\@contest/);
	last if ($lines[$i] eq "\032") }
    if ($i >= @lines) {
	$data = join ("\n", @lines);
	return "<PRE>$data\n</PRE>\n";
    }
    $lno = $lines[$i] eq "\032" ? $i+1 : $i;
    @lines = @lines[$lno .. $#lines];
    ($contname) = expect_comm ('contest', 1);
    ($startat) = expect_comm ('startat', 1);
    m_error ('Invalid date format') 
	unless ($startat =~ /^(\d\d\.\d\d\.\d\d\d\d\s\d\d:\d\d:\d\d|undefined)$/);
    $contlen = expect_comm_num ('contlen');
    $now = expect_comm_num ('now');
    $now = $cutoff if $cutoff > 0 and $cutoff < $now;
    ($state) = expect_comm ('state', 1);
    m_error ("Unknown state code `$state'") if 
	$state ne 'BEFORE' && $state ne 'RUNNING' && 
	$state ne 'FROZEN' && $state ne 'OVER' && $state ne 'RESULTS';
    $freeze = expect_comm_num ('freeze');
    $problems = expect_comm_num ('problems');
    $teams = expect_comm_num ('teams');
    $submissions = expect_comm_num ('submissions');
    parse_line ();
    if ($cmd eq 'for' && scalar @args == 1) {
	$MonForTeam = $args[0];
    } else { put_back(); }
    $state = 'FROZEN' if ($state eq 'RUNNING' && $now >= $freeze * 60 && $freeze > 0);
    $state = 'OVER (FROZEN)' if ($state eq 'OVER' && $freeze > 0);
    $effnow = ($state =~ /FROZEN/) ? $freeze * 60 : $now; 
    m_error ("Too few problems: $problems") unless ($problems >= 0 && $problems <= 512);
    m_error ("Too few teams: $teams") unless ($teams >= 0 && $teams <= 512);
    m_error ("Too many submissions: $submissions") unless ($submissions <= 65536);
    return undef if $MonError;

    @Problems = ();
    for ($i = 0; $i < $problems; $i++) {
	my ($id, $pname, $p1, $p2) = @t = expect_comm ('p', 4);
	m_error ("Invalid problem id: `$id'") unless ($id =~ /^[A-Za-z0-9_\-]{1,16}$/);
	m_error ("Invalid penalty: $p1") unless ($p1 =~ /^\d+$/ && $p1 <= 1000);
	m_error ("Invalid penalty: $p2") unless ($p2 =~ /^\d+$/ && $p2 <= 1000);
	m_error ("Dup problem id: $id") if ($IdToNum{$id} ne '');
	$IdToNum{$id} = $i;
	push @Problems, [$id, $pname, $p1, $p2, 
			 defined($ProblemTitle{$id}) ? $ProblemTitle{$id} : $pname,
			 $ProblemURL{$id}];
    }

    %Teams = @Teams = ();
    for ($i = 0; $i < $teams; $i++) {
	my ($id, $a1, $a2, $name) = my @t = expect_comm ('t', 4);
	m_error ("Invalid team id: `$id'") unless ($id =~ /^[A-Za-z0-9_\-]{1,10}$/);
	m_error ("Invalid monclass: $a1") unless ($a1 =~ /^\d+$/ && $a1 < 16);
	m_error ("Invalid monset: $a2") unless ($a2 =~ /^\d+$/ && $a2 <= 0x10000);
	m_error ("Dup team id: $id") if ($TeamToNum{$id} ne '');
	return undef if $MonError;
	$TeamToNum{$id} = $i;
	my $t = [$id, $a1, $a2, $name, 0, 0, 0, 0];
	$Teams{$id} = $t;
	push @Teams, $t;
    }
    my @A;
    for $i (0 .. $teams-1) { for my $j (0 .. $problems-1) { $A[$i][$j] = []; } }
    $IOI = 0;  $IOIScores = 0;
    my $lsu;  my $lsc;
    for ($i = 0; $i < $submissions; $i++) {
	&parse_line;
	m_error ("\@s expected but \@$cmd found") unless ($cmd eq 's' || $cmd eq '');
	m_error ("submissions counter mismatch") unless ($cmd eq 's');
	m_error ("parameter count mismatch") unless (@args >= 5 && @args <= 6);
	my ($tid, $pid, $att, $tim, $rc, $tn) = @args;
	m_error ("unknown team id `$tid'") unless ($Teams{$tid});
	m_error ("unknown problem id `$pid'") unless ($IdToNum{$pid} ne '');
	my $tm = $TeamToNum{$tid};  my $pr = $IdToNum{$pid};
	m_error ("invalid attempt number $att") 
	    unless ($att =~ /^\d+$/ && $att > 0 && $att < 1000);
	m_error ("invalid submission time $tim")
	    unless ($tim =~ /^\d+$/ && $tim < ($contlen + 10) * 60);
	my $ths = 0;
	$rc = $1 if $rc =~ /^\?(..)\?$/;
	$ths = -1 if $rc =~ /^[A-Z][A-Z]$/;
	$ths = 1 if $rc =~ /^((\d{1,3})|(\?\?)|(\-\-))$/;
	$IOIScores = 1 if $rc =~ /^\d{1,3}$/;
	$IOI = $ths unless $IOI;
	m_error ("invalid result code `$rc'") unless $ths;
	m_error ("mixed acm/ioi monitor") unless $ths == $IOI;
	m_error ("test number not expected for an OK/OC result") if (($rc eq 'OK' || $rc eq 'OC') && $tn ne '');
	m_error ("test number not expected in an ioi monitor") if ($IOI > 0 && $tn ne '' && $rc ne '--');
	return undef if $MonError;
	next if $i >= $submco;
	my $p = [$tim, $att, $rc, $tn, $tm, $pr];	
	if ($tim <= $effnow) {
	    push @{$A[$tm][$pr]}, $p;
	    $lsu = $p if ($rc ne 'NO' && $rc ne 'OC') and (!$lsu || $lsu->[0] <= $tim);
	    $lsc = $p if $rc eq 'OK' and (!$lsc || $lsc->[0] <= $tim);
	}
    }
    $IOI = 0 if $IOI < 0;

    my $Lsubm = $lsu && $lsu ne $lsc ? 
	'Last submission: '.conv_submit_line ($lsu)."<BR>\n" : undef;
    my $Lsucc = $lsc ? 
	'Last success: '.conv_submit_line ($lsc)."<BR>\n" : undef;

    my @C;
    for my $i (0 .. $teams-1) {
	for my $j (0 .. $problems-1) {
	    my $k;
	    my @L = sort {$$a[0] <=> $$b[0] || $$a[1] <=> $$b[1]} @{$A[$i][$j]};
	    my $k2 = scalar @L;
	    for ($k = 0; $k < @L; $k++) { 
		last if ($L[$k][2] eq 'OK'); 
		$k2 = $k if $L[$k][2] ne '--';
		last if ($L[$k][2] eq 'OC')
	    }
	    $k = $k2 if $IOI;
	    @L = @L[0 .. $k] if (@L && $k < @L);  
	    my @t = @{$L[$#L]};
	    my @R = (0, 0, 0, '', 0);
	    if ($t[2] eq 'OC') {
	      @R = (1, 0, $t[0], $t[2], 0);
	    } else {
              if (@L && !$IOI) {
                  @R = $t[2] eq 'OK' ? 
                      ($#L + 1, $Problems[$j][2] * 60 * $#L + $t[0], $t[0], $t[2], 0) : 
                      (-$#L- 1, $Problems[$j][3] * 60 * @L, $t[0], $t[2], $t[3]);
              }
              if (@L && $IOI) {
                  @R = $t[2] ne '--' ?
                      ($#L + 1, 0+$t[2], $t[0], $t[2], 0) :
                      (-$#L - 1, 0, $t[0], $t[2], 0);
              }
            }
	    $C[$i][$j] = [@R];
	    $Teams[$i][4]++ if ($R[0] > 0);
	    $Teams[$i][5] += $R[1];
	}
    }

    if ($IOI) {
	@SortedTeams = sort { $IOIScores ? $$b[5] <=> $$a[5] : $$b[4] <=> $$a[4] } @Teams;
    } else {
	@SortedTeams = sort {$$b[4] <=> $$a[4] || $$a[5] <=> $$b[5] || $$a[0] <=> $$b[0]} @Teams;
    }
    my $p = [0,0,0,0,-1,-1];  my $probr = 0;  my $rk = 0;  my $rgc = 0;
    for my $t (@SortedTeams) {
	$probr++ if ($$t[4] != $$p[4]);
	$rk++;  
	unless ($$t[5] == $$p[5] && ($IOIScores || $$t[4] == $$p[4])) {
	    $rg = $rk;  $rgc++;
	}
	$$t[6] = $rg;  $$t[7] = $IOIScores ? $rgc : $probr;  $p = $t; 
    }

    my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime ($time);
    my $date = sprintf ("%02d.%02d.%04d %02d:%02d:%02d", 
			$mday, $mon + 1, $year + 1900, $hour, $min, $sec);
    if (($state eq 'RUNNING' || $state eq 'FROZEN') && $now < $contlen*60) {
	$state = $state . ' ' . int($now/60) . '/' . $contlen; }
    $contlen = sprintf ('%d:%02d', int($contlen/60), $contlen%60);
    $contname = enc ($contname);

    my $Tm = $IOI ? 'Score' : 'Time';
    my $Tem = $IOI ? 'Participant' : 'Team';
    my $Res = <<HEAD;
Started at: <B>$startat</B><BR>
Duration: <B>$contlen</B><BR>
State: <B>$state</B><BR>
$Lsucc$Lsubm
<I>Last updated: $date</I><BR><BR>
<TABLE BORDER=1 CELLPADDING=4 CLASS=mtab>
<TR CLASS=head><TH>ID</TH><TH>$Tem</TH>
HEAD
    my $cw = 35;  my $cw2 = 25;
    if (!$hideproblems) {
        for my $p (@Problems) {
            my $href = $p->[5] ? " HREF=$$p[5]" : '';
            $Res .= "<TH WIDTH=$cw><A$href TITLE=\"$$p[4]\">$$p[0]</A></TH>";
        }
    }
    $Res .= "<TH WIDTH=$cw2>=</TH><TH>$Tm</TH><TH>Rank</TH>\n";
    my @Acc, @Rej;
    for my $t (@SortedTeams) {
	my @t = @{$t};  
	my $cls = ($IOIScores ? $t[7] : $t[7]) % 2 ? 'even' : 'odd';
	my $csf = ($t[0] eq $MonForTeam && $MonForTeam ne '') ? ' class=for' : '';
	my $t0 = $t[0];
	$t0 = "<A HREF=".$TeamURL{$t0}." CLASS=tli>$t0</A>" if exists $TeamURL{$t0};
	$tmn = $t[3];
	$tmn = "&nbsp" if ($tmn eq '') || ($tmn eq ' ');
	$Res .= "<TR class=$cls><TD$csf>$t0</TD><TD$csf>$tmn</TD>";
	my $tid = $t[0];  my $tn = $TeamToNum{$tid};
	if (!$hideproblems) {
    	for my $i (0 .. $#Problems) {
            my $ptr = $C[$tn][$i];
    	    my $r = $ptr->[0];
    	    my $tm = int ($ptr->[2] / 60);
    	    $tm = sprintf ("<BR>%d:%02d", int ($tm/60), $tm%60);
    	    $tm = '' unless ($showtimes);
    #	    $Res .= join ('|', '{', @$ptr, '}');
    	    if (!$IOI) {
              if ($r > 0) {$Acc[$i]++; $Rej[$i]+= $r - 1;} 
              elsif ($r < 0) {$Rej[$i]+=-$r;}

              if ($ptr->[3] eq 'OC') {$Res .= "<TD class=ok>*</TD>"; }
              elsif ($r > 1) { $r--; $Res .= "<TD class=ok>+$r$tm</TD>"; }
              elsif ($r == 1) { $Res .= "<TD class=ok>+$tm</TD>"; }
              elsif ($r == 0) { $Res .= "<TD class=no>.</TD>"; }
              else { $Res .= "<TD class=wa>$r$tm</TD>"; }
    	    } else {
              my $cd = $ptr->[3];
              $cd = $1 if $cd =~ /^([\?\-])/;
              if ($ptr->[3] eq 'OC') {$Res .= "<TD class=ok>*</TD>"; }
              elsif ($r > 0 && ($cd > 0 || $cd eq '?')) { 
                  $Res .= "<TD class=ok>$cd$tm</TD>"; 
              }
              elsif ($r > 0) { $Res .= "<TD class=wa>$cd$tm</TD>"; }
              elsif ($r == 0) { $Res .= "<TD class=no>.</TD>"; }
              else { $Res .= "<TD class=wa>$cd$tm</TD>"; }
    	    }
    	}
    }
	my $pen = $IOI ? $t[5] : int ($t[5] / 60);
	$Res .= "<TD class=solv>$t[4]</TD><TD class=pen>$pen</TD><TD class=rk>$t[6]</TD></TR>\n";
    }
   	if (!$IOI&&!$hideproblems) {
	  $cls = 'even';

	  $Res .= "<TR class=$cls><TD>&nbsp;</TD><TD class=no>Submits</TD>";
	  $cnt = 0;
      for my $i (0 .. $#Problems) {
        my $Tot = $Acc[$i]+$Rej[$i];
        $cnt += $Tot;
        $Tot = "&nbsp" unless $Tot;
        $Res .= "<TD class=no>$Tot</TD>";
      }
      $Res .= "<TD class=no>$cnt</TD><TD>&nbsp</TD><TD>&nbsp</TD></TR>";

	  $Res .= "<TR class=$cls><TD>&nbsp;</TD><TD class=ok>Accepted</TD>";
	  $cnt = 0;
      for my $i (0 .. $#Problems) {
        my $Tot = $Acc[$i];
        $cnt += $Tot;
        $Tot = "&nbsp" unless $Tot;
        $Res .= "<TD class=ok>$Tot</TD>";
      }
      $Res .= "<TD class=ok>$cnt</TD><TD>&nbsp</TD><TD>&nbsp</TD></TR>";

	  $Res .= "<TR class=$cls><TD>&nbsp;</TD><TD class=wa>Rejected</TD>";
	  $cnt = 0;
      for my $i (0 .. $#Problems) {
        my $Tot = $Rej[$i];
        $cnt += $Tot;
        $Tot = "&nbsp" unless $Tot;
        $Res .= "<TD class=wa>$Tot</TD>";
      }
      $Res .= "<TD class=wa>$cnt</TD><TD>&nbsp</TD><TD>&nbsp</TD></TR>";
   	}
    $Res .= "\n</TABLE>\n";
    return $MonError ? undef : $Res;
}

1;
1