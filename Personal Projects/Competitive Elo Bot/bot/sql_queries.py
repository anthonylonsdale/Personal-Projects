from aiosqlite import connect
from bot.config import blocked_ids_path, ratings_path, ratings_master_path, matches_path, guild_settings_path


async def initialize_guild_settings():
    async with connect(guild_settings_path) as db:
        await db.execute('''create table if not exists guilds (
                   guild_id BIGINT PRIMARY KEY NOT NULL,
                   bot_channel_id BIGINT NOT NULL,
                   leaderboard_channel_id BIGINT NOT NULL,
                   bot_admin_id BIGINT NOT NULL,
                   starting_elo DECIMAL NOT NULL,
                   starting_sigma DECIMAL NOT NULL,
                   global_elo_floor DECIMAL NOT NULL,
                   unique(guild_id)
                   )''')
        await db.commit()


class createGuildSettings:
    def __init__(self, guild_id: int = None):
        self.id = guild_id

    async def initialize_tables(self):
        async with connect(blocked_ids_path) as db:
            await db.execute(f'''create table if not exists bans_{self.id} (
                       discord_id BIGINT PRIMARY KEY NOT NULL,
                       discord_name VARCHAR(50) NOT NULL,
                       date_banned DATETIME DEFAULT CURRENT_TIMESTAMP,
                       unique(discord_id)
                       )''')
            await db.commit()
        async with connect(ratings_path) as db:
            await db.execute(f'''create table if not exists ratings_{self.id} (
                       discord_id BIGINT PRIMARY KEY NOT NULL,
                       last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                       discord_name VARCHAR(50) NOT NULL,
                       clan_id VARCHAR(50) NOT NULL,
                       player_name VARCHAR(50) NOT NULL,
                       rating DECIMAL NOT NULL,
                       sigma DECIMAL NOT NULL,
                       wins INTEGER NOT NULL,
                       losses INTEGER NOT NULL,
                       unique(discord_id)
                       )''')
            await db.commit()
        async with connect(ratings_master_path) as db:
            await db.execute(f'''create table if not exists players_{self.id} (
                       discord_id BIGINT PRIMARY KEY NOT NULL,
                       entry_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                       discord_name VARCHAR(50) NOT NULL,
                       clan_id VARCHAR(50) NOT NULL,
                       player_name VARCHAR(50) NOT NULL,
                       unique(discord_id)
                       )''')
            await db.commit()
        async with connect(matches_path) as db:
            await db.execute(f'''create table if not exists matches_{self.id} (
                       id INTEGER PRIMARY KEY NOT NULL,
                       entry_date DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                       player_a VARCHAR(50) NOT NULL,
                       player_a_score TINYINT NOT NULL,
                       player_a_old_elo DECIMAL NOT NULL,
                       player_a_old_sigma DECIMAL NOT NULL,
                       player_a_new_elo DECIMAL NOT NULL,
                       player_a_new_sigma DECIMAL NOT NULL,
                       player_b VARCHAR(50) NOT NULL,
                       player_b_score TINYINT NOT NULL,
                       player_b_old_elo DECIMAL NOT NULL,
                       player_b_old_sigma DECIMAL NOT NULL,
                       player_b_new_elo DECIMAL NOT NULL,
                       player_b_new_sigma DECIMAL NOT NULL,
                       inputted_user_name VARCHAR(50) NOT NULL,
                       inputted_user_id BIGINT NOT NULL,
                       unique(id)
                       )''')
            await db.commit()
