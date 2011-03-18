require TswNetConf;

use Socket;
use Fcntl qw{O_NONBLOCK F_GETFL F_SETFL};

$NetError = 0;

%Chan = ();
&defChannel ('CONSOLE', 17240);
&defChannel ('SUBMIT', 17241);
&defChannel ('MSG', 17242);
&defChannel ('MONITOR', 17243);
&defChannel ('PRINTSOL', 17244);

$IP = $ENV{'REMOTE_ADDR'};
$Client = $IP ? "tsweb,".$IP : 'tsweb-text';

sub defChannel {
    my ($name, $port) = @_;
    $Chan{$name} = { 'name' => $name, 'port' => $port, 'sock' => undef,
		     'queue' => [], 'type' => 'Channel', 'partial' => undef,
	 	     'debug' => $NetDebug, 'noblock' => 1, 'flags' => undef };
}

sub setError {
    $NetError = shift unless $NetError;
}

sub getChannel {
    my $name = shift;
    return $name if ref($name) eq 'HASH' and $name->{'type'} eq 'Channel';
    return $Chan{$name} if exists $Chan{$name} and
	$Chan{$name}{'name'} eq $name;
    die "Unknown channel: $name\n";
}

sub setblockChannel {
    my ($C, $v) = @_;
    $C = getChannel ($C);
    return $C->{'noblock'} unless (!defined($C->{'flags'}) || 
	defined($v)) && defined($C->{'sock'});
    my $f = $C->{'flags'} = fcntl ($C->{'sock'}, F_GETFL, 0)
	or die "cannot fcntl(): $!";
    my $u = ($f & O_NONBLOCK) != 0;
    print "|$f|$u|$v|", O_NONBLOCK, "|\n" if $NetDebug;
    if (!$v == $u) {
	$f ^= O_NONBLOCK;
	print "fcntl(F_SETFL, $f)\n" if $NetDebug;
	fcntl ($C->{'sock'}, F_SETFL, $f) or die "cannot set fcntl(): $!";
	$f = $C->{'flags'} = fcntl ($C->{'sock'}, F_GETFL, 0)
	    or die "cannot fcntl(): $!";
	$u = ($f & O_NONBLOCK) != 0;
	die "cannot set O_NONBLOCK: fcntl() = $f" unless !$v == !$u;
    }
    return $C->{'noblock'} = $u;
}

sub openChannel {
    my $nb = $_[1];
    my $C = getChannel (shift);
    return $C if ($C->{'sock'});
    die "No port" unless $C->{'port'};
    my $iaddr = inet_aton ($TestsysIP) || die "no host: $TestsysIP";
    my $paddr = sockaddr_in ($C->{'port'}, $iaddr);
    my $proto = getprotobyname('tcp');
    print "Connecting to $TestsysIP:", $C->{'port'}, "...\n" if $NetDebug;
    socket(my $sock, PF_INET, SOCK_STREAM, $proto) || die "socket: $!";
    connect($sock, $paddr) || return die setError($!);
    $C->{'sock'} = $sock;
    $C->{'noblock'} = 0;
    $C->{'flags'} = undef;
    setblockChannel ($C, $nb);
    return $C;
}

sub closeChannel {
    my $C = getChannel (shift);
    my $sock = $C->{'sock'};
    if ($sock) { shutdown ($sock, 2);  close ($sock);  $C->{'sock'} = undef; }
}


sub dle_encode {
    local $_ = shift;
    s/([\x00-\x1f])/"\x18".chr(0x40+ord($1))/eg;
    $_;
}

sub dle_decode {
    local $_ = shift;
    s/\x18([\x40-\x5f])/chr(ord($1)-0x40)/eg;
    $_;
}

sub makereq {
    my $p = shift;
    my @L = ('---');
    $p->{'ID'} = sprintf ("%.9d", rand(1000000000)) unless exists($p->{'ID'});
    $p->{'Client'} = $Client if $Client;
    $p->{'Origin'} = $IP if $IP;
    for my $k (sort keys %$p) {
	push @L, "$k=".dle_encode($p->{$k});
    }
    return join ("\0", '', @L, '+++', '');
}

sub sendChannel {
    my $C = &openChannel (shift);
    my $req = &makereq (@_);
    print "Socket: ", $C->{'sock'}, ", port=", $C->{'port'}, "\n" if $NetDebug;
    print "Request: $req\n" if $NetDebug;
    my $tot = 0;
    my $endt = time + $SendTimeout;
    while (length $req) {
	my $res = send ($C->{'sock'}, $req, 0);
	$tot = $res < 0 ? $res : $tot + $res;
	selectWriteChannels ($SendTimeout, $C);
	last if $res <= 0 or $res == length $req;
	last if time > $endt;
	$req = substr ($req, $res);
    }
    die "send() returned $tot" unless $tot >= 0;
    return $tot;
}

sub recvChannel {
    my $C = &openChannel (shift);
    my $buff = undef;
    my $res = recv ($C->{'sock'}, $buff, 655360, 0);
    die "recv: $!" unless defined($buff);
    my $len = length $buff;
    print "(read ", length $buff, " bytes)\n" if $NetDebug;
    print "(BUFF: |$buff|)\n" if $NetDebug >= 3;
    my $R;
    my $on;
    if (defined ($C->{'partial'})) {
	$buff = $C->{'partial'} . $buff;
	$C->{'partial'} = undef;
    }
    my @L = split ("\0", $buff);
    my @E;
    for (@L) {
	print "Got: $_\n" if $NetDebug;
	push @E, $_ if $on;
	if ($_ eq '---') { $on = 1; $R = {}; @E = ('---'); }
	elsif ($_ eq '+++') {
	    push @{$C->{'queue'}}, $R if $on;
	    $on = 0;
	    $R = {};
	    @E = ();
	} elsif ($on && /^([A-Za-z_0-9]+)=(.*)$/) {
	    $R->{$1} = dle_decode ($2);
	}
    }
    $C->{'partial'} = join ("\0", @E) if $on;
    return $len;
}

sub readChannel {
    my $C = &getChannel (shift);
    return undef unless @{$C->{'queue'}};
    return shift @{$C->{'queue'}};
}

sub doreadChannel {
    my ($C, $f) = @_;
    my $C = &getChannel ($C);    
    my $R;
    my $endt = time + $Timeout;
    while (!($R = readChannel ($C))) {
	&selectChannels ($Timeout, $C);
	last unless recvChannel ($C);
	last if time > $endt;
	print "Partially received: ".length($C->{'partial'})." bytes\n" if $NetDebug;
	last if $f and $C->{'partial'} eq '';
    }
    print "*** end of doreadChannel() cycle ***\n" if $NetDebug;
    $R = readChannel ($C) unless $R;
    #print "doreadChannel() = $R\n" if $NetDebug;
    return $R;
}

sub selectChannels {
    my $timeout = shift;
    my $bits = '';
    for (@_) {
	my $C = getChannel ($_);
	vec ($bits, fileno($C->{'sock'}), 1) = 1 if defined ($C->{'sock'});
    }
    $nfound = select ($rout = $selwrite ? '' : $bits, $wout = $selwrite ? $bits : '', $eout = $bits, $timeout);
    $selwrite = 0;
    die "select: $!" if $nfound < 0;
    return $nfound;
}

sub selectWriteChannels {
    $selwrite = 1;
    &selectChannels;
}

sub selectAllChannels {
    selectChannels ($_[0], values %Chan);
}

sub pollAllChannels {
    for my $C (values %Chan) {
	if (defined ($C->{'sock'}) && $C->{'noblock'}) {
	    recvChannel ($C);
	}
    }
}


1;
