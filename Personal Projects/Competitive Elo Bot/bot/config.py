# Discord's authentication token for the bot
# **Eventually this will be separate**
token = "ODQwNzY4NTg4MDAwMTMzMTUx.YJdAxA.b0E9L5ik-2S0BM_5Hn2cysTOoj0"

# Storing file paths as strings
matches_path = "data/matches.db"
ratings_path = "data/ratings.db"
ratings_master_path = "data/ratings_master.db"
blocked_ids_path = "data/banned_ids.db"
days_of_backup_file_storage = 14

# Time in seconds before correspondence with bot is removed
delete_delay = 45
maxwinsallowed = 15
starting_elo = 1200
global_elo_floor = 900
starting_sigma = 150
name_of_bot = "Competitive Elo Tracker"

# Discord server's channel ID for the bot
bot_channel_id = 847304034310291456
leaderboard_channel_id = 845769329068605491
# Chadley's Discord ID
owner_id = 813330702712045590
# Server's admin role's ID
#bot_admin_role_id = 843673834333667369
bot_admin_role_id = 847978194702172160

rank0 = "Novice"
rank1 = "Class C"
rank2 = "Class B"
rank3 = "Class A"
rank4 = "Provisional Master"
rank5 = "Master"
rank6 = "Grandmaster"

# Rating based ranks in a key based array
#   "string" => integer
ranks = {rank0: 900, rank1: 1000, rank2: 1100, rank3: 1200, rank4: 1300, rank5: 1450, rank6: 1600}


class rankEmoji:
    def __init__(self, client=None):
        self.client = client
        self.gm = self.client.get_emoji(847972250685931540)
        self.m = self.client.get_emoji(847972968474083329)
        self.pm = self.client.get_emoji(847972981598584872)
        self.classa = self.client.get_emoji(847972981598584872)
        self.classb = self.client.get_emoji(847972981598584872)
        self.classc = self.client.get_emoji(847972981598584872)
        self.novice = self.client.get_emoji(847972981598584872)

    def rank_emoji(self):
        return {rank0: self.novice, rank1: self.classc, rank2: self.classb, rank3: self.classa, rank4: self.pm,
                rank5: self.m, rank6: self.gm}
