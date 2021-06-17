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
import sqlite3
import aiosqlite
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bot.config import *
import bot.glicko
from bot.sql_queries import *


def days_hours_minutes(td):
    return td.days, td.seconds // 3600, (td.seconds // 60) % 60


async def check_admin(guild_id):
    async with aiosqlite.connect(guild_settings_path) as db:
        async with db.execute("select bot_admin_id from guilds where guild_id = ?", (guild_id,)) as c:
            admin_id = await c.fetchone()
            if admin_id is None:
                return None
            return admin_id[0]


if __name__ == '__main__':
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    for path in path_list:
        if not os.path.isfile(path):
            if path == guild_settings_path:
                loop = asyncio.new_event_loop()
                asyncio.get_event_loop().run_until_complete(initialize_guild_settings())
                continue
            db_conn = sqlite3.connect(path)
            db_conn.close()

    prefix = '.'
    client = commands.Bot(command_prefix=prefix)
    client.remove_command('help')
    start_time = datetime.datetime.now().astimezone()

    load_dotenv(env_path)
    token = os.getenv("TEST_BOT")


    @client.command("ping", aliases=['p'])
    async def ping(ctx):
        await ctx.send(f'Bot Response Time: {round(client.latency * 1000)}ms ', delete_after=delete_delay)

    @client.command('reset_settings')
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
                res = await client.wait_for("message", check=check, timeout=180)
                try:
                    await client.fetch_channel(int(res.content))
                    bot_channel_id = res.content
                except Exception:
                    await ctx.send("You supplied an invalid response", delete_after=delete_delay)
                    return
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
            await ctx.send("please supply the channel id of the leaderboard channel", delete_after=delete_delay)
            try:
                res = await client.wait_for("message", check=check, timeout=180)
                try:
                    await client.fetch_channel(int(res.content))
                    leaderboard_channel_id = int(res.content)
                except Exception:
                    await ctx.send("You supplied an invalid response", delete_after=delete_delay)
                    return
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
        elif 'n' == yn.content:
            await ctx.send("Input hyphenated bot channel and leaderboard channel names separated by a space, in that "
                           "order. Example: ratings-bot-channel leaderboard-channel:", delete_after=delete_delay)
            try:
                channel_names = await client.wait_for("message", check=check, timeout=response_time)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return

            try:
                ch_names = channel_names.content.split(' ')
                if len(ch_names) > 2:
                    raise Exception("Too many arguments provided")
                bot_channel_name = ch_names[0]
                leaderboard_channel_name = ch_names[1]

                bot_channel = await ctx.message.guild.create_text_channel(str(bot_channel_name))
                leaderboard_channel = await ctx.message.guild.create_text_channel(leaderboard_channel_name)
                bot_channel_id = bot_channel.id
                leaderboard_channel_id = leaderboard_channel.id
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
                try:
                    r_id = await client.wait_for("message", check=check, timeout=response_time)
                    role = discord.utils.get(ctx.guild.roles, id=int(r_id.content))
                    bot_admin_id = int(r_id.content)
                except Exception:
                    await ctx.send("An error has occurred", delete_after=delete_delay)
                    return
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return
        elif 'n' == ynr.content:
            role = await ctx.message.guild.create_role(name="Bot Admin")
            bot_admin_id = role.id
            user = ctx.message.author
            await user.add_roles(role)
            await ctx.send("The \"Bot Admin\" Role has been created, feel free to give the role to other members but"
                           " please do not delete it as the id is hardcoded in the database.",
                           delete_after=delete_delay)
        else:
            await ctx.send("You supplied an invalid response", delete_after=delete_delay)
            return

        await ctx.send("Input starting elo and starting sigma and global ratings floor, separated by spaces "
                       "Example: 1200 150 900:", delete_after=delete_delay)

        try:
            ratings_set = await client.wait_for("message", check=check, timeout=180)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return

        try:
            ratings_settings = ratings_set.content.split(' ')
            if len(ratings_settings) > 3:
                raise Exception("Too many arguments provided")
            starting_elo = ratings_settings[0]
            starting_sigma = ratings_settings[1]
            global_elo_floor = ratings_settings[2]
        except Exception as e:
            await ctx.send(f"You did not follow the provided format! {e}", delete_after=delete_delay)
            return

        async with aiosqlite.connect(guild_settings_path) as db:
            params = (ctx.guild.id, bot_channel_id, leaderboard_channel_id, bot_admin_id, starting_elo, starting_sigma,
                      global_elo_floor,)
            await db.execute("insert into guilds values (?, ?, ?, ?, ?, ?, ?)", params)
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
                       it will automatically recreate itself''',
                       delete_after=120)


    @client.command("block", aliases=['bl', 'ban'])
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
        except ValueError:
            try:
                banned_id = int(id_to_block[3:-1])
            except ValueError:
                await ctx.send("Invalid input detected!", delete_after=delete_delay)
                return
        try:
            user = await client.fetch_user(banned_id)
        except Exception:
            await ctx.send("You provided an invalid ID!", delete_after=delete_delay)
            return
        name = user.name

        async with aiosqlite.connect(blocked_ids_path) as db:
            await db.execute(f"insert or ignore into bans_{ctx.guild.id} (discord_id, discord_name) values (?, ?)",
                             (banned_id, name,))
            await db.commit()
            await ctx.send(f'<@{banned_id}> You have been banned from using {client.user.name}', delete_after=delete_delay)

    # completed
    @client.command("unblock", aliases=['un', 'unban'])
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
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return

            id_to_unblock = unblockid.content

        try:
            unbanned_id = int(id_to_unblock)
        except ValueError:
            try:
                unbanned_id = int(id_to_unblock[3:-1])
            except ValueError:
                await ctx.send("Invalid input detected!", delete_after=delete_delay)
                return

        try:
            user = await client.fetch_user(unbanned_id)
        except Exception:
            await ctx.send("You provided an invalid ID!", delete_after=delete_delay)
            return

        async with aiosqlite.connect(blocked_ids_path) as db:
            await db.execute("delete from bans_" + f'{ctx.guild.id}' + " where discord_id = ?", (unbanned_id,))
            await db.commit()
            await ctx.send(f"<@{unbanned_id}> You have been unbanned from using {client.user.name}",
                           delete_after=delete_delay)

    # completed
    @tasks.loop(hours=12)
    async def backup(ctx):
        todays_date = datetime.date.today().strftime("%m-%d-%Y")
        backup_file = f'./data/ratings_backup_{todays_date}.db'
        source = sqlite3.connect(ratings_path)
        destination = sqlite3.connect(backup_file)
        source.backup(destination)
        source.close()

        backup_file = f'./data/ratings_master_backup_{todays_date}.db'
        source = sqlite3.connect(ratings_master_path)
        destination = sqlite3.connect(backup_file)
        source.backup(destination)
        source.close()

        backup_file = f'./data/matches_backup_{todays_date}.db'
        source = sqlite3.connect(matches_path)
        destination = sqlite3.connect(backup_file)
        source.backup(destination)
        source.close()

        backup_file = f'./data/guild_settings_backup_{todays_date}.db'
        source = sqlite3.connect(guild_settings_path)
        destination = sqlite3.connect(backup_file)
        source.backup(destination)
        source.close()

        backup_file = f'./data/banned_ids_backup_{todays_date}.db'
        source = sqlite3.connect(blocked_ids_path)
        destination = sqlite3.connect(backup_file)
        source.backup(destination)
        source.close()

        # prunes old backups
        backup_files = glob.glob('./data/*_backup_*.db')
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
    @commands.is_owner()
    async def restore(ctx):
        backup_files = glob.glob('./data/ratings_backup_*.db')
        if len(backup_files) == 0:
            await ctx.send("No backups to restore from", delete_after=delete_delay)
            return

        await ctx.send(f"Input date to restore ratings from (format mo-dy-year).\n"
                       f"Available dates to restore from: {backup_files}", delete_after=delete_delay)

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        try:
            date_to_restore = await client.wait_for("message", check=check, timeout=response_time)
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
    async def list_members(ctx):
        bot_admin_id = await check_admin(ctx.guild.id)
        role = ctx.guild.get_role(bot_admin_id)
        if role not in ctx.author.roles:
            await ctx.send("You do not have the proper permissions to use this command", delete_after=delete_delay)
            return

        members = ''
        i = 0
        async with aiosqlite.connect(ratings_master_path) as db:
            async with db.execute(f"select clan_id, player_name from players_{ctx.guild.id}") as cursor:
                async for row in cursor:
                    members += f'{row[0]}{row[1]}\n'
                    i += 1
                await ctx.send(f"There are {i} ranked members:\n{members}", delete_after=delete_delay)

    # completed
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
                             "losses + ? where discord_id = ?;",
                             (p1_new_rating, p1_new_sigma, persononewins, persontwowins, p1_info[0],))
            await db.commit()
            await db.execute(f"update ratings_{guild_id} set rating = ?, sigma = ?, wins = wins + ?, losses = "
                             "losses + ? where discord_id = ?;",
                             (p2_new_rating, p2_new_sigma, persontwowins, persononewins, p2_info[0],))
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

    # completed
    @client.command("filecontents", aliases=['fc'])
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

        i = 1
        ratings_embed = discord.Embed(title="Contents of \'ratings.db\'")
        async with aiosqlite.connect(ratings_path) as db:
            async with db.execute(f"select * from ratings_{guild_id}") as cur:
                async for row in cur:
                    ratings_embed.add_field(name=str(i), value=str(row), inline=False)
                    i += 1
        await user.send(embed=ratings_embed, delete_after=delete_delay)

        i = 1
        ratings_master_embed = discord.Embed(title="Contents of \'ratings_master.db\'")
        async with aiosqlite.connect(ratings_master_path) as db:
            async with db.execute(f"select * from players_{guild_id}") as cur:
                async for row in cur:
                    ratings_master_embed.add_field(name=str(i), value=str(row), inline=False)
                    i += 1
        await user.send(embed=ratings_master_embed, delete_after=delete_delay)

        i = 1
        matches_embed = discord.Embed(title="Contents of \'matches.db\'")
        async with aiosqlite.connect(matches_path) as db:
            async with db.execute(f"select * from matches_{guild_id}") as cur:
                async for row in cur:
                    matches_embed.add_field(name=str(i), value=str(row), inline=False)
                    i += 1
        await user.send(embed=matches_embed, delete_after=delete_delay)

        i = 1
        bans_embed = discord.Embed(title="Contents of \'banned_ids.db\'")
        async with aiosqlite.connect(blocked_ids_path) as db:
            async with db.execute(f"select * from bans_{guild_id}") as cur:
                async for row in cur:
                    bans_embed.add_field(name=str(i), value=str(row), inline=False)
                    i += 1
        await user.send(embed=bans_embed, delete_after=delete_delay)

        i = 1
        guilds_embed = discord.Embed(title="Contents of \'guild_settings.db\'")
        async with aiosqlite.connect(guild_settings_path) as db:
            async with db.execute("select * from guilds where guild_id = ?", (guild_id,)) as cur:
                async for row in cur:
                    guilds_embed.add_field(name=str(i), value=str(row), inline=False)
                    i += 1
        await user.send(embed=guilds_embed, delete_after=delete_delay)

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
        line_no = split_msg[1]

        if 'matches' in file_name:
            async with aiosqlite.connect(matches_path) as db:
                await db.execute(f"delete from matches_{guild_id} where rowid = ?;", (line_no,))
                await db.commit()
        elif 'ratings_master' in file_name:
            async with aiosqlite.connect(ratings_master_path) as db:
                await db.execute(f"delete from players_{guild_id} where rowid = ?;", (line_no,))
                await db.commit()
        elif 'ratings' in file_name:
            async with aiosqlite.connect(ratings_path) as db:
                await db.execute(f"delete from ratings_{guild_id} where rowid = ?;", (line_no,))
                await db.commit()
        elif 'banned' in file_name:
            async with aiosqlite.connect(blocked_ids_path) as db:
                await db.execute(f"delete from players_{guild_id} where rowid = ?;", (line_no,))
                await db.commit()
        elif 'settings' in file_name:
            async with aiosqlite.connect(guild_settings_path) as db:
                await db.execute("delete from guilds where rowid = ?;", (line_no,))
                await db.commit()

        await ctx.send(f"Line {line_no} in File {file_name} has been removed", delete_after=delete_delay)

    # completed
    @client.command("editelo", aliases=['ee'])
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

    # completed
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

    # completed and rewritten in async format
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
                    await ctx.send("Name already exists!", delete_after=delete_delay)
                    return

            async with db.execute(f"select discord_id from players_{guild_id} where player_name = ?",
                                  (name,)) as cur:
                search = await cur.fetchone()
                if search is None:
                    await ctx.send(f"Name {name} does not exist!", delete_after=delete_delay)
                    return
            # if bot admin
            if role in ctx.author.roles:
                author_id = search[0]
            elif author_id != search[0]:
                await ctx.send("Only Bot admins may change other member's names!", delete_after=delete_delay)
                return

            # a non bot admin can only ever change their own name
            await db.execute(f"update players_{guild_id} set player_name = ? where discord_id = ?;",
                             (new_name.content, author_id,))
            await db.commit()

        async with aiosqlite.connect(ratings_path) as db:
            await db.execute(f"update ratings_{guild_id} set player_name = ? where discord_id = ?;",
                             (new_name.content, author_id,))
            await db.commit()
            await ctx.send(f"<@{author_id}> Your name was changed from {name} to {new_name.content}")

    # completed and rewritten in async format
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
                tslm = datetime.datetime.utcnow() - datetime.datetime.fromisoformat(r[6])
                t = days_hours_minutes(tslm)
                await ctx.send(f"Stats for {r[0]}{r[1]}:\nRating: {r[2]}\nSigma: {r[3]}\nWins: {r[4]}\nLosses: {r[5]}\n"
                               f"Time since last match: {t[0]} days, {t[1]} hours and {t[2]} minutes",
                               delete_after=delete_delay)

    # completed and rewritten in async format
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
                           f"Elo starts at {starting_elo} and Sigma starts at {starting_sigma} for all players.\n"
                           f"Bot Admins are allowed to enter in members other than themselves by specifying <clan>name"
                           f"then discord_id i.e. <BestClan>Example 112233445566778899", delete_after=delete_delay)
            try:
                msg = await client.wait_for("message", check=check, timeout=response_time)
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
            async with db.execute(f"select 1 from players_{guild_id} where discord_id = ? limit 1", (author_id,)) as cur:
                if await cur.fetchone() is None:
                    await cur.execute(f"insert into players_{guild_id} (discord_id, discord_name, clan_id, player_name)"
                                      f" values (?, ?, ?, ?)", (author_id, str(user), clan, name,))
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
            await ctx.send(f'<@{author_id}> was successfully registered in the database, GLHF!', delete_after=delete_delay)

    # completed and rewritten in async format
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
            cur = await db.execute(f"select player_name from players_{guild_id} where player_name like ?",
                                   ('%' + name + '%',))
            name = await cur.fetchone()
            await ctx.send(f"Are you sure you want to delete {name[0]}? (y/n)")
            try:
                yn = await client.wait_for("message", check=check, timeout=response_time)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return

            if 'y' == yn.content:
                await cur.execute(f"delete from players_{guild_id} where player_name = ?", (name[0],))
                await db.commit()
                async with aiosqlite.connect(ratings_path) as dbr:
                    await dbr.execute(f"delete from ratings_{guild_id} where player_name = ?;", (name[0],))
                    await dbr.commit()
                await ctx.send(f'{name[0]} was removed from the database!', delete_after=delete_delay)
            else:
                await ctx.send("Command aborted, no deletions have occurred.", delete_after=delete_delay)
                return

    # completed and rewritten in async format
    async def leaderboard(message):
        try:
            emoji_object = rankEmoji(client=client)
            rank_emojis = emoji_object.rank_emoji()

            async with aiosqlite.connect(guild_settings_path) as db:
                cur = await db.execute("select leaderboard_channel_id from guilds where guild_id = ?",
                                       (message.guild.id,))
                leaderboard_channel = await cur.fetchone()
                channel = discord.utils.get(message.guild.text_channels, id=leaderboard_channel[0])
                msgs = await channel.history(limit=100).flatten()

            ratings = []
            new_embed = discord.Embed(title=f"Current Top {leaderboard_members} leaderboard by Elo rating:")

            async with aiosqlite.connect(ratings_path) as db:
                async with db.execute(f"select * from ratings_{message.guild.id}") as cs:
                    async for row in cs:
                        ratings.append(row)
                    ratings.sort(key=lambda x: x[5], reverse=True)

            for index, row in enumerate(ratings):
                if index == (leaderboard_members - 1):
                    break

                clan_id = row[3]
                player_name = row[4]
                rating = row[5]
                sigma = row[6]
                wins = row[7]
                losses = row[8]

                if clan_id == '<>':
                    name_string = f'{index+1}) {player_name}'
                else:
                    name_string = f'{index+1}) {clan_id}{player_name}'

                try:
                    winrate_pct = round(((wins / (wins + losses)) * 100), 2)
                    winrate = str(winrate_pct) + '%'
                except ZeroDivisionError:
                    winrate = 'N/A'

                value_string = f'\nRating: {rating} Sigma: {sigma} \nWins: {wins} Losses: {losses} Winrate: {winrate}'
                rank = None
                em = None
                for k in ranks:
                    if rating >= ranks[k]:
                        rank = k
                        em = rank_emojis[k]
                    else:
                        break
                new_embed.add_field(name=name_string, value=f'Rank: {rank} {em}{value_string}',
                                    inline=False)

            if len(msgs) == 0:
                await channel.send(embed=new_embed)
            else:
                for message in msgs:
                    if message.author.name == client.user.name:
                        message = await channel.fetch_message(message.id)
                        await message.edit(embed=new_embed)
        except Exception as e:
            await message.channel.send("An error occurred with the leaderboard function", delete_after=delete_delay)
            pass


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


    @client.command('help', aliases=['h'])
    async def help_command(ctx):
        embed = discord.Embed(colour=discord.Colour.blue())
        embed.set_author(name='Help:')
        embed.add_field(name='Developers:', value='Bobo#6885 <@813330702712045590>, Sean#4318 <@202947434236739584>',
                        inline=False)
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
        embed.add_field(name='.admin_add or .aa', value='*Requires \'Bot Admin\' role* Used for adding a person other '
                                                        'than yourself', inline=True)
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
        if message.author.name == client.user.name:
            return

        if str(message.content) == '.reset_settings' or str(message.content) == '.setup':
            await client.process_commands(message)
            return

        try:
            async with aiosqlite.connect(guild_settings_path) as db:
                cs = await db.execute("select bot_channel_id from guilds where guild_id = ?", (message.guild.id,))
                bot_channel_id = await cs.fetchone()
                if bot_channel_id is None:
                    pass
                if bot_channel_id[0] != message.channel.id:
                    return
        except Exception:
            pass

        try:
            async with aiosqlite.connect(blocked_ids_path) as db:
                async with db.execute(f"select discord_id from bans_{message.guild.id}") as bans:
                    if bans is None:
                        return
                    async for row in bans:
                        if message.author.id == row[0]:
                            await message.delete()
                            return
        except Exception:
            pass

        if message.content.startswith(prefix):
            await client.process_commands(message)
            await leaderboard(message)
            return


    @client.command("shutdown")
    @commands.is_owner()
    async def shutdown(ctx):
        await client.change_presence(status=discord.Status.offline)
        await client.close()


    @client.event
    async def on_ready():
        print('Bot is active')
        await client.change_presence(status=discord.Status.online, activity=discord.Activity(
            type=3, name=f"{len(client.guilds)} servers. Type .help to get started"))


    @client.event
    async def on_command_error(ctx, error):
        logger.debug(f"An error {error} occurred in {ctx.guild} invoked by {ctx.author} "
                     f"who inputted \"{ctx.message.content}\"")
        logger.exception(error)
        await ctx.send(f"An error has occurred {error}. Try .help. If you believe this to be a bug, "
                       f"contact the bot developers", delete_after=15)

    # possible future implementations of more client events
    # @client.event
    # async def on_guild_channel_delete(channel):
    #     print(channel.id)

    # @client.event
    # async def on_guild_channel_update(before, after):
    #     print(after.id)
    #     pseudo code
    #     if after.id == bot_channel_id
    #     channel.set_permissions(use_external_emojis true

    # This could potentially be needed to resolve conflicts in the
    # databases
    # @client.event
    # async def on_user_update(before, after):
    #     pseudo code
    #     if after.name != username in ratings_master.db:
    #          username == after.name where user.discord_id in players

    client.run(token)
