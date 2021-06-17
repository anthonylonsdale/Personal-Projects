# Storing file paths as strings
matches_path = "data/matches.db"
ratings_path = "data/ratings.db"
ratings_master_path = "data/ratings_master.db"
blocked_ids_path = "data/banned_ids.db"
guild_settings_path = "data/guild_settings.db"
env_path = 'data/.env'

path_list = [matches_path, ratings_master_path, ratings_path, blocked_ids_path,
             guild_settings_path, env_path]

days_of_backup_file_storage = 14
response_time = 60
delete_delay = 45
leaderboard_members = 25
maxwinsallowed = 15

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
        self.classa = self.client.get_emoji(847972991630573568)
        self.classb = self.client.get_emoji(847973003774263356)
        self.classc = self.client.get_emoji(847973016532418610)
        self.novice = self.client.get_emoji(847973027957571634)

    def rank_emoji(self):
        return {rank0: self.novice, rank1: self.classc, rank2: self.classb, rank3: self.classa, rank4: self.pm,
                rank5: self.m, rank6: self.gm}
