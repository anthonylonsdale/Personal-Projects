import discord
from discord.ext import commands
from discord.ext import tasks
import os
import sys
import datetime
import glob
import re
import asyncio
import logging
import traceback
import aiosqlite
from urllib.request import pathname2url
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bot.config import *
import bot.glicko
from bot.sql_queries import *


def days_hours_minutes(td):
    return td.days, td.seconds // 3600, (td.seconds // 60) % 60


async def check_admin(guild_id):
    async with aiosqlite.connect(guild_settings_path) as db:
        async with db.execute_fetchall("select bot_admin_id from guilds where guild_id = ?", (guild_id,)) as c:
            try:
                bot_admin_id = c[0][0]
                return bot_admin_id
            except IndexError:
                return None


async def file_init():
    for path in path_list:
        if not os.path.isfile(path):
            if path == guild_settings_path:
                await initialize_guild_settings()
                continue
            db = await aiosqlite.connect(path)
            await db.close()
    return


if __name__ == '__main__':
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='./data/discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    asyncio.run(file_init())
    prefix = '.'
    asyncio.set_event_loop(asyncio.new_event_loop())
    client = commands.Bot(command_prefix=prefix)
    client.remove_command('help')
    start_time = datetime.datetime.now().astimezone()

    load_dotenv(env_path)
    # token = os.getenv("PRODUCTION_BOT_TOKEN")
    token = os.getenv("TEST_BOT_TOKEN")


    @client.command("ping", aliases=['p'])
    async def ping(ctx):
        await ctx.send(f'Bot Response Time: {round(client.latency * 1000)}ms ', delete_after=delete_delay)


    @client.command('resetsettings')
    @commands.has_permissions(administrator=True)
    async def reset(ctx):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        await ctx.send("Are you sure you want to delete the settings for this guild? (y/n)", delete_after=response_time)
        try:
            yn = await client.wait_for("message", check=check, timeout=response_time)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return

        if 'y' == yn.content:
            async with aiosqlite.connect(guild_settings_path) as db:
                await db.execute("delete from guilds where guild_id = ?", (ctx.guild.id,))
                await db.commit()
            await ctx.send("Bot settings for this guild have been wiped!", delete_after=delete_delay)
            await setup(ctx)
        else:
            await ctx.send("\'y\' was not detected, no settings have been changed")
            return


    @client.command("setup")
    @commands.has_permissions(administrator=True)
    async def setup(ctx):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if await check_admin(ctx.guild.id) is not None:
            await ctx.send("Settings have already been set up for this server")
            return

        await ctx.send("Do you already have two channels to designate as the bot-commands channel and leaderboard "
                       "channel? (y/n)", delete_after=delete_delay)
        try:
            yn = await client.wait_for("message", check=check, timeout=180)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return

        if 'y' == yn.content:
            await ctx.send("please supply the channel id of the bot channel", delete_after=delete_delay)
            try:
                bot = await client.wait_for("message", check=check, timeout=180)
                await client.fetch_channel(int(bot.content))
                bot_channel_id = bot.content
            except asyncio.TimeoutError or Exception:
                await ctx.send("You either supplied an invalid channel or took too long", delete_after=delete_delay)
                return

            await ctx.send("please supply the channel id of the leaderboard channel", delete_after=delete_delay)
            try:
                board = await client.wait_for("message", check=check, timeout=180)
                await client.fetch_channel(int(board.content))
                leaderboard_channel_id = int(board.content)
            except asyncio.TimeoutError or Exception as e:
                await ctx.send("You either supplied an invalid channel or took too long", delete_after=delete_delay)
                return
        elif 'n' == yn.content:
            await ctx.send("Input hyphenated bot channel and leaderboard channel names separated by a space, in that "
                           "order. Example: ratings-bot-channel leaderboard-channel:", delete_after=delete_delay)
            try:
                channel_names = await client.wait_for("message", check=check, timeout=response_time)
                ch_names = channel_names.content.split(' ')
                if len(ch_names) > 2:
                    raise Exception("Too many arguments provided")
                bot_channel_name = ch_names[0]
                leaderboard_channel_name = ch_names[1]
                bot_channel = await ctx.message.guild.create_text_channel(str(bot_channel_name))
                leaderboard_channel = await ctx.message.guild.create_text_channel(leaderboard_channel_name)
                bot_channel_id = bot_channel.id
                leaderboard_channel_id = leaderboard_channel.id
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            except Exception as e:
                await ctx.send(f"You did not follow the provided format! {e}", delete_after=delete_delay)
                return

        else:
            await ctx.send("You supplied an invalid response", delete_after=delete_delay)
            return

        await ctx.send("Do you already have a role to set as a Bot Administrator (y/n)?", delete_after=delete_delay)
        try:
            ynr = await client.wait_for("message", check=check, timeout=response_time)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return

        if 'y' == ynr.content:
            await ctx.send("Input role ID to serve as Bot Administrator", delete_after=delete_delay)
            try:
                r_id = await client.wait_for("message", check=check, timeout=response_time)
                discord.utils.get(ctx.guild.roles, id=int(r_id.content))
                bot_admin_id = int(r_id.content)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            except Exception:
                await ctx.send("An error has occurred", delete_after=delete_delay)
                return
        elif 'n' == ynr.content:
            role = await ctx.message.guild.create_role(name="Bot Admin")
            bot_admin_id = role.id
            user = ctx.message.author
            await user.add_roles(role)
            await ctx.send("The \"Bot Admin\" Role has been created, feel free to give the role to other members but "
                           "please do not delete it as the id is hardcoded in the database.", delete_after=delete_delay)
        else:
            await ctx.send("You supplied an invalid response", delete_after=delete_delay)
            return

        await ctx.send("Input starting elo and starting sigma and global ratings floor, separated by spaces "
                       "Example: 1200 150 900:", delete_after=delete_delay)
        try:
            ratings_set = await client.wait_for("message", check=check, timeout=180)
            ratings_settings = ratings_set.content.split(' ')
            if len(ratings_settings) > 3:
                raise Exception("Too many arguments provided")
            starting_elo = ratings_settings[0]
            starting_sigma = ratings_settings[1]
            global_elo_floor = ratings_settings[2]
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return
        except Exception as e:
            await ctx.send(f"You did not follow the provided format! {e}", delete_after=delete_delay)
            return

        async with aiosqlite.connect(guild_settings_path) as db:
            await db.execute("insert into guilds values (?, ?, ?, ?, ?, ?, ?)",
                             (ctx.guild.id, bot_channel_id, leaderboard_channel_id, bot_admin_id, starting_elo,
                              starting_sigma, global_elo_floor,))
            await db.commit()

        init_tables = createGuildSettings(guild_id=ctx.guild.id)
        await init_tables.initialize_tables()
        await ctx.send('''Settings have been initialized for this server, GLHF!\n
                       A few things to keep in mind as you get started using the bot and its features:\n
                       1) The bot only accepts commands invoked in the bot channel (to mitigate bot spam issues)\n
                       2) If you end up needing to reuse this command (in case of accidental channel/role deletion),
                       invoke the .reset_settings command which is restricted to users with adminstrator permissions
                       (and can also be read from any channel).\n
                       3) The leaderboard will automatically update itself upon entry of a command, if it is deleted 
                       it will automatically recreate itself\n
                       4) The Bot Admin role is given elevated privileges which can potentially be abused, assign it
                       to others with caution.''', delete_after=120)


    @client.command("block", aliases=['b', 'ban'])
    async def block_id(ctx, id_to_block=None):
        bot_admin_id = await check_admin(ctx.guild.id)
        role = ctx.guild.get_role(bot_admin_id)
        if role not in ctx.author.roles:
            await ctx.send("You do not have the proper permissions to use this command", delete_after=delete_delay)
            return

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if id_to_block is None:
            await ctx.send("What user do you want to prohibit? Format: @username or id", delete_after=delete_delay)
            try:
                blockid = await client.wait_for("message", check=check, timeout=response_time)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            id_to_block = blockid.content

        try:
            banned_id = int(id_to_block)
            user = await client.fetch_user(banned_id)
        except ValueError:
            try:
                banned_id = int(id_to_block[3:-1])
                user = await client.fetch_user(banned_id)
            except ValueError:
                await ctx.send("Invalid input detected!", delete_after=delete_delay)
                return

        name = user.name
        async with aiosqlite.connect(blocked_ids_path) as db:
            await db.execute(f"insert or ignore into bans_{ctx.guild.id} (discord_id, discord_name) values (?, ?)",
                             (banned_id, name,))
            await db.commit()
        await ctx.send(f'<@{banned_id}> You have been banned from using {client.user.name}', delete_after=delete_delay)


    @client.command("unblock", aliases=['ub', 'unban'])
    async def unblock_id(ctx, id_to_unblock=None):
        bot_admin_id = await check_admin(ctx.guild.id)
        role = ctx.guild.get_role(bot_admin_id)
        if role not in ctx.author.roles:
            await ctx.send("You do not have the proper permissions to use this command", delete_after=delete_delay)
            return

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if id_to_unblock is None:
            await ctx.send("What user do you want to allow commands from? Format: @username", delete_after=delete_delay)

            try:
                unblockid = await client.wait_for("message", check=check, timeout=response_time)
                id_to_unblock = unblockid.content
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return

        try:
            unbanned_id = int(id_to_unblock)
            await client.fetch_user(unbanned_id)
        except ValueError:
            try:
                unbanned_id = int(id_to_unblock[3:-1])
                await client.fetch_user(unbanned_id)
            except ValueError:
                await ctx.send("Invalid input detected!", delete_after=delete_delay)
                return

        async with aiosqlite.connect(blocked_ids_path) as db:
            await db.execute(f"delete from bans_{ctx.guild.id} where discord_id = ?", (unbanned_id,))
            await db.commit()
        await ctx.send(f"<@{unbanned_id}> You have been unbanned from using {client.user.name}",
                       delete_after=delete_delay)


    class Backup(commands.Cog):
        def __init__(self):
            self.backup.start()

        @tasks.loop(hours=12)
        async def backup(self):
            todays_date = datetime.date.today().strftime("%m-%d-%Y")
            for file in paths:
                source = await aiosqlite.connect(f'./data/{file}.db')
                destination = await aiosqlite.connect(f'./data/{file}_backup_{todays_date}.db')
                await source.backup(destination)
                await source.close()

            # prunes old backups
            backup_files = glob.glob('./data/*_backup_*.db')
            for file in backup_files:
                re_match = re.search(r'\d{2}-\d{2}-\d{4}', file)
                date = datetime.datetime.strptime(re_match.group(), '%m-%d-%Y').date()
                date_cutoff = datetime.date.today() - datetime.timedelta(days=days_of_backup_file_storage)
                if date_cutoff > date:
                    pruned_backup = str('./') + str(file)
                    os.remove(pruned_backup)
            logger.debug("Backup of all files made")

            ids = []
            for guild in client.guilds:
                ids.append(guild.id)

            async with aiosqlite.connect(guild_settings_path) as db:
                async with db.execute_fetchall("select guild_id from guilds") as cursor:
                    for row in cursor:
                        if row[0] not in ids:
                            await db.execute("delete from guilds where guild_id = ?", (row[0],))
                            await db.commit()
                            drop_guild_tables = dropGuildSettings(row[0])
                            await drop_guild_tables.drop_tables()


    @client.command("restore", aliases=['r'])
    async def restore(ctx):
        backup_files = glob.glob('./data/*_backup_*.db')
        if len(backup_files) == 0:
            await ctx.send("No backups to restore from", delete_after=delete_delay)
            return

        backup_dates = []
        for f in backup_files:
            re_match = re.search(r'\d{2}-\d{2}-\d{4}', f)
            date = re_match.group()
            if date not in backup_dates:
                backup_dates.append(date)

        await ctx.send(f"Input date to restore table from (format mo-dy-year).\n"
                       f"Available dates to restore from: {backup_dates}", delete_after=delete_delay)

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        tables_to_select = []
        try:
            date_to_restore = await client.wait_for("message", check=check, timeout=response_time)
            for index, path in enumerate(paths):
                db = f'./data/{path}_backup_{date_to_restore.content}.db'
                dburi = f'file:{pathname2url(db)}?mode=rw'
                async with aiosqlite.connect(dburi, uri=True) as db:
                    table_name = f'{tables[index]}_{ctx.guild.id}'
                    result = await db.execute_fetchall(f"select name from sqlite_master where type=\'table\'")
                    for element in result:
                        if table_name == element[0]:
                            tables_to_select.append(table_name)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return
        except Exception as e:
            await ctx.send("An error has occurred with the restore function!", delete_after=delete_delay)
            return

        if len(tables_to_select) > 0:
            available_tables = ''
            for table in tables_to_select:
                available_tables += table.replace(f"_{ctx.guild.id}", '') + '\n'
            await ctx.send(f"Available tables:\n{available_tables}Input table to restore from (without ID):",
                           delete_after=delete_delay)
        else:
            await ctx.send(f"No tables found!", delete_after=delete_delay)
            return

        try:
            table_selection = await client.wait_for("message", check=check, timeout=response_time)
            selected_table = table_selection.content
            if str(selected_table + f'_{ctx.guild.id}') not in tables_to_select:
                raise Exception("Table not found")
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return
        except Exception as e:
            await ctx.send("Table wasn't found!", delete_after=delete_delay)
            return

        for index, path in enumerate(tables):
            if selected_table == path:
                file = paths[index]
                new_file = f'./data/{file}.db'
                file_path = f'./data/{file}_backup_{date_to_restore.content}.db'
                async with aiosqlite.connect(new_file) as db:
                    await db.execute(f"delete from {selected_table}_{ctx.guild.id};")
                    async with aiosqlite.connect(file_path) as backupdb:
                        async for line in backupdb.iterdump():
                            if "CREATE TABLE" in line and str(ctx.guild.id) in line:
                                await db.execute(f"drop table if exists {selected_table}_{ctx.guild.id}")
                                await db.execute(line)
                                await db.commit()
                            elif "INSERT INTO" in line and str(ctx.guild.id) in line:
                                await db.execute(line)
                                await db.commit()


    @client.command("listmembers", aliases=['lm'])
    async def list_members(ctx):
        bot_admin_id = await check_admin(ctx.guild.id)
        role = ctx.guild.get_role(bot_admin_id)
        if role not in ctx.author.roles:
            await ctx.send("You do not have the proper permissions to use this command", delete_after=delete_delay)
            return

        members = ''
        async with aiosqlite.connect(ratings_master_path) as db:
            async with db.execute_fetchall(f"select clan_id, player_name from players_{ctx.guild.id}") as c:
                for row in c:
                    if row[0] == '<>':
                        members += f'{row[1]}\n'
                        continue
                    members += f'{row[0]}{row[1]}\n'
                await ctx.send(f"There are {len(c)} ranked members:\n{members}", delete_after=delete_delay)


    @client.command("match", aliases=['m'])
    async def match(ctx, personone: str = None, persononewins: int = None, persontwo: str = None,
                    persontwowins: int = None):
        emoji_object = rankEmoji(client=client)
        rank_emojis = emoji_object.rank_emoji()
        guild_id = ctx.guild.id

        async with aiosqlite.connect(guild_settings_path) as db:
            async with db.execute("select global_elo_floor, bot_admin_id from guilds where guild_id = ?",
                                  (guild_id,)) as cur:
                result = await cur.fetchone()
                global_elo_floor = result[0]
                bot_admin_id = result[1]

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if personone is None or persononewins is None or persontwo is None or persontwowins is None:
            await ctx.send(f"Input new match to influence rating, format is Name1 (wins) Name2 (wins), example: "
                           f"<BestClan>AlphaBeta 5 <WorstClan>OmegaLambda 5. Global Elo floor is {global_elo_floor}. "
                           f"There is no Elo ceiling.", delete_after=delete_delay)

            try:
                match_msg = await client.wait_for("message", check=check, timeout=response_time)
                match_array = match_msg.content.split()
                personone = match_array[0]
                persononewins = int(match_array[1])
                persontwo = match_array[2]
                persontwowins = int(match_array[3])
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            except Exception as e:
                await ctx.send("You provided invalid arguments, there should be 4 distinct arguments, player1, the "
                               "number of times that player1 has won, player2 and the number of times player2 won.",
                               delete_after=delete_delay)

        if persononewins > maxwinsallowed or persontwowins > maxwinsallowed:
            await ctx.send(f'You have exceeded the number of wins allowed in a single session ({maxwinsallowed})',
                           delete_after=delete_delay)
            return

        async with aiosqlite.connect(ratings_master_path) as db:
            async with db.execute(f"select * from players_{guild_id} where player_name like ?",
                                  ('%' + personone + '%',)) as cur:
                p1_info = await cur.fetchall()

        name_found_bool = False
        if p1_info is None or len(p1_info) == 0:
            await ctx.send(f'<@{ctx.author.id}> {personone} was not detected in the database!',
                           delete_after=delete_delay)
            return
        elif len(p1_info) == 1:
            p1_info = p1_info[0]
        else:
            result = ''
            for row in p1_info:
                result += row[3] + row[4] + '\n'
            await ctx.send(f'Multiple names found:\n{result}Specify which player you want to show:',
                           delete_after=response_time)
            try:
                name = await client.wait_for("message", check=check, timeout=response_time)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            search = name.content
            for row in p1_info:
                if search == str(row[4]):
                    p1_info = row
                    name_found_bool = True
                    break
            # This means we failed to narrow down the search
            if not name_found_bool:
                await ctx.send("Name was not found!", delete_after=delete_delay)
                return

        async with aiosqlite.connect(ratings_master_path) as db:
            async with db.execute(f"select * from players_{guild_id} where player_name like ?",
                                  ('%' + persontwo + '%',)) as cur:
                p2_info = await cur.fetchall()

        name_found_bool = False
        if p2_info == p1_info:
            await ctx.send("You cannot input a match against yourself", delete_after=delete_delay)
            return

        if p2_info is None or len(p2_info) == 0:
            await ctx.send(f'<@{ctx.author.id}> {persontwo} was not detected in the database!',
                           delete_after=delete_delay)
            return
        elif len(p2_info) == 1:
            p2_info = p2_info[0]
            pass
        else:
            result = ''
            for row in p2_info:
                result += row[3] + row[4] + '\n'

            await ctx.send(f'Multiple names found:\n{result}Specify which player you want to show:',
                           delete_after=response_time)
            try:
                name = await client.wait_for("message", check=check, timeout=response_time)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            search = name.content
            for row in p2_info:
                if search == str(row[4]):
                    p2_info = row
                    name_found_bool = True
                    break
            # This means we failed to narrow down the search
            if not name_found_bool:
                await ctx.send("Name was not found!", delete_after=delete_delay)
                return

        personone = p1_info[4]
        persontwo = p2_info[4]

        async with aiosqlite.connect(ratings_path) as db:
            cur = await db.execute(f"select rating, sigma from ratings_{guild_id} where discord_id = ?", (p1_info[0],))
            p1_r_s_tuple = await cur.fetchone()
            p1_old_rating = p1_r_s_tuple[0]
            p1_old_sigma = p1_r_s_tuple[1]

            cur2 = await db.execute(f"select rating, sigma from ratings_{guild_id} where discord_id = ?", (p2_info[0],))
            p2_r_s_tuple = await cur2.fetchone()
            p2_old_rating = p2_r_s_tuple[0]
            p2_old_sigma = p2_r_s_tuple[1]

        playeroneobject = bot.glicko.Player(rating=p1_old_rating, rd=p1_old_sigma)
        playertwoobject = bot.glicko.Player(rating=p2_old_rating, rd=p2_old_sigma)

        for i in range(persononewins):
            playeroneobject.update_player([p2_old_rating], [p2_old_sigma], [1])
            playertwoobject.update_player([p1_old_rating], [p1_old_sigma], [0])
        for i in range(persontwowins):
            playertwoobject.update_player([p2_old_rating], [p2_old_sigma], [1])
            playeroneobject.update_player([p1_old_rating], [p1_old_sigma], [0])

        p1_new_rating = round(playeroneobject.get_rating(), 2)
        if p1_new_rating < global_elo_floor:
            p1_new_rating = global_elo_floor
        p1_new_sigma = round(playeroneobject.get_rd(), 2)

        p2_new_rating = round(playertwoobject.get_rating(), 2)
        if p2_new_rating < global_elo_floor:
            p2_new_rating = global_elo_floor
        p2_new_sigma = round(playertwoobject.get_rd(), 2)

        author = str(ctx.author)
        author_id = ctx.author.id
        role = ctx.guild.get_role(bot_admin_id)

        if ctx.author.id == p1_info[0]:
            await ctx.send(f'<@{p2_info[0]}> A match involving you was just added. The match results have been sent '
                           f'to you for your perusal', delete_after=delete_delay)
            user = await client.fetch_user(p2_info[0])
            await user.send(f'<@{p2_info[0]}>, A match was added with a score of {persononewins} wins for '
                            f'{personone} and {persontwowins} wins for {persontwo}, if this result is incorrect, please'
                            f' contact the Bot Administrators.\nOld Elo: {p2_old_rating}   Old Sigma: {p2_old_sigma}.'
                            f'\nNew Elo: {p2_new_rating}   New Sigma: {p2_new_sigma}.')

        elif ctx.author.id == p2_info[0]:
            await ctx.send(f'<@{p1_info[0]}> A match involving you was just added. The match results have been sent '
                           f'to you for your perusal', delete_after=delete_delay)
            user = await client.fetch_user(p1_info[0])
            await user.send(f'<@{p1_info[0]}>, A match was added with a score of {persononewins} wins for '
                            f'{personone} and {persontwowins} wins for {persontwo}, if this result is incorrect, please'
                            f' contact the Bot Administrators.\nOld Elo: {p2_old_rating}   Old Sigma: {p2_old_sigma}.'
                            f'\nNew Elo: {p2_new_rating}   New Sigma: {p2_new_sigma}.')
        else:
            if role in ctx.author.roles:
                await ctx.send(f'<@{p1_info[0]}> <@{p2_info[0]}> A match involving you was just added. The match '
                               f'results have been sent to you for your perusal', delete_after=delete_delay)
            else:
                await ctx.send(f"<@{ctx.author.id}>You cannot input a match concerning two other people!",
                               delete_after=delete_delay)
                return

        async with aiosqlite.connect(ratings_path) as db:
            await db.execute(f"update ratings_{guild_id} set rating = ?, sigma = ?, wins = wins + ?, losses = "
                             "losses + ?, last_updated = ? where discord_id = ?;",
                             (p1_new_rating, p1_new_sigma, persononewins, persontwowins,
                              datetime.datetime.now().astimezone(), p1_info[0],))
            await db.commit()
            await db.execute(f"update ratings_{guild_id} set rating = ?, sigma = ?, wins = wins + ?, losses = "
                             "losses + ?, last_updated = ? where discord_id = ?;",
                             (p2_new_rating, p2_new_sigma, persontwowins, persononewins,
                              datetime.datetime.now().astimezone(), p2_info[0],))
            await db.commit()

        async with aiosqlite.connect(matches_path) as db:
            await db.execute(f"insert into matches_{guild_id} (player_a, player_a_score, player_a_old_elo, "
                             f"player_a_old_sigma, player_a_new_elo, player_a_new_sigma, player_b, player_b_score, "
                             f"player_b_old_elo, player_b_old_sigma, player_b_new_elo, player_b_new_sigma, "
                             f"inputted_user_name, inputted_user_id) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (personone, persononewins, p1_old_rating, p1_old_sigma, p1_new_rating, p1_new_sigma,
                              persontwo, persontwowins, p2_old_rating, p2_old_sigma, p2_new_rating, p2_new_sigma,
                              author, author_id,))
            await db.commit()

        rankp1 = None
        emoji1 = None
        rankp2 = None
        emoji2 = None
        for k in ranks:
            if p1_new_rating >= ranks[k]:
                rankp1 = k
                emoji1 = rank_emojis[k]
            if p2_new_rating >= ranks[k]:
                rankp2 = k
                emoji2 = rank_emojis[k]

        if p1_new_rating < p1_old_rating:
            color1 = f'```diff\n- {p1_new_rating} {rankp1}\nnew Sigma {p1_new_sigma} \n```'
        else:
            color1 = f'```diff\n+ {p1_new_rating} {rankp1}\nnew Sigma {p1_new_sigma} \n```'

        if p2_new_rating < p2_old_rating:
            color2 = f'```diff\n- {p2_new_rating} {rankp2}\nnew Sigma {p2_new_sigma} \n```'
        else:
            color2 = f'```diff\n+ {p2_new_rating} {rankp2}\nnew Sigma {p2_new_sigma} \n```'

        await ctx.send(f"Updated Ratings (automatically saved to file):\n\n{personone}\'s Rank: {emoji1} {color1}\n"
                       f"{persontwo}\'s Rank: {emoji2} {color2}", delete_after=delete_delay)


    @client.command("files", aliases=['f'])
    async def file_contents(ctx):
        bot_admin_id = await check_admin(ctx.guild.id)
        role = ctx.guild.get_role(bot_admin_id)
        if role not in ctx.author.roles:
            await ctx.send("You do not have the proper permissions to use this command", delete_after=delete_delay)
            return

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        guild_id = ctx.guild.id
        user = await client.fetch_user(ctx.author.id)

        for i in range(len(paths)):
            embed = discord.Embed(title=f"Contents of {paths[i]}")
            async with aiosqlite.connect(f"./data/{paths[i]}.db") as db:
                if paths[i] == 'matches':
                    for row in await db.execute_fetchall(f"select * from {tables[i]}_{guild_id}"):
                        embed.add_field(name=f"Row ID: {row[0]}", value=str(row), inline=False)
                elif paths[i] == 'guild_settings':
                    for row in await db.execute_fetchall("select rowid, * from guilds where guild_id = ?", (guild_id,)):
                        embed.add_field(name=f"Row ID: {row[0]}", value=str(row), inline=False)
                else:
                    for row in await db.execute_fetchall(f"select rowid, * from {tables[i]}_{guild_id}"):
                        embed.add_field(name=f"Row ID: {row[0]}", value=str(row), inline=False)
            await user.send(embed=embed, delete_after=delete_delay)

        await ctx.send("Input the file and line that you want to delete:\nFormat: file_name  line-#)",
                       delete_after=delete_delay)

        try:
            msg = await client.wait_for("message", check=check, timeout=response_time)
            if msg.content == 'stop':
                return
            if str(msg.content).startswith('.'):
                return
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return

        split_msg = msg.content.split(' ')
        file_name = split_msg[0]
        row_id = split_msg[1]

        if 'matches' in file_name:
            async with aiosqlite.connect(matches_path) as db:
                await db.execute(f"delete from matches_{guild_id} where rowid = ?;", (row_id,))
                await db.commit()
        elif 'ratings_master' in file_name:
            async with aiosqlite.connect(ratings_master_path) as db:
                await db.execute(f"delete from players_{guild_id} where rowid = ?;", (row_id,))
                await db.commit()
        elif 'ratings' in file_name:
            async with aiosqlite.connect(ratings_path) as db:
                await db.execute(f"delete from ratings_{guild_id} where rowid = ?;", (row_id,))
                await db.commit()
        elif 'banned' in file_name:
            async with aiosqlite.connect(blocked_ids_path) as db:
                await db.execute(f"delete from bans_{guild_id} where rowid = ?;", (row_id,))
                await db.commit()
        elif 'settings' in file_name:
            await reset(ctx)
            return
        await ctx.send(f"Line {row_id} in File {file_name} has been removed", delete_after=delete_delay)


    @client.command("editrating", aliases=['er'])
    async def edit_elo(ctx, name: str = None, newelo: str = None):
        bot_admin_id = await check_admin(ctx.guild.id)
        role = ctx.guild.get_role(bot_admin_id)
        if role not in ctx.author.roles:
            await ctx.send("You do not have the proper permissions to use this command", delete_after=delete_delay)
            return

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if name is None or newelo is None:
            await ctx.send("Who\'s elo do you want to change? format: user newelo", delete_after=delete_delay)

            try:
                msg = await client.wait_for("message", check=check, timeout=response_time)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            name = msg.content.split()[0]
            newelo = msg.content.split()[1]

        async with aiosqlite.connect(ratings_path) as db:
            await db.execute(f"update ratings_{ctx.guild.id} set rating = ? where player_name = ?;", (newelo, name,))
            await db.commit()
            await ctx.send(f"{name}\'s elo has been changed to {newelo}")


    @client.command("editsigma", aliases=['es'])
    async def edit_sigma(ctx, name: str = None, newsigma: str = None):
        bot_admin_id = await check_admin(ctx.guild.id)
        role = ctx.guild.get_role(bot_admin_id)
        if role not in ctx.author.roles:
            await ctx.send("You do not have the proper permissions to use this command", delete_after=delete_delay)
            return

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if name is None or newsigma is None:
            await ctx.send("Who\'s sigma do you want to change? format: user newsigma", delete_after=delete_delay)

            try:
                msg = await client.wait_for("message", check=check, timeout=response_time)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return

            name = msg.content.split()[0]
            newsigma = msg.content.split()[1]

        # No ID checks needed because this is an admin only command
        async with aiosqlite.connect(ratings_path) as db:
            await db.execute(f"update ratings_{ctx.guild.id} set sigma = ? where player_name = ?;", (newsigma, name,))
            await db.commit()
            await ctx.send(f'{name}\'s sigma has been changed to {newsigma}')


    @client.command('editname', aliases=['en'])
    async def edit_member(ctx, name: str = None):
        guild_id = ctx.guild.id
        bot_admin_id = await check_admin(ctx.guild.id)
        role = ctx.guild.get_role(bot_admin_id)

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if name is None:
            await ctx.send("Input the name to be edited (Note that you may only change the name that is associated with"
                           " your unique Discord tag)", delete_after=delete_delay)

            try:
                old_name = await client.wait_for("message", check=check, timeout=response_time)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            name = old_name.content

        try:
            await ctx.send("Enter new name:", delete_after=delete_delay)
            new_name = await client.wait_for("message", check=check, timeout=response_time)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return

        author_id = ctx.author.id
        async with aiosqlite.connect(ratings_master_path) as db:
            async with db.execute(f"select discord_id from players_{guild_id} where player_name = ?",
                                  (new_name.content,)) as cur:
                search = await cur.fetchone()
                if search is not None:
                    await ctx.send(f"Name {new_name} already exists!", delete_after=delete_delay)
                    return

            async with db.execute(f"select discord_id from players_{guild_id} where player_name = ?", (name,)) as cur:
                search = await cur.fetchone()
                if search is None:
                    await ctx.send(f"Name {name} does not exist!", delete_after=delete_delay)
                    return

            if role in ctx.author.roles:
                author_id = search[0]
            elif author_id != search[0]:
                await ctx.send("Only Bot admins may change other member's names!", delete_after=delete_delay)
                return

            await db.execute(f"update players_{guild_id} set player_name = ? where discord_id = ?;",
                             (new_name.content, author_id,))
            await db.commit()

        async with aiosqlite.connect(ratings_path) as db:
            await db.execute(f"update ratings_{guild_id} set player_name = ? where discord_id = ?;",
                             (new_name.content, author_id,))
            await db.commit()
            await ctx.send(f"<@{author_id}> Your name was changed from {name} to {new_name.content}")


    @client.command('stats', aliases=['s'])
    async def member_stats(ctx, name: str = None):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if name is None:
            await ctx.send(f"Who\'s stats do you want to check?", delete_after=delete_delay)
            try:
                msg = await client.wait_for("message", check=check, timeout=response_time)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            name = msg.content

        guild_id = ctx.guild.id
        async with aiosqlite.connect(ratings_master_path) as db:
            async with db.execute(f"select discord_id, clan_id, player_name from players_{guild_id} where "
                                  f"player_name like ?", ('%' + name + '%',)) as cur:
                search_results = await cur.fetchall()

                discord_id = None
                if len(search_results) == 0:
                    await ctx.send(f'<@{ctx.author.id}> {name} has not been added to the database!\n',
                                   delete_after=delete_delay)
                    return
                elif len(search_results) > 1:
                    result = ''
                    for row in search_results:
                        result += row[1] + row[2] + '\n'
                    await ctx.send(f'Multiple names found:\n{result}Specify which player you want to show:',
                                   delete_after=response_time)
                    try:
                        name = await client.wait_for("message", check=check, timeout=response_time)
                    except asyncio.TimeoutError:
                        await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                        return
                    name = name.content
                    for row in search_results:
                        if name == row[2]:
                            discord_id = int(row[0])
                    if discord_id is None:
                        await ctx.send("Name was not found!", delete_after=delete_delay)
                        return
                else:
                    name = search_results[0][2]
                    discord_id = search_results[0][0]

        async with aiosqlite.connect(ratings_path) as db:
            async with db.execute("select clan_id, player_name, rating, sigma, wins, losses, last_updated from ratings_"
                                  f"{guild_id} where player_name = ? and discord_id = ?", (name, discord_id,)) as cur:
                r = await cur.fetchone()
                tslm = datetime.datetime.now().astimezone() - datetime.datetime.fromisoformat(r[6])
                t = days_hours_minutes(tslm)
                wr = round((r[4] / (r[4] + r[5])) * 100, 2)
                await ctx.send(f"Stats for {r[0]}{r[1]}:\nRating: {r[2]}\nSigma: {r[3]}\nWins: {r[4]}\nLosses: {r[5]}"
                               f"\nWinrate: {wr}%\nTime since last match: {t[0]} days, {t[1]} hours and {t[2]} minutes",
                               delete_after=delete_delay)


    @client.command("add", aliases=['a'])
    async def add_member(ctx, name: str = None, d_id=None):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        guild_id = ctx.guild.id

        async with aiosqlite.connect(guild_settings_path) as db:
            cur = await db.execute("select bot_admin_id, starting_elo, starting_sigma from guilds where guild_id = ?",
                                   (guild_id,))
            starting_settings = await cur.fetchone()
            bot_admin_id = starting_settings[0]
            starting_elo = starting_settings[1]
            starting_sigma = starting_settings[2]
            role = ctx.guild.get_role(bot_admin_id)

        if name is None:
            await ctx.send(f"Input new member for competitive ranking, Format is <clan>name, i.e. <BestClan>Example.\n"
                           f"Warning, your unique Discord tag will be associated with your inputted name, so do not "
                           f"input anybody except yourself. If you make a typo, please use the .editname command.\n"
                           f"Elo starts at {starting_elo} and Sigma starts at {starting_sigma} for all players.")
            try:
                msg = await client.wait_for("message", check=check, timeout=response_time)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            name = msg.content
        else:
            print(name)
            if '@' in name:
                pass


        try:
            clan = re.findall('[^>]+>', name)[0]
            name = name.replace(clan, '')
        except IndexError:
            clan = '<>'

        author_id = ctx.author.id
        # if admin, allow the ability to add others, else, just sets id to author
        if d_id is not None:
            if role in ctx.author.roles:
                try:
                    author_id = int(d_id)
                except Exception as e:
                    try:
                        author_id = d_id[3:-1]
                    except Exception as er:
                        await ctx.send("ID is invalid type!", delete_after=delete_delay)
                        return

        user = await client.fetch_user(author_id)
        async with aiosqlite.connect(ratings_master_path) as db:
            async with db.execute(f"select 1 from players_{guild_id} where discord_id = ? limit 1", (author_id,)) as c:
                if await c.fetchone() is None:
                    await c.execute(f"insert into players_{guild_id} (discord_id, discord_name, clan_id, player_name) "
                                    f"values (?, ?, ?, ?)", (author_id, str(user), clan, name,))
                    await db.commit()
                else:
                    await ctx.send(f'<@{ctx.author.id}> This Discord ID was already detected in the database! If you '
                                   f'need to edit your name, use the .editname command', delete_after=delete_delay)
                    return

        async with aiosqlite.connect(ratings_path) as db:
            await db.execute(f"insert into ratings_{guild_id} (discord_id, discord_name, clan_id, player_name, rating, "
                             f"sigma, wins, losses) values (?, ?, ?, ?, ?, ?, ?, ?)",
                             (author_id, str(user), clan, name, starting_elo, starting_sigma, 0, 0))
            await db.commit()
            await ctx.send(f'<@{author_id}> was successfully registered in the database, GLHF!',
                           delete_after=delete_delay)


    @client.command('delete', aliases=['d'])
    async def delete_member(ctx, name: str = None):
        guild_id = ctx.guild.id
        bot_admin_id = await check_admin(ctx.guild.id)
        role = ctx.guild.get_role(bot_admin_id)
        if role not in ctx.author.roles:
            await ctx.send("You do not have the proper permissions to use this command", delete_after=delete_delay)
            return

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if name is None:
            await ctx.send("Who do you want to remove from the database?", delete_after=delete_delay)
            try:
                msg = await client.wait_for("message", check=check, timeout=response_time)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            name = msg.content

        try:
            split = name.split('>')
            name = split[1]
        except IndexError:
            pass

        async with aiosqlite.connect(ratings_master_path) as db:
            async with db.execute(f"select player_name, discord_id from players_{guild_id} where player_name like ?",
                                  ('%' + name + '%',)) as c:
                names = await c.fetchall()
                if len(names) == 0:
                    await ctx.send(f"Name was not found!", delete_after=delete_delay)
                    return
                if len(names) == 1:
                    await ctx.send(f"Are you sure you want to delete {names[0][0]}? (y/n)", delete_after=delete_delay)
                    try:
                        yn = await client.wait_for("message", check=check, timeout=response_time)
                    except asyncio.TimeoutError:
                        await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                        return

                    if 'y' == yn.content:
                        await c.execute(f"delete from players_{guild_id} where player_name = ?", (names[0][0],))
                        await db.commit()
                        async with aiosqlite.connect(ratings_path) as dbr:
                            await dbr.execute(f"delete from ratings_{guild_id} where player_name = ?;", (names[0][0],))
                            await dbr.commit()
                        await ctx.send(f'{names[0][0]} was removed from the database!', delete_after=delete_delay)
                    else:
                        await ctx.send("Command aborted, no deletions have occurred.", delete_after=delete_delay)
                        return
                else:
                    members = ''
                    for i in range(len(names)):
                        members += names[i][0] + '\n'
                    await ctx.send(f"Multiple names were found!\n{members}Please specifiy which player you want "
                                   f"to drop", delete_after=delete_delay)
                    try:
                        name = await client.wait_for("message", check=check, timeout=response_time)
                    except asyncio.TimeoutError:
                        await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                        return
                    name = name.content

                    for i in range(len(names)):
                        if name == names[i][0]:
                            async with aiosqlite.connect(ratings_master_path) as db:
                                await db.execute(f"delete from players_{guild_id} where discord_id = ?", (names[i][1],))
                                await db.commit()
                            async with aiosqlite.connect(ratings_path) as d:
                                await d.execute(f"delete from ratings_{guild_id} where discord_id = ?", (names[i][1],))
                                await d.commit()
                            await ctx.send(f"{names[i][0]} with Discord ID {names[i][1]} has been deleted",
                                           delete_after=delete_delay)
                            return
                    await ctx.send("Name was not found! No information was changed", delete_after=delete_delay)


    async def leaderboard(message):
        try:
            emoji_object = rankEmoji(client=client)
            rank_emojis = emoji_object.rank_emoji()
            guild_id = message.guild.id
            new_embed = discord.Embed(title=f"Current Top {leaderboard_members} leaderboard by Elo rating:")
            async with aiosqlite.connect(ratings_path) as db:
                async with db.execute_fetchall(f"select * from ratings_{guild_id}") as cs:
                    cs.sort(key=lambda x: x[5], reverse=True)
                    for index, row in enumerate(cs):
                        if index == (leaderboard_members - 1):
                            break

                        clan_id = row[3]
                        player_name = row[4]
                        elo = row[5]
                        sigma = row[6]
                        wins = row[7]
                        losses = row[8]

                        name_string = f"{index+1}) {clan_id if clan_id != '<>' else ''}{player_name}"
                        wr = str(round(((wins / (wins + losses)) * 100), 2)) + '%' if wins > 0 or losses > 0 else 'N/A'
                        value_string = f'\nRating: {elo} Sigma: {sigma} \nWins: {wins} Losses: {losses} Winrate: {wr}'

                        rank = None
                        em = None
                        for k in ranks:
                            if elo >= ranks[k]:
                                rank = k
                                em = rank_emojis[k]
                            else:
                                break
                        new_embed.add_field(name=name_string, value=f'Rank: {rank} {em}{value_string}', inline=False)

            async with aiosqlite.connect(guild_settings_path) as db:
                async with db.execute_fetchall("select leaderboard_channel_id from guilds where guild_id = ?",
                                               (guild_id,)) as c:
                    channel = discord.utils.get(message.guild.channels, id=c[0][0])

                    async for message in channel.history(limit=200):
                        if message.author == client.user:
                            msg = await channel.fetch_message(message.id)
                            await msg.edit(embed=new_embed)
                            return
                    await channel.send(embed=new_embed)
        except Exception as e:
            await message.channel.send("An error occurred with the leaderboard function", delete_after=delete_delay)
            return


    @client.command('uptime', aliases=['up'])
    async def uptime(ctx):
        now = datetime.datetime.now().astimezone()
        delta = now - start_time
        delta_d_h_s = days_hours_minutes(delta)
        if delta_d_h_s[0]:
            time_format = f"**{delta_d_h_s[0]}** days, **{delta_d_h_s[1]}** hours and **{delta_d_h_s[2]}** minutes."
        else:
            time_format = f"**{delta_d_h_s[1]}** hours and **{delta_d_h_s[2]}** minutes."
        await ctx.send(f"{client.user.name} has been up for {time_format}", delete_after=10)


    @client.command('invite', aliases=['i'])
    async def invite_link(ctx):
        # Bot has the following permissions: Manage Roles and channels, view channels, Send messages, manage messages,
        # embed links, attach files, read message history, mention everyone, use external emojis
        oauth2_url = discord.utils.oauth_url(str(client.user.id), permissions=discord.Permissions(1342695440))
        await ctx.send(oauth2_url, delete_after=delete_delay)


    @client.command('help', aliases=['h'])
    async def help_command(ctx):
        embed = discord.Embed(colour=discord.Colour.blue())
        embed.set_author(name='Help and Documentation:')
        embed.add_field(name='Developers:', value='Bobo#6885 <@813330702712045590>, Sean#4318 <@202947434236739584>',
                        inline=False)
        embed.add_field(name='Commands:',
                        value='All commands are listed below, with the parenthesis giving the format for how the '
                              'command ought to be invoked. The user has the option to specify the arguments in the '
                              'same message that invokes the command i.e. (.add <Clan>Example), or to separate the '
                              'command and its arguments into different messages i.e. (.add) then (<Clan>Example). '
                              'Each argument is listed in quotes but quotes are used for demonstration and should not '
                              'be used when invoking the command, the type of the argument is also listed.',
                        inline=False)
        file = discord.File("./data/ArcturusMengsk_SC2_Cine1.jpg")
        embed.set_thumbnail(url='attachment://ArcturusMengsk_SC2_Cine1.jpg')
        embed.add_field(name='.add or .a',
                        value="Enter your name to be ranked, Clan tag is optional, Bot Admins may add other users by "
                              "specifying the unique Discord ID of the user (arguments: <Clan>Example *String* or "
                              "<Clan>Example *String* discord_id *Integer*).", inline=True)
        embed.add_field(name='.match or .m',
                        value="Add a new match to influence rating, Bot Admins may add matches between two other "
                              "users (arguments: <Clan>Example1 *String* Example1wins *Integer* "
                              "<Clan>Example2 *String* Example2wins *Integer*)",
                        inline=True)
        embed.add_field(name='.stats or .s',
                        value="Check the ratings of a member (arguments: 'player_name' *String*). Command checks if "
                              "multiple similar names exist and will ask you to clarify if that is the case.",
                        inline=True)
        embed.add_field(name='.help or .h', value='Shows this', inline=True)
        embed.add_field(name='.ping or .p', value='Bot latency (in ms)', inline=True)
        embed.add_field(name='.uptime or .up', value='Display how long bot has been running for', inline=True)
        embed.add_field(name='.block or .bl',
                        value="*Requires \'Bot Admin\' role* Blocks a user from inputting commands "
                              "(arguments: 'discord_id' or '@user')", inline=True)
        embed.add_field(name='.unblock or .u',
                        value="*Requires \'Bot Admin\' role* Un-blocks a user from inputting commands"
                              "(arguments: 'discord_id' or '@user')", inline=True)
        embed.add_field(name='.delete or .d',
                        value='*Requires \'Bot Admin\' role* Removes an erroneously entered name (arguments: '
                              '"player_name" *String*)', inline=True)
        embed.add_field(name='.editname or .en',
                        value='Edit your name (for typos and clan changes) (arguments: "player_name" *String*)',
                        inline=True)
        embed.add_field(name='.editrating or .er',
                        value='*Requires \'Bot Admin\' role* Edits the Elo of a player '
                              '(arguments: "player_name" *String* "new_elo" *Float*)', inline=True)
        embed.add_field(name='.editsigma or .es',
                        value='*Requires \'Bot Admin\' role* Edits the Sigma of a player '
                              '(arguments: "player_name" *String* "new_sigma" *Float*)', inline=True)
        embed.add_field(name='.restore or .r',
                        value='*Requires \'Bot Admin\' role* Restore database from previous date (WARNING: can '
                              'potentially cause problems) (server specific, arguments will be prompted)', inline=True)
        embed.add_field(name='.listmembers or .lm',
                        value='*Requires \'Bot Admin\' role* List all members being ranked '
                              '(server specific, takes no arguments)', inline=True)
        embed.add_field(name='.files or .f',
                        value='*Requires \'Bot Admin\' role* Displays contents of database files '
                              '(server specific, takes no arguments)', inline=True)
        embed.add_field(name='.invite or .i',
                        value='Returns the invite link for the bot', inline=True)
        embed.set_footer(icon_url=ctx.author.avatar_url,
                         text='Requested by {} on {}'.format(ctx.author, datetime.date.today().strftime("%m-%d-%Y")))
        await ctx.author.send(file=file, embed=embed)


    @client.event
    async def on_message(message):
        if message.author.name == client.user.name:
            return

        if message.guild.owner_id == message.author.id:
            await client.process_commands(message)
            return

        try:
            async with aiosqlite.connect(guild_settings_path) as db:
                async with db.execute_fetchall("select bot_channel_id from guilds where guild_id = ?",
                                               (message.guild.id,)) as c:
                    if c[0][0] != message.channel.id:
                        return
            async with aiosqlite.connect(blocked_ids_path) as db:
                async with db.execute_fetchall(f"select count(*) from bans_{message.guild.id} where discord_id = ?",
                                               (message.author.id,)) as c:
                    if c[0][0]:
                        await message.delete()
                        return
        except Exception:
            pass

        if message.content.startswith(prefix):
            await client.process_commands(message)
            await leaderboard(message)


    @client.command("shutdown")
    @commands.is_owner()
    async def shutdown(ctx):
        await client.change_presence(status=discord.Status.offline)
        await client.close()


    @client.command("master_view")
    @commands.is_owner()
    async def master_file_viewer(ctx):
        user = await client.fetch_user(ctx.author.id)
        for path in paths:
            file_write = f'./data/temp/{path}.txt'
            with open(file_write, "a") as f:
                async with aiosqlite.connect(f'./data/{path}.db') as db:
                    async for line in db.iterdump():
                        f.write(line + '\n')
            await user.send(file=discord.File(file_write), delete_after=delete_delay)
            os.remove(file_write)


    @client.event
    async def on_ready():
        print('Bot is active')
        await client.change_presence(status=discord.Status.online, activity=discord.Activity(
            type=3, name=f"{len(client.guilds)} servers. Type .help to get started"))
        Backup()


    @client.event
    async def on_error(event, *args, **kwargs):
        logger.warning(event)
        embed = discord.Embed(title=':x: Event Error', colour=0xe74c3c)  # Red
        embed.add_field(name='Event', value=event)
        embed.description = '```py\n%s\n```' % traceback.format_exc()
        embed.timestamp = datetime.datetime.utcnow()

        Bobo = await client.fetch_user(813330702712045590)
        await Bobo.send(embed=embed)
        logging.exception("Got exception on main handler", event)


    @client.event
    async def on_command_error(ctx, error):
        command_error_msg = f"Command \"{str(ctx.message.content).lstrip('.')}\" is not found"
        if str(error) == command_error_msg:
            return
        logger.debug(f"An error {error} occurred in {ctx.guild} invoked by {ctx.author} "
                     f"who inputted \"{ctx.message.content}\"")
        embed = discord.Embed(title=':x: Event Error', colour=0xe74c3c)  # Red
        embed.add_field(name='Event', value=error)
        embed.description = '```py\n%s\n```' % traceback.format_exc()
        embed.timestamp = datetime.datetime.utcnow()

        bobo = await client.fetch_user(813330702712045590)
        await bobo.send(embed=embed)
        logger.exception("Got exception on main handler", error)
        await ctx.send(f"An error has occurred. Try .help. If you believe this to be a bug, "
                       f"contact the bot developers", delete_after=15)

    # update the guilds we are in
    @client.event
    async def on_guild_join(guild):
        await client.change_presence(status=discord.Status.online, activity=discord.Activity(
            type=3, name=f"{len(client.guilds)} servers. Type .help to get started"))


    @client.event
    async def on_guild_remove(guild):
        await client.change_presence(status=discord.Status.online, activity=discord.Activity(
            type=3, name=f"{len(client.guilds)} servers. Type .help to get started"))


    @client.event
    async def on_guild_channel_delete(channel):
        try:
            async with aiosqlite.connect(guild_settings_path) as db:
                async with db.execute_fetchall("select bot_channel_id, leaderboard_channel_id from guilds "
                                               "where guild_id = ?", (channel.guild.id,)) as cursor:
                    if channel.id in cursor[0]:
                        user = await client.fetch_user(channel.guild.owner_id)
                        await user.send("It appears that a bot channel has been deleted! If you wish to create a new "
                                        "channel, please use .resetsettings to clear your server settings, then use "
                                        ".setup to reinitialize the bot's settings. All data stored in the player and "
                                        "ratings databases will not be removed unless the bot is removed from the "
                                        "server.")
        except IndexError:
            pass

    @client.event
    async def on_guild_role_delete(role):
        try:
            async with aiosqlite.connect(guild_settings_path) as db:
                async with db.execute_fetchall("select bot_admin_id from guilds where guild_id = ?",
                                               (role.guild.id,)) as cursor:
                    if role.id in cursor[0]:
                        user = await client.fetch_user(role.guild.owner_id)
                        await user.send("It appears that the bot admin role has been deleted! If you wish to create a "
                                        "new role, please use .resetsettings to clear your server settings, then use "
                                        ".setup to reinitialize the bot's settings. All data stored in the player and "
                                        "ratings databases will not be removed unless the bot is removed from the "
                                        "server.")
        except IndexError:
            pass
        
    # @client.event
    # async def on_member_remove(member):
    #    print(member)

    # @client.event
    # async def on_guild_channel_update(before, after):
    #    print(before)
    #    print(before.overwrites)
    #    print(before.id)
    #    print(after)
    #    print(after.overwrites)
    #    print(after.id)
    #    async with aiosqlite.connect(guild_settings_path) as db:
    #        async with db.execute_fetchall("select bot_channel_id, leaderboard_channel_id from guilds where "
    #                                       "guild_id = ?", (before.guild.id,)) as result:
    #           if after.id == result[0][0] or after.id == result[0][1]:
    #               print(after)
    #   if after.id == bot_channel_id
    #   channel.set_permissions(use_external_emojis true

    # This could potentially be needed to resolve conflicts in the
    # databases
    # @client.event
    # async def on_user_update(before, after):
    #     pseudo code
    #     if after.name != username in ratings_master.db:
    #          username == after.name where user.discord_id in players

    client.run(token)
