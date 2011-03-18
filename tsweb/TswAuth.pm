require TswConf;
require ReadArgs;

sub http_cookies {
    return qq|Set-Cookie: tsw=""; expires=Fri, 17-Feb-2006 00:00:00 GMT; path=$cgiroot \n|
	if $CookieState < 0;
    return undef if $CookieState < 2 or !valid_teamname($team) or $password eq '';
    my $bake = "$team|" . cypher_pwd(time + 3600*6, $password) . '|' . "$contestid|";
    return qq|Set-Cookie: tsw="$bake"; path=$cgiroot \n|;
}

sub valid_teamname {
    shift =~ /^[A-Za-z\-\_0-9]{1,8}$/;
}

sub valid_contestid {
    shift =~ /^[A-Za-z\-\_0-9]{0,32}$/;
}

sub decypher_pwd {
    srand shift ^ 0x3ae6;
    my @L = map { ord $_ } split (//, pack ('H*', shift));
    @L = map { $_ ^ int(256*rand) } @L;
    my $s = 0;
    for my $a (@L) {
	$s += $a;
	$r .= chr $a;
    }
    my $l = $L[0]*256 + $L[1];
    return undef if ($s & 255) or ($l + 3 != scalar @L);
    my $r = join ('', map { chr $_ } @L[2 .. $#L-1]);
    return undef if $r =~ /\x0/;
    return $r;
}

sub cypher_pwd {
    my ($r, $p) = @_;
    srand $r ^ 0x3ae6;
    my @L = split (//, $p);
    my $l = scalar @L;
    for my $a (@L) { $a = ord $a; }
    unshift @L, $l & 255;
    unshift @L, $l >> 8;
    my $s = 0;
    for my $a (@L) { $s += 256 - $a; }
    push @L, $s & 255;
    @L = map { $_ ^ int(256*rand) } @L;
    return sprintf ("%.8x", $r) . join ('', map { sprintf ("%02x", $_) } @L);
}


sub an_cookies {
    my ($t, $p, $c, $s) = my @L = split (/\|/, $COOKIE{'tsw'});
    $team = $password = undef;
    $CookieState = 0;
    return undef unless $t ne '';
    $CookieState = -1;
    return undef unless valid_teamname ($t);
    return undef unless valid_contestid ($c);
    return undef unless $p =~ /^([a-f0-9][a-f0-9]){10,300}$/;
    $p =~ /^(.{8,8})(.*)$/;
    $CookieState = -2;
    return undef if time() > hex($1);
    $password = decypher_pwd (hex($1), $2);
    return undef unless defined $password;
    $CookieState = 1;
    $contestid = $c;
    return $team = $t;
}

an_cookies();
if ($trivauth) {
    require TswTrivAuth;
    $CookieState = 16;
}

srand;

1;

