import discord
from discord.ext import commands
import os
import sys
import datetime
import glob
import re
import asyncio
import logging
import sqlite3
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bot.config import *
import bot.glicko
from bot.sql_queries import *

if __name__ == '__main__':
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    db_conn = sqlite3.connect(matches_path)
    cursor = db_conn.cursor()
    cursor.execute(table_create_matches)
    db_conn.commit()
    db_conn.close()

    db_conn = sqlite3.connect(ratings_master_path)
    cursor = db_conn.cursor()
    cursor.execute(table_create_players)
    db_conn.commit()
    db_conn.close()

    db_conn = sqlite3.connect(ratings_path)
    cursor = db_conn.cursor()
    cursor.execute(table_create_ratings)
    db_conn.commit()
    db_conn.close()

    db_conn = sqlite3.connect(blocked_ids_path)
    cursor = db_conn.cursor()
    cursor.execute(table_create_ban_ids)
    db_conn.commit()
    db_conn.close()

    prefix = '.'
    client = commands.Bot(command_prefix=prefix)
    client.remove_command('help')
    start_time = datetime.datetime.now().astimezone()

    if not os.path.exists(blocked_ids_path):
        f = open(blocked_ids_path, "w")
        f.close()

    @client.command("ping", aliases=['p'])
    @commands.has_role('Bot Admin')
    async def ping(ctx):
        await ctx.send(f'Bot Response Time: {round(client.latency * 1000)}ms ', delete_after=delete_delay)

    """
    @client.command("setup")
    @commands.has_permissions(administrator=True)
    async def setup(ctx):
        pass
        guild = ctx.message.guild
        bot_channel = await guild.create_text_channel('ratings-bot')
        leaderboard_channel = await guild.create_text_channel('top-25-leaderboard')
        print(bot_channel.id)
        print(leaderboard_channel.id)
    """

    @client.command("block", aliases=['bl'])
    @commands.has_role('Bot Admin')
    async def block_id(ctx, id_to_block: str = None):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if id_to_block is None:
            await ctx.send("What user do you want to prohibit? Format: @username", delete_after=delete_delay)
            try:
                blockid = await client.wait_for("message", check=check, timeout=delete_delay)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            id_to_block = blockid.content

        user = await client.fetch_user(id_to_block)
        name = user.name

        db_conn = sqlite3.connect(blocked_ids_path)
        cursor = db_conn.cursor()
        cursor.execute("insert or ignore into bans (discord_id, discord_name) values (?, ?)", (id_to_block, name))
        db_conn.commit()
        db_conn.close()


    @client.command("unblock", aliases=['un'])
    @commands.has_role('Bot Admin')
    async def unblock_id(ctx, id_to_unblock: str = None):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if id_to_unblock is None:
            await ctx.send("What user do you want to allow commands from? Format: @username", delete_after=delete_delay)

            try:
                unblockid = await client.wait_for("message", check=check, timeout=delete_delay)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return

            id_to_unblock = unblockid.content

        with open(blocked_ids_path, 'r+') as f0:
            data = f0.readlines()
            f0.seek(0)
            for line in data:
                if id_to_unblock in line:
                    continue
                f0.write(line)
            f0.truncate()

    # completed
    @client.command("backupratings", aliases=['br', 'backup'])
    @commands.has_role('Bot Admin')
    async def backup(ctx):
        todays_date = datetime.date.today().strftime("%m-%d-%Y")
        backup_file = f'./data/ratings_backup_{todays_date}.db'
        source = sqlite3.connect(ratings_path)
        destination = sqlite3.connect(backup_file)
        source.backup(destination)
        source.close()

        # prunes old backups
        backup_files = glob.glob('./data/ratings_backup_*.db')
        for file in backup_files:
            re_match = re.search(r'\d{2}-\d{2}-\d{4}', file)
            date = datetime.datetime.strptime(re_match.group(), '%m-%d-%Y').date()
            date_cutoff = datetime.date.today() - datetime.timedelta(days=days_of_backup_file_storage)
            if date_cutoff > date:
                pruned_backup = str('./') + str(file)
                os.remove(pruned_backup)

        await ctx.send(f"ELO backed up for today {todays_date}", delete_after=delete_delay)

    # completed
    @client.command("restoreratings", aliases=['rr', 'restore'])
    @commands.has_role('Bot Admin')
    async def restore(ctx):
        backup_files = glob.glob('./data/ratings_backup_*.db')
        await ctx.send(f"Input date to restore ratings from (format mo-dy-year).\n"
                       f"Available dates to restore from: {backup_files}", delete_after=delete_delay)

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        try:
            date_to_restore = await client.wait_for("message", check=check, timeout=delete_delay)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return

        try:
            backup_file = f'./data/ratings_backup_{date_to_restore.content}.db'
            source = sqlite3.connect(backup_file)
            destination = sqlite3.connect(ratings_path)
            source.backup(destination)
            source.close()
        except Exception as e:
            await ctx.send(f"Could not find backup for the date specified, error: {e}", delete_after=delete_delay)
            return

        await ctx.send(f'ELO data restored from backup made on {date_to_restore.content}', delete_after=delete_delay)

    # completed
    @client.command("listmembers", aliases=['lm'])
    @commands.has_role('Bot Admin')
    async def list_members(ctx):
        con = sqlite3.connect(ratings_master_path)
        rm = pd.read_sql_query("select clan_id, player_name from players", con)
        await ctx.send(f"There are {len(rm.index)} ranked members\n {rm}", delete_after=delete_delay)
        con.close()

    # completed
    @client.command("match", aliases=['m'])
    async def match(ctx, personone: str = None, persononewins: int = None, persontwo: str = None,
                    persontwowins: int = None):

        emoji_object = rankEmoji(client=client)
        rank_emojis = emoji_object.rank_emoji()

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if personone is None or persononewins is None or persontwo is None or persontwowins is None:
            await ctx.send(f"Input new match to influence rating, format is Name1 (wins) Name2 (wins), example: "
                           f"<BestClan>AlphaBeta 5 <WorstClan>OmegaLambda 5. Global Elo floor is {global_elo_floor}. "
                           f"There is no Elo ceiling.", delete_after=delete_delay)

            try:
                match_msg = await client.wait_for("message", check=check, timeout=delete_delay)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            match_array = match_msg.content.split()
            personone = match_array[0]
            persononewins = int(match_array[1])
            persontwo = match_array[2]
            persontwowins = int(match_array[3])

        if persononewins > maxwinsallowed or persontwowins > maxwinsallowed:
            await ctx.send(f'You have exceeded the number of wins allowed in a single session ({maxwinsallowed})',
                           delete_after=delete_delay)
            return

        if personone == persontwo:
            await ctx.send("You cannot input a match against yourself", delete_after=delete_delay)
            return

        con = sqlite3.connect(ratings_master_path)
        cur = con.cursor()
        cur.execute("select * from players where player_name like ?", (personone,))
        # need to insert a check if multiple names are returned
        p1_info = cur.fetchall()
        if p1_info is None:
            await ctx.send(f'<@{ctx.author.id}> {personone} was not detected in the database!',
                           delete_after=delete_delay)
            return

        cur.execute("select * from players where player_name like ?", (persontwo,))
        p2_info = cur.fetchall()
        if p2_info is None:
            await ctx.send(f'<@{ctx.author.id}> {persontwo} was not detected in the database!',
                           delete_after=delete_delay)
            return
        con.close()

        con = sqlite3.connect(ratings_path)
        cur = con.cursor()
        cur.execute("select rating, sigma from ratings where discord_id = ?", (p1_info[0][0],))
        p1_r_s_tuple = cur.fetchall()[0]
        p1_old_rating = p1_r_s_tuple[0]
        p1_old_sigma = p1_r_s_tuple[1]

        cur.execute("select rating, sigma from ratings where discord_id = ?", (p2_info[0][0],))
        p2_r_s_tuple = cur.fetchall()[0]
        p2_old_rating = p2_r_s_tuple[0]
        p2_old_sigma = p2_r_s_tuple[1]
        con.close()

        playeroneobject = bot.glicko.Player(rating=p1_old_rating, rd=p1_old_sigma)
        playertwoobject = bot.glicko.Player(rating=p2_old_rating, rd=p2_old_sigma)

        for i in range(persononewins):
            playeroneobject.update_player([p2_old_rating], [p2_old_sigma], [1])
            playertwoobject.update_player([p1_old_rating], [p1_old_sigma], [0])
        for i in range(persontwowins):
            playertwoobject.update_player([p2_old_rating], [p2_old_sigma], [1])
            playeroneobject.update_player([p1_old_rating], [p1_old_sigma], [0])

        p1_new_rating = round(playeroneobject.get_rating(), 2)
        if p1_new_rating < 900:
            p1_new_rating = 900
        p1_new_sigma = round(playeroneobject.get_rd(), 2)

        p2_new_rating = round(playertwoobject.get_rating(), 2)
        if p2_new_rating < 900:
            p2_new_rating = 900
        p2_new_sigma = round(playertwoobject.get_rd(), 2)

        con = sqlite3.connect(ratings_path)
        cur = con.cursor()
        cur.execute("update ratings set rating = ?, sigma = ?, wins = ?, losses = ? where discord_id = ?;",
                    (p1_new_rating, p1_new_sigma, persononewins, persontwowins, p1_info[0][0],))
        con.commit()
        cur.execute("update ratings set rating = ?, sigma = ?, wins = ?, losses = ? where discord_id = ?;",
                    (p2_new_rating, p2_new_sigma, persontwowins, persononewins, p2_info[0][0],))
        con.commit()
        con.close()

        author = str(ctx.author)
        author_id = ctx.author.id

        role = discord.utils.get(ctx.guild.roles, id=bot_admin_role_id)
        if ctx.author.id == p1_info[0][0]:
            await ctx.send(f'<@{p2_info[0][0]}> A match involving you was just added. The match results have been sent '
                           f'to you for your perusal', delete_after=delete_delay)
            user = await client.fetch_user(p2_info[0][0])
            await user.send(f'<@{p2_info[0][0]}>, A match was added with a score of {persononewins} wins for '
                            f'{personone} and {persontwowins} wins for {persontwo}, if this result is incorrect, please'
                            f' contact the Bot Administrators.\nOld Elo: {p2_old_rating}   Old Sigma: {p2_old_sigma}.'
                            f'\nNew Elo: {p2_new_rating}   New Sigma: {p2_new_sigma}.')

        elif ctx.author.id == p2_info[0][0]:
            await ctx.send(f'<@{p1_info[0][0]}> A match involving you was just added. The match results have been sent '
                           f'to you for your perusal', delete_after=delete_delay)
            user = await client.fetch_user(p1_info[0][0])
            await user.send(f'<@{p1_info[0][0]}>, A match was added with a score of {persononewins} wins for '
                            f'{personone} and {persontwowins} wins for {persontwo}, if this result is incorrect, please'
                            f' contact the Bot Administrators.\nOld Elo: {p2_old_rating}   Old Sigma: {p2_old_sigma}.'
                            f'\nNew Elo: {p2_new_rating}   New Sigma: {p2_new_sigma}.')

        else:
            if role in ctx.author.roles:
                await ctx.send(f'<@{p1_info[0][0]}> <@{p2_info[0][0]}> A match involving you was just added. The match '
                               f'results have been sent to you for your perusal', delete_after=delete_delay)
            else:
                await ctx.send(f"<@{ctx.author.id}>You cannot input a match concerning two other people!",
                               delete_after=delete_delay)
                return

        con = sqlite3.connect(matches_path)
        cur = con.cursor()
        params = (personone, persononewins, p1_old_rating, p1_old_sigma, p1_new_rating, p1_new_sigma, persontwo,
                  persontwowins, p2_old_rating, p2_old_sigma, p2_new_rating, p2_new_sigma, author, author_id)
        cur.execute(f"insert into matches (player_a, player_a_score, player_a_old_elo, player_a_old_sigma,"
                    f"player_a_new_elo, player_a_new_sigma, player_b, player_b_score, player_b_old_elo,"
                    f"player_b_old_sigma, player_b_new_elo, player_b_new_sigma, inputted_user_name, "
                    f"inputted_user_id) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", params)
        con.commit()
        con.close()

        rankp1 = None
        emoji1 = None
        for rank in ranks:
            if p1_new_rating >= ranks[rank]:
                rankp1 = rank
                emoji1 = rank_emojis[rank]
            else:
                break

        rankp2 = None
        emoji2 = None
        for rank in ranks:
            if p2_new_rating >= ranks[rank]:
                rankp2 = rank
                emoji2 = rank_emojis[rank]
            else:
                break

        if p1_new_rating < p1_old_rating:
            color1 = f'```diff\n- {p1_new_rating} {rankp1}\nnew Sigma {p1_new_sigma} \n```'
        elif p1_new_rating > p1_old_rating:
            color1 = f'```diff\n+ {p1_new_rating} {rankp1}\nnew Sigma {p1_new_sigma} \n```'
        else:
            color1 = 'Ratings are unchanged'

        if p2_new_rating < p2_old_rating:
            color2 = f'```diff\n- {p2_new_rating} {rankp2}\nnew Sigma {p2_new_sigma} \n```'
        elif p2_new_rating > p2_old_rating:
            color2 = f'```diff\n+ {p2_new_rating} {rankp2}\nnew Sigma {p2_new_sigma} \n```'
        else:
            color2 = 'Ratings are unchanged'

        await ctx.send(f"Updated Ratings (automatically saved to file):\n\n{personone}\'s Rank: {emoji1} {color1}\n"
                       f"{persontwo}\'s Rank: {emoji2} {color2}", delete_after=delete_delay)

    # completed
    @client.command("filecontents", aliases=['fc'])
    @commands.has_role('Bot Admin')
    async def file_contents(ctx):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        user = await client.fetch_user(ctx.author.id)

        con = sqlite3.connect(ratings_path)
        ratings_embed = discord.Embed(title="Contents of \'ratings.db\'")
        ratings = pd.read_sql_query("select * from ratings", con)
        for item in zip(*ratings.to_dict("list").values()):
            ratings_embed.add_field(name=item[0], value=str(item), inline=False)
        await user.send(embed=ratings_embed, delete_after=delete_delay)
        con.close()

        con = sqlite3.connect(ratings_master_path)
        ratings_master_embed = discord.Embed(title="Contents of \'ratings_master.db\'")
        rm = pd.read_sql_query("select * from players", con)
        for item in zip(*rm.to_dict("list").values()):
            ratings_master_embed.add_field(name=item[0], value=str(item), inline=False)
        await user.send(embed=ratings_master_embed, delete_after=delete_delay)
        con.close()

        con = sqlite3.connect(matches_path)
        match_backup_embed = discord.Embed(title="Contents of \'matches.db\'")
        dfmatches = pd.read_sql_query("select * from matches", con)
        for item in zip(*dfmatches.to_dict("list").values()):
            match_backup_embed.add_field(name=item[0], value=str(item), inline=False)
        await user.send(embed=match_backup_embed, delete_after=delete_delay)
        con.close()

        await ctx.send("Input which line of which file you want to delete:\nformat (file_name  line-#)",
                       delete_after=delete_delay)

        try:
            msg = await client.wait_for("message", check=check, timeout=delete_delay)
            if msg.content == 'stop':
                return
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return
        split_msg = msg.content.split(' ')
        file_name = split_msg[0]
        line_no = split_msg[1]

        if 'matches' in file_name:
            con = sqlite3.connect(matches_path)
            cur = con.cursor()
            cur.execute("delete from matches where rowid = ?;", line_no)
            con.commit()
            con.close()
            return
        elif 'ratings_master' in file_name:
            con = sqlite3.connect(ratings_master_path)
            cur = con.cursor()
            cur.execute("delete from players where rowid = ?;", line_no)
            con.commit()
            con.close()
            return
        elif 'ratings' in file_name:
            con = sqlite3.connect(ratings_path)
            cur = con.cursor()
            cur.execute("delete from players where rowid = ?;", line_no)
            con.commit()
            con.close()
            return

        await ctx.send(f"Line {line_no} in File {file_name} has been removed", delete_after=delete_delay)

    # completed
    @client.command("editelo", aliases=['ee'])
    @commands.has_role('Bot Admin')
    async def edit_elo(ctx, name: str = None, newelo: str = None):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if name is None or newelo is None:
            await ctx.send("Who\'s elo do you want to change? format: user newelo", delete_after=delete_delay)

            try:
                msg = await client.wait_for("message", check=check, timeout=delete_delay)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            name = msg.content.split()[0]
            newelo = msg.content.split()[1]

        con = sqlite3.connect(ratings_path)
        cur = con.cursor()
        cur.execute("update ratings set rating = ? where player_name = ?;", (newelo, name,))
        con.commit()
        con.close()

        await ctx.send(f"{name}\'s elo has been changed to {newelo}")

    # completed
    @client.command("editsigma", aliases=['es'])
    @commands.has_role('Bot Admin')
    async def edit_sigma(ctx, name: str = None, newsigma: str = None):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if name is None or newsigma is None:
            await ctx.send("Who\'s sigma do you want to change? format: user newsigma", delete_after=delete_delay)

            try:
                msg = await client.wait_for("message", check=check, timeout=delete_delay)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return

            name = msg.content.split()[0]
            newsigma = msg.content.split()[1]

        # No ID checks needed because this is an admin only command
        con = sqlite3.connect(ratings_path)
        cur = con.cursor()
        cur.execute("update ratings set sigma = ? where player_name = ?;", (newsigma, name,))
        con.commit()
        con.close()

        await ctx.send(f'{name}\'s sigma has been changed to {newsigma}')

    # completed
    @client.command('editname', aliases=['en'])
    async def edit_member(ctx, name: str = None):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if name is None:
            await ctx.send("Input the name to be edited (Note that you may only change the name that is associated with"
                           " your unique Discord tag)", delete_after=delete_delay)

            try:
                old_name = await client.wait_for("message", check=check, timeout=delete_delay)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            name = old_name.content

        try:
            await ctx.send("Enter new name:", delete_after=delete_delay)
            new_name = await client.wait_for("message", check=check, timeout=delete_delay)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return

        role = discord.utils.get(ctx.guild.roles, id=bot_admin_role_id)
        conn = sqlite3.connect(ratings_master_path)
        cur = conn.cursor()
        # bot admins are not checked for ids
        if role in ctx.author.roles:
            cur.execute("update players set player_name = ? where player_name = ?;", (new_name.content, name,))
            conn.commit()
            cur.execute("select discord_id from players where player_name = ?", (new_name.content,))
            # have to do this strange conversion because current.fetchone returns a nonetype
            await ctx.send(f"<@{str(cur.fetchone())[1:-2]}> Your name was changed from {name} to {new_name.content}")
            conn.close()

            conn = sqlite3.connect(ratings_path)
            cur = conn.cursor()
            cur.execute("update ratings set player_name = ? where player_name = ?;", (new_name.content, name,))
            conn.commit()
            conn.close()
            return

        # a non bot admin can only ever change their own name
        cur.execute("update players set player_name = ? where discord_id = ?;", (new_name.content, ctx.author.id,))
        conn.commit()
        conn.close()

        conn = sqlite3.connect(ratings_path)
        cur = conn.cursor()
        cur.execute("update ratings set player_name = ? where discord_id = ?;", (new_name.content, ctx.author.id,))
        conn.commit()
        conn.close()

        await ctx.send(f"<@{ctx.author.id}> Your name has been updated", delete_after=delete_delay)

    # completed
    @client.command('stats', aliases=['s'])
    async def member_stats(ctx, name: str = None):
        if name is None:
            await ctx.send(f"Who\'s stats do you want to check?", delete_after=delete_delay)

            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel

            try:
                msg = await client.wait_for("message", check=check, timeout=delete_delay)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            name = msg.content

        conn = sqlite3.connect(ratings_master_path)
        cur = conn.cursor()
        cur.execute("select 1 from players where player_name = ? limit 1", (name,))
        if cur.fetchone() is None:
            await ctx.send(f'<@{ctx.author.id}> {name} has not been added to the database!', delete_after=delete_delay)
            return
        conn.close()

        conn = sqlite3.connect(ratings_path)
        ratings = pd.read_sql_query("select clan_id, player_name, rating, sigma, wins, losses from ratings where "
                                    "player_name = ?", params=(name,), con=conn)
        for item in zip(*ratings.to_dict("list").values()):
            await ctx.send(f"Stats for {item[0]}{item[1]}:\nRating: {item[2]}\nSigma: {item[3]}\n"
                           f"Wins: {item[4]}\nLosses: {item[5]}", delete_after=delete_delay)
        conn.close()

    # completed
    @client.command("admin_add", aliases=['aa'])
    @commands.has_role("Bot Admin")
    async def admin_add(ctx, d_id=None, name: str = None):
        if d_id is None or name is None:
            await ctx.send(f'<@{ctx.author.id}> First Arg: @Username Second Arg: <Clan>Name', delete_after=delete_delay)
            return
        if '@' in d_id:
            d_id = d_id[3:-1]

        user = await client.fetch_user(d_id)
        try:
            split = name.split('>')
            clan = split[0] + '>'
            name = split[1]
        except IndexError:
            clan = '<>'

        con = sqlite3.connect(ratings_master_path)
        cur = con.cursor()
        cur.execute("select 1 from players where discord_id = ? limit 1", (d_id,))

        if cur.fetchone() is None:
            cur.execute("insert into players (discord_id, discord_name, clan_id, player_name) values (?, ?, ?, ?)",
                        (d_id, str(user), clan, name))
            con.commit()
            con.close()
        else:
            await ctx.send(f'<@{ctx.author.id}> The inputted Discord ID was already detected in the database!',
                           delete_after=delete_delay)
            return

        con = sqlite3.connect(ratings_path)
        cur = con.cursor()
        cur.execute("insert into ratings (discord_id, discord_name, clan_id, player_name, rating, sigma, wins, losses) "
                    "values (?, ?, ?, ?, ?, ?, ?, ?)",
                    (d_id, str(user), clan, name, starting_elo, starting_sigma, 0, 0))
        con.commit()
        con.close()
        await ctx.send(f'<@{ctx.author.id}> You successfully registered <@{d_id}> in the database, GLHF!',
                       delete_after=delete_delay)

    # completed
    @client.command("add", aliases=['a'])
    async def add_member(ctx, name: str = None):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if name is None:
            await ctx.send(f"Input new member for leaderboard ranking, Format is <clan>name, i.e. "
                           f"<BestClan>Example. Warning, your unique Discord tag will be associated with your "
                           f"inputted name, so do not input anybody except yourself. If you make a typo, please use "
                           f"the .editname command.\nElo starts at {starting_elo} and Sigma starts at {starting_sigma} "
                           f"for all players", delete_after=delete_delay)
            try:
                msg = await client.wait_for("message", check=check, timeout=delete_delay)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            name = msg.content

        try:
            split = name.split('>')
            clan = split[0] + '>'
            name = split[1]
        except IndexError:
            clan = '<>'

        con = sqlite3.connect(ratings_master_path)
        cur = con.cursor()
        cur.execute("select 1 from players where discord_id = ? limit 1", (ctx.author.id,))

        if cur.fetchone() is None:
            cur.execute("insert into players (discord_id, discord_name, clan_id, player_name) values (?, ?, ?, ?)",
                        (ctx.author.id, str(ctx.author), clan, name))
            con.commit()
            con.close()
        else:
            await ctx.send(f'<@{ctx.author.id}> Your Discord ID was already detected in the database! If you need '
                           f'to edit your name, use the .editname command', delete_after=delete_delay)
            return

        con = sqlite3.connect(ratings_path)
        cur = con.cursor()
        cur.execute("insert into ratings (discord_id, discord_name, clan_id, player_name, rating, sigma, wins, losses) "
                    "values (?, ?, ?, ?, ?, ?, ?, ?)",
                    (ctx.author.id, str(ctx.author), clan, name, starting_elo, starting_sigma, 0, 0))
        con.commit()
        con.close()
        await ctx.send(f'<@{ctx.author.id}> You were successfully registered in the database, GLHF!',
                       delete_after=delete_delay)

    # completed
    @client.command('delete', aliases=['d'])
    @commands.has_role('Bot Admin')
    async def delete_member(ctx, name: str = None):
        if name is None:
            await ctx.send("Who do you want to remove from the database?", delete_after=delete_delay)

            def check(message):
                return message.author == ctx.author and message.channel == ctx.channel

            try:
                msg = await client.wait_for("message", check=check, timeout=delete_delay)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            name = msg.content

        try:
            split = name.split('>')
            name = split[1]
        except IndexError:
            pass

        conn = sqlite3.connect(ratings_master_path)
        cur = conn.cursor()
        dfmatches = pd.read_sql_query("select player_name from players where player_name = ?", params=(name,),
                                      con=conn)
        for item in zip(*dfmatches.to_dict("list").values()):
            await ctx.send(f'{item[0]} was successfully removed from the database', delete_after=delete_delay)
        cur.execute("delete from players where player_name = ?", (name,))
        conn.commit()
        conn.close()

        conn = sqlite3.connect(ratings_path)
        cur = conn.cursor()
        cur.execute("delete from ratings where player_name = ?;", (name,))
        conn.commit()
        conn.close()

    # broken
    async def refresh_leaderboard():
        pass
        emoji_object = rankEmoji(client=client)
        rank_emojis = emoji_object.rank_emoji()
        channel = client.get_channel(leaderboard_channel_id)
        messages = await channel.history(limit=1).flatten()

        if len(messages) == 0:
            await leaderboard()
        else:
            for message in messages:
                if message.author.name == name_of_bot:
                    message_id = message.id
                    message = await channel.fetch_message(message_id)
                    elo_ranking = []
                    with open(ratings_path, 'r') as file:
                        for i, line in enumerate(file.readlines(), 1):
                            try:
                                sigma = float(line.split()[4])
                                elo = float(line.split()[2])
                                name = str(line.split()[0])
                                elo_ranking.append((name, elo, sigma))
                            except IndexError:
                                pass
                    sorted_elo_ranking = sorted(elo_ranking, key=lambda tup: tup[1], reverse=True)
                    new_embed = discord.Embed(title="Current Top 25 leaderboard by Elo rating:")
                    for i in range(25):
                        if i == len(sorted_elo_ranking):
                            break
                        name_string = f'{i+1}) {sorted_elo_ranking[i][0]}'
                        rank = None
                        emoji = None
                        for k in ranks:
                            if float(sorted_elo_ranking[i][1]) >= ranks[k]:
                                rank = k
                                emoji = rank_emojis[rank]
                            else:
                                break

                        value_string = f'{sorted_elo_ranking[i][1]} ({rank}) Sigma: {sorted_elo_ranking[i][2]}'
                        new_embed.add_field(name=name_string, value=f'{emoji} ' + value_string, inline=False)
                    await message.edit(embed=new_embed)

    # broken
    async def leaderboard():
        pass
        emoji_object = rankEmoji(client=client)
        rank_emojis = emoji_object.rank_emoji()
        channel = client.get_channel(leaderboard_channel_id)
        elo_ranking = []
        with open(ratings_path, 'r') as file:
            for i, line in enumerate(file.readlines(), 1):
                try:
                    sigma = float(line.split()[4])
                    elo = float(line.split()[2])
                    name = str(line.split()[0])
                    elo_ranking.append((name, elo, sigma))
                except IndexError:
                    pass
        sorted_elo_ranking = sorted(elo_ranking, key=lambda tup: tup[1], reverse=True)
        embed = discord.Embed(title="Current Top 25 leaderboard by Elo rating:")
        for i in range(25):
            if i == len(sorted_elo_ranking):
                break
            name_string = f'{i+1}) {sorted_elo_ranking[i][0]}'
            rank = None
            emoji = None
            for k in ranks:
                if float(sorted_elo_ranking[i][1]) >= ranks[k]:
                    rank = k
                    emoji = rank_emojis[rank]
                else:
                    break

            value_string = f'{sorted_elo_ranking[i][1]} ({rank}) Sigma: {sorted_elo_ranking[i][2]}'
            embed.add_field(name=name_string, value=f'{emoji} {value_string}', inline=False)
        await channel.send(embed=embed)


    @client.command('uptime', aliases=['up'])
    async def uptime(ctx):
        now = datetime.datetime.now().astimezone()
        delta = now - start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        if days:
            time_format = "**{d}** days, **{h}** hours, **{m}** minutes, and **{s}** seconds."
        else:
            time_format = "**{h}** hours, **{m}** minutes, and **{s}** seconds."
        uptime_stamp = time_format.format(d=days, h=hours, m=minutes, s=seconds)
        await ctx.send(f"{client.user.name} has been up for {uptime_stamp}", delete_after=10)


    @client.command('help', aliases=['h'])
    async def help_command(ctx):
        embed = discord.Embed(colour=discord.Colour.blue())
        embed.set_author(name='Help:')
        embed.add_field(name='Bot Developers:',
                        value='Bobo#6885 <@813330702712045590>, Sean#4318 <@202947434236739584>', inline=False)
        file = discord.File("./data/ArcturusMengsk_SC2_Cine1.jpg")
        embed.set_thumbnail(url='attachment://ArcturusMengsk_SC2_Cine1.jpg')
        embed.add_field(name='.add or .a', value="Add yourself to be ranked", inline=True)
        embed.add_field(name='.match or .m', value="Add a new match to influence rating", inline=True)
        embed.add_field(name='.stats or .s', value="Check the ratings of a member", inline=True)
        embed.add_field(name='.editname or .en', value="Edit your name (for typos and clan changes)", inline=True)
        embed.add_field(name='.help or .h', value='Shows this', inline=True)
        embed.add_field(name='.ping or .p', value='Bot latency (in ms)', inline=True)
        embed.add_field(name='.uptime or .up', value='Display how long bot has been running for', inline=True)
        embed.add_field(name='.block or .bl', value="*Requires \'Bot Admin\' role* Blocks a user from inputting "
                                                    "commands", inline=True)
        embed.add_field(name='.unblock or .u', value="*Requires \'Bot Admin\' role* Un-blocks a user from inputting "
                                                     "commands", inline=True)
        embed.add_field(name='.delete or .d', value='*Requires \'Bot Admin\' role* Removes an erroneously entered name',
                        inline=True)
        embed.add_field(name='.editelo or .ee', value='*Requires \'Bot Admin\' role* Edits the Elo of a player',
                        inline=True)
        embed.add_field(name='.editsigma or .es', value='*Requires \'Bot Admin\' role* Edits the Sigma of a player',
                        inline=True)
        embed.add_field(name='.backupratings or .br', value="*Requires \'Bot Admin\' role* Backup Current Elo ratings",
                        inline=True)
        embed.add_field(name='.restoreratings or .rr', value='*Requires \'Bot Admin\' role* Restore Elo from backup '
                                                             'date', inline=True)
        embed.add_field(name='.listmembers or .lm', value='*Requires \'Bot Admin\' role* List all members being ranked',
                        inline=True)
        embed.add_field(name='.filecontents or .fc', value='*Requires \'Bot Admin\' role* Displays contents of Elo '
                                                           'files', inline=True)
        embed.set_footer(icon_url=ctx.author.avatar_url,
                         text='Requested by {} on {}'.format(ctx.author, datetime.date.today().strftime("%m-%d-%Y")))
        await ctx.author.send(file=file, embed=embed)


    @client.event
    async def on_message(message):
        with open(blocked_ids_path) as fo:
            data = fo.readlines()
            if len(data) > 0:
                for line in data:
                    if str(message.author.id) in line:
                        await message.delete()
                        return
            else:
                pass

        if message.author.name == name_of_bot:
            return

        if message.content.startswith(prefix):
            await client.process_commands(message)
            # if message.content.startswith('.m') or message.content.startswith('.match'):
            #     await refresh_leaderboard()
        else:
            return


    @client.event
    async def on_command_error(ctx, error):
        await ctx.send(f'Error. Try .help ({error})', delete_after=15)


    print('Bot is active')
    client.run(token)
