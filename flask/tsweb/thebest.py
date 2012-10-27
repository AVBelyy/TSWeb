#######@@######################
#      thebest in place       #
#        configuration        #
#####@@########################

DB_PATH = "thebest.db"
ADMIN_TEAM = "00"
ADMIN_PASSWORD = "cntgektyjr`1"

UPDATE_DELAY = 5 # in seconds

###############################

import os, time, json, argparse
from tsweb import util

DB_PATH = os.path.join(os.path.dirname(__file__), DB_PATH)

class TheBest():
    def __init__(self, db):
        self.db = db

    def _update_db(self):
        open(DB_PATH, "w").write(json.dumps(self.db))

    def _all_contests(self):
        state, answer = util.communicate("MSG", {
            "Team": ADMIN_TEAM,
            "Password": ADMIN_PASSWORD,
            "Command": "ListContests",
            "Mask": 1})

        answer, ans_id = answer
        contests = util.parse_contests(answer["Contests"].decode("cp866"))
        return ((c["id"], c["state"].split(",")[0]) for c in contests)

    def _update_contest(self, contest):
        state, answer = util.communicate("MSG", {
            "Team": ADMIN_TEAM,
            "Password": ADMIN_PASSWORD,
            "ContestId": contest,
            "DisableUnrequested": "1",
            "AllSubm": 1,
            "Command": "AllSubmits"})

        answer, ans_id = answer
        Max = {}
        for x in xrange(int(answer["Submits"])):
            Problem = answer.get("SubmProb_"+str(x), "")
            Team = answer.get("SubmTeam_"+str(x), "").split(" ", 1)[0]
            TL = float(answer.get("SubmTL_"+str(x), "").replace(" sec", "") or 100500)
            ML = float(answer.get("SubmML_"+str(x), "").replace("Mb", "") or 100500)
            Result = answer.get("SubmRes_"+str(x), "")
            if Result == "OK":
                if Problem in Max:
                    if TL <= Max[Problem][1] and ML < Max[Problem][2]:
                        Max[Problem] = [Team, TL, ML]
                else:
                    Max[Problem] = [Team, TL, ML]

        self.db[contest] = Max

    def index(self):
        cnt = 0
        for id, state in self._all_contests():
            cnt += 1
            self._update_contest(id)
        self._update_db()
        print "thebest: Indexed %d contests" % cnt

    def serve(self):
        while True:
            try:
                cnt = 0
                for id, state in filter(lambda (x, s): s == "RUNNING", self._all_contests()):
                    cnt += 1
                    self._update_contest(id)
                self._update_db()
                print "thebest: Updated %d contests" % cnt
                time.sleep(UPDATE_DELAY)
            except KeyboardInterrupt:
                print "Have a nice day!"
                break

parser = argparse.ArgumentParser(description="Make code competition more competitive.")
parser.add_argument("-f", "--first-time", dest="first_time",
                    action="store_const", const=True, default=(False or not os.path.exists(DB_PATH)),
                    help="(re)create db and index all the contests")

args = parser.parse_args()

if args.first_time:
    open(DB_PATH, "w").close()
    db = {}
else:
    db = json.load(open(DB_PATH))

app = TheBest(db)

if args.first_time:
    app.index()

# leave thebest running in an infinite loop
app.serve()
