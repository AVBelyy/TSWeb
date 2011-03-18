# Trivial authentification module:
# Looks for .tsauth in current directory, then in home directory
# Format of .tsauth file:
#   team=<team_id>
#   password=<password>

$TAuth = $RawTAuth = '.tsauth';

if (! -r $TAuth) {
    $TAuth = $ENV{'HOME'}.'/'.$TAuth;
}

open FILE, $TAuth || die "unable to read $TAuth: $!";

while (<FILE>) {
    chomp;
    $AUTH{$1} = $2 if /^\s*([A-Za-z]+)\s*=([\x20-\xff]*)$/;
}

close FILE;

($team, $password) = @AUTH{'team', 'password'};
die "No 'team=' entry found in $TAuth" if $team eq '';
die "No 'password=' entry found in $TAuth" if $password eq '';
print "(Team $team)\n";

