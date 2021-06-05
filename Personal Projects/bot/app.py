import discord
from discord.ext import commands
import os
import datetime
import glob
import re
import asyncio

from bot.glicko import Glicko2

if __name__ == '__main__':
    TOKEN = open("./token.txt", 'r').readline()
    prefix = '.'
    client = commands.Bot(command_prefix=prefix)
    client.remove_command('help')

    start_time = datetime.datetime.now().astimezone()

    delete_delay = 45
    name_of_bot = "Competitive Elo Tracker"
    bot_channel_id = 847304034310291456
    owner_id = 813330702712045590
    bot_admin_role_id = 843673834333667369
    leaderboard_channel_id = 845769329068605491

    starting_elo = 1200
    starting_sigma = 250

    if not os.path.exists("bot/data/matches.txt"):
        f = open("bot/data/matches.txt", "w")
        f.close()
    if not os.path.exists("bot/data/ratings.txt"):
        f = open("bot/data/ratings.txt", "w")
        f.close()
    if not os.path.exists("bot/data/ratings_master.txt"):
        f = open("bot/data/ratings_master.txt", "w")
        f.close()
    if not os.path.exists("bot/data/blocked_ids.txt"):
        f = open("bot/data/blocked_ids.txt", "w")
        f.close()

    rank0 = 'Novice'
    rank1 = 'Class C'
    rank2 = 'Class B'
    rank3 = 'Class A'
    rank4 = 'Provisional Master'
    rank5 = 'Master'
    rank6 = 'Grandmaster'
    ranks = {rank0: 900, rank1: 1000, rank2: 1100, rank3: 1200, rank4: 1300, rank5: 1450, rank6: 1600}


    @client.command()
    @commands.has_role('Bot Admin')
    async def ping(ctx):
        await ctx.send(f'Bot Response Time: {round(client.latency * 1000)}ms ', delete_after=delete_delay)


    @client.command("block")
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
        with open("bot/data/blocked_ids.txt", "a+") as f0:
            f0.write(id_to_block + '\n')


    @client.command("unblock")
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

        with open('bot/data/blocked_ids.txt', 'r+') as f0:
            data = f0.readlines()
            f0.seek(0)
            for line in data:
                if id_to_unblock in line:
                    continue
                f0.write(line)
            f0.truncate()


    @client.command("backupratings")
    @commands.has_role('Bot Admin')
    async def backup(ctx):
        with open('bot/data/ratings.txt', 'r') as file:
            data = file.readlines()

        backup_file = 'bot/data/ratings_backup_{}.txt'.format(
            datetime.date.today().strftime("%m-%d-%Y"))
        with open(backup_file, 'w') as file:
            file.writelines(data)

        backup_files = glob.glob('bot/data/ratings_backup_*.txt')
        for file in backup_files:
            re_match = re.search(r'\d{2}-\d{2}-\d{4}', file)
            date = datetime.datetime.strptime(re_match.group(), '%m-%d-%Y').date()
            one_week_ago = datetime.date.today() - datetime.timedelta(days=7)
            if one_week_ago > date:
                pruned_backup = str('./') + str(file)
                os.remove(pruned_backup)

        await ctx.send("ELO backed up for today {}".format(datetime.date.today().strftime("%m-%d-%Y")),
                       delete_after=delete_delay)


    @client.command("restoreratings")
    @commands.has_role('Bot Admin')
    async def restore(ctx):
        backup_files = glob.glob('bot/data/ratings_backup_*.txt')
        await ctx.send("Input date to restore from (format mo-dy-year):", delete_after=delete_delay)
        await ctx.send(f"Available dates to restore from: {backup_files}", delete_after=delete_delay)

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        try:
            date_to_restore = await client.wait_for("message", check=check, timeout=delete_delay)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return

        try:
            with open(f'bot/data/ratings_backup_{date_to_restore.content}.txt', 'r') as file:
                data = file.readlines()
        except Exception as e:
            await ctx.send(f"Could not find backup for the date specified, error: {e}", delete_after=delete_delay)
            return

        with open('bot/data/ratings.txt', 'w') as file:
            file.writelines(data)
        await ctx.send(f'ELO data restored from backup made on {date_to_restore.content}', delete_after=delete_delay)


    @client.command("listmembers")
    @commands.has_role('Bot Admin')
    async def list_members(ctx):
        with open('bot/data/ratings_master.txt', 'r') as file:
            data = file.readlines()

        members_array = []
        for line in data:
            try:
                split = line.split()
                members_array.append(split[0])
            except IndexError:
                pass

        members_string = f'There are {len(members_array)} ranked members: ' + '\n'.join(p for p in members_array)
        await ctx.send(members_string, delete_after=delete_delay)


    @client.command("match")
    async def match(ctx, personone: str = None, persononewins: int = None, persontwo: str = None,
                    persontwowins: int = None):
        guild = client.guilds
        gm = None
        m = None
        pm = None
        classa = None
        classb = None
        classc = None
        novice = None
        for i in guild:
            if str(i) == "Risk Legacy Competitive":
                for j in i.emojis:
                    if str(j) == '<:GMrank:847985103787524147>':
                        gm = j
                    if str(j) == '<:Masterrank:847985113244499978>':
                        m = j
                    if str(j) == '<:PMrank:847985121478049823>':
                        pm = j
                    if str(j) == '<:ClassArank:847985131809538059>':
                        classa = j
                    if str(j) == '<:ClassBrank:847985143389356052>':
                        classb = j
                    if str(j) == '<:ClassCrank:847985151631949835>':
                        classc = j
                    if str(j) == '<:Novicerank:847985160711569468>':
                        novice = j

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if personone is None or persononewins is None or persontwo is None or persontwowins is None:
            await ctx.send("Input new match to influence rating, format is Name1 (wins) Name2 (wins), example: "
                           "<BestClan>AlphaBeta 5 <WorstClan>OmegaLambda 5. Global Elo floor is 900. "
                           "There is no Elo ceiling.", delete_after=delete_delay)

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

        maxwinsallowed = 15
        if persononewins > maxwinsallowed or persontwowins > maxwinsallowed:
            await ctx.send(f'You have exceeded the number of wins allowed in a single session ({maxwinsallowed})',
                           delete_after=delete_delay)
            return

        with open('bot/data/ratings_master.txt') as file:
            if personone not in file.read():
                await ctx.send(f'{personone} has not been added yet!', delete_after=delete_delay)
                return
        with open('bot/data/ratings_master.txt') as file:
            if persontwo not in file.read():
                await ctx.send(f'{persontwo} has not been added yet!', delete_after=delete_delay)
                return

        persononeelo = 0
        persononesigma = 0
        persontwoelo = 0
        persontwosigma = 0

        currentelofile = open('bot/data/ratings.txt.txt')
        for line in currentelofile:
            elofileline = line.split()
            if personone in elofileline[0]:
                persononeelo = float(elofileline[2])
                persononesigma = float(elofileline[4])
                break
        currentelofile.close()

        currentelofile = open('bot/data/ratings.txt')
        for line in currentelofile:
            elofileline = line.split()
            if persontwo in elofileline[0]:
                persontwoelo = float(elofileline[2])
                persontwosigma = float(elofileline[4])
                break
        currentelofile.close()

        base = Glicko2(tau=1.0, epsilon=0.000001)

        p1ratingobject = base.create_rating(persononeelo, persononesigma)
        p2ratingobject = base.create_rating(persontwoelo, persontwosigma)

        win_array = []
        loss_array = []
        for i in range(persononewins):
            win_array.append((1.0, p2ratingobject))
            loss_array.append((0., p1ratingobject))
        for i in range(persontwowins):
            win_array.append((0., p2ratingobject))
            loss_array.append((1.0, p1ratingobject))

        p1_rating = base.rate(p1ratingobject, win_array)
        p2_rating = base.rate(p2ratingobject, loss_array)

        p1newelo = round(p1_rating.mu, 2)
        p1newsigma = round(p1_rating.phi, 2)
        p2newelo = round(p2_rating.mu, 2)
        p2newsigma = round(p2_rating.phi, 2)

        new_data = []
        with open("bot/data/ratings.txt", 'r') as file:
            for i, line in enumerate(file.readlines(), 1):
                if line == '\n':
                    continue
                linesplitted = line.split()
                if personone in linesplitted[0]:
                    linesplitted[2] = str(round(p1newelo, 2))
                    linesplitted[4] = str(round(p1newsigma, 2))
                    personone = linesplitted[0]
                if persontwo in linesplitted[0]:
                    linesplitted[2] = str(round(p2newelo, 2))
                    linesplitted[4] = str(round(p2newsigma, 2))
                    persontwo = linesplitted[0]
                line = ' '.join(linesplitted)
                new_data.append(line)

        if personone == persontwo:
            await ctx.send("You cannot input a match against yourself", delete_after=delete_delay)
            return

        length = len(new_data) - 1
        with open('bot/data/ratings.txt', 'w') as file:
            for index, line in enumerate(new_data):
                if index == length:
                    file.writelines(f'{line}')
                    break
                file.writelines(f'{line}\n')

        time_f = datetime.datetime.now().astimezone()
        tz = ''.join([c for c in str(time_f.tzinfo) if c.isupper()])
        match_backup = open("bot/data/matches.txt", "a+")
        match_backup.write(f'{personone} {persononewins} - {persontwo} {persontwowins} Match inputted by '
                           f'{ctx.author} at: {time_f} Timezone: {tz}\n')
        match_backup.close()

        search_for_person_two = False
        search_for_person_one = False
        id_to_notify = 0

        with open('bot/data/ratings_master.txt') as file:
            for i, line in enumerate(file.readlines(), 1):
                linesplit = line.split()
                id_substring = re.search("<@(.*?)>", str(linesplit[-1])).group(1)
                id_to_notify = int(id_substring)
                if id_to_notify == ctx.author.id and personone == linesplit[0]:
                    search_for_person_two = True
                    break
                if id_to_notify == ctx.author.id and persontwo == linesplit[0]:
                    search_for_person_one = True
                    break

        role = discord.utils.get(ctx.guild.roles, id=bot_admin_role_id)
        if not search_for_person_one and not search_for_person_two and role not in ctx.author.roles:
            await ctx.send("You cannot input a match concerning two other people!", delete_after=delete_delay)
            return

        with open('bot/data/ratings_master.txt') as file:
            for i, line in enumerate(file.readlines(), 1):
                linesplit = line.split()
                id_substring = re.search("<@(.*?)>", str(linesplit[-1])).group(1)
                id_to_notify = int(id_substring)
                if search_for_person_two:
                    if linesplit[0] == persontwo:
                        id_to_notify = id_to_notify
                        break
                if search_for_person_one:
                    if linesplit[0] == personone:
                        id_to_notify = id_to_notify
                        break

        await ctx.send(f'<@{id_to_notify}> A match involving you was just added. The match results have been sent to '
                       f'you for your perusal', delete_after=delete_delay)

        user = await client.fetch_user(id_to_notify)
        if search_for_person_two:
            await user.send(f'<@{id_to_notify}>, A match was added with a score of {persononewins} wins for {personone}'
                            f' and {persontwowins} wins for {persontwo}, if this result is incorrect, please contact '
                            f'the Bot Administrators.\nOld Elo: {persontwoelo}   Old Sigma: {persontwosigma}.'
                            f'\nNew Elo: {p2newelo}   New Sigma: {p2newsigma}.')
        if search_for_person_one:
            await user.send(f'<@{id_to_notify}>, A match was added with a score of {persononewins} wins for {personone}'
                            f' and {persontwowins} wins for {persontwo}, if this result is incorrect, please contact '
                            f'the Bot Administrators.\nOld Elo: {persononeelo}   Old Sigma: {persononesigma}.'
                            f'\nNew Elo: {p1newelo}   New Sigma: {p1newsigma}.')

        emoji1 = None
        rankp1 = rank0
        if float(p2newelo) < float(ranks[rank1]):
            rankp1 = rank0
            emoji1 = novice
        elif float(ranks[rank1]) <= float(p2newelo) < float(ranks[rank2]):
            rankp1 = rank1
            emoji1 = classc
        elif float(ranks[rank2]) <= float(p1newelo) < float(ranks[rank3]):
            rankp1 = rank2
            emoji1 = classb
        elif float(ranks[rank3]) <= float(p1newelo) < float(ranks[rank4]):
            rankp1 = rank3
            emoji1 = classa
        elif float(ranks[rank4]) <= float(p1newelo) < float(ranks[rank5]):
            rankp1 = rank4
            emoji1 = pm
        elif float(ranks[rank5]) <= float(p1newelo) < float(ranks[rank6]):
            rankp1 = rank5
            emoji1 = m
        elif float(p1newelo) >= float(ranks[rank6]):
            rankp1 = rank6
            emoji1 = gm

        emoji2 = None
        rankp2 = rank0
        if float(p2newelo) < float(ranks[rank1]):
            rankp2 = rank0
            emoji2 = novice
        elif float(ranks[rank1]) <= float(p2newelo) < float(ranks[rank2]):
            rankp2 = rank1
            emoji2 = classc
        elif float(ranks[rank2]) <= float(p2newelo) < float(ranks[rank3]):
            rankp2 = rank2
            emoji2 = classb
        elif float(ranks[rank3]) <= float(p2newelo) < float(ranks[rank4]):
            rankp2 = rank3
            emoji2 = classa
        elif float(ranks[rank4]) <= float(p2newelo) < float(ranks[rank5]):
            rankp2 = rank4
            emoji2 = pm
        elif float(ranks[rank5]) <= float(p2newelo) < float(ranks[rank6]):
            rankp2 = rank5
            emoji2 = m
        elif float(p2newelo) >= float(ranks[rank6]):
            rankp2 = rank6
            emoji2 = gm

        color1 = None
        color2 = None
        if p1newelo < persononeelo:
            color1 = f'```diff\n- {p1newelo} {rankp1}\nnew Sigma {p1newsigma} \n```'
        if p1newelo > persononeelo:
            color1 = f'```diff\n+ {p1newelo} {rankp1}\nnew Sigma {p1newsigma} \n```'
        if p2newelo < persontwoelo:
            color2 = f'```diff\n- {p2newelo} {rankp2}\nnew Sigma {p2newsigma} \n```'
        if p2newelo > persontwoelo:
            color2 = f'```diff\n+ {p2newelo} {rankp2}\nnew Sigma {p2newsigma} \n```'

        await ctx.send(f"Updated Ratings (automatically saved to file):\n\n{personone}\'s Rank: {emoji1} {color1}\n"
                       f"{persontwo}\'s Rank: {emoji2} {color2}", delete_after=delete_delay)


    @client.command("filecontents")
    @commands.has_role('Bot Admin')
    async def file_contents(ctx):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        user = await client.fetch_user(owner_id)
        with open('bot/data/ratings.txt', 'r') as file:
            current_elo_embed = discord.Embed(title="Contents of \'ratings.txt\'")
            for i, line in enumerate(file.readlines(), 1):
                if line == '\n':
                    continue
                current_elo_embed.add_field(name=str(i), value=line, inline=False)
        await user.send(embed=current_elo_embed, delete_after=delete_delay)

        with open('bot/data/ratings_master.txt', 'r') as file:
            master_backup_embed = discord.Embed(title="Contents of \'ratings_master.txt\'")
            for i, line in enumerate(file.readlines(), 1):
                if line == '\n':
                    continue
                master_backup_embed.add_field(name=str(i), value=line, inline=False)
        await user.send(embed=master_backup_embed, delete_after=delete_delay)

        with open('bot/data/matches.txt', 'r') as file:
            match_backup_embed = discord.Embed(title="Contents of \'matches.txt\'")
            for i, line in enumerate(file.readlines(), 1):
                if line == '\n':
                    continue
                match_backup_embed.add_field(name=str(i), value=line, inline=False)
        await user.send(embed=match_backup_embed, delete_after=delete_delay)

        await ctx.send("Input which line of which file you want to delete:\nformat(\"file name\", (line #))",
                       delete_after=delete_delay)

        try:
            msg = await client.wait_for("message", check=check, timeout=120)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return
        split_msg = msg.content.split(',')
        file_name = split_msg[0]
        line_no = split_msg[1]
        old_file = []
        with open('bot/data/{}'.format(file_name), 'r') as file:
            for i, line in enumerate(file.readlines(), 1):
                if i == int(line_no):
                    continue
                old_file.append(line)
        with open('bot/data/{}'.format(file_name), 'w') as file:
            for line in old_file:
                file.writelines(line)
        await ctx.send(f"Line {line_no} in File {file_name} has been removed", delete_after=delete_delay)


    @client.command("editelo")
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

        with open('bot/data/ratings.txt', 'r+') as f0:
            data = f0.readlines()
            f0.seek(0)
            for line in data:
                if name in line:
                    line = line.replace(line.split()[2], newelo)
                    name = line.split()[0]
                f0.write(line)
            f0.truncate()

        await ctx.send(name + "\'s elo has been changed to " + newelo)


    @client.command("editsigma")
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
        with open('bot/data/ratings.txt', 'r+') as f0:
            data = f0.readlines()
            f0.seek(0)
            for line in data:
                if name in line:
                    line = line.replace(line.split()[4], newsigma)
                    name = line.split()[0]
                f0.write(line)
            f0.truncate()

        await ctx.send(f'{name}\'s sigma has been changed to {newsigma}')


    @client.command('editname')
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

        role = discord.utils.get(ctx.guild.roles, id=bot_admin_role_id)
        line_to_change = None
        with open('bot/data/ratings_master.txt', 'r') as f0:
            for i, line in enumerate(f0.readlines(), 1):
                if line == '\n':
                    continue
                newline = line.split()
                if name in newline[0] and f'<@{ctx.author.id}>' in line:
                    await ctx.send(f"Old name was found: {line}", delete_after=delete_delay)
                    line_to_change = i
                    break
                elif name in newline[0] and f'<@{ctx.author.id}>' not in line and role not in ctx.author.roles:
                    await ctx.send("You are not allowed to change someone else's name!", delete_after=delete_delay)
                    return
            if line_to_change is None:
                await ctx.send("Name was not found!", delete_after=delete_delay)
                return

        await ctx.send("Enter new name:", delete_after=delete_delay)
        try:
            new_name = await client.wait_for("message", check=check, timeout=delete_delay)
        except asyncio.TimeoutError:
            await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
            return

        amended_line = None
        with open('bot/data/ratings_master.txt', 'r+') as f1:
            data = f1.readlines()
            f1.seek(0)
            for i, line in enumerate(data):
                line_split = line.split()
                if new_name.content.lower() == line_split[0].lower():
                    await ctx.send(f"New name matches an existing name: {line_split[0]}", delete_after=delete_delay)
                    return
                if (i+1) == line_to_change:
                    line_split[0] = new_name.content
                    line = ' '.join(line_split) + '\n'
                    if i+1 == len(data):
                        line = ' '.join(line_split)
                    amended_line = f'{line_split[0]} {line_split[1]} {line_split[2]} {line_split[3]} {line_split[4]}'
                f1.write(line)
            f1.truncate()

        with open('bot/data/ratings.txt', 'r+') as f2:
            data = f2.readlines()
            f2.seek(0)
            for i, line in enumerate(data):
                if (i+1) == line_to_change:
                    line = amended_line + '\n'
                    if i+1 == len(data):
                        line = amended_line
                f2.write(line)
            f2.truncate()

        await ctx.send("Name has been updated", delete_after=delete_delay)


    @client.command('stats')
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

        with open('bot/data/ratings_master.txt') as file:
            if name not in file.read():
                await ctx.send('This member has not been added!', delete_after=delete_delay)
                return

        with open('bot/data/ratings.txt', 'r') as file:
            for i, line in enumerate(file.readlines(), 1):
                if line == '\n':
                    continue
                s_line = line.split()
                if name.lower() in s_line[0].lower():
                    if float(s_line[2]) < float(ranks[rank1]):
                        rank = rank0
                    elif float(ranks[rank1]) <= float(s_line[2]) < float(ranks[rank2]):
                        rank = rank1
                    elif float(ranks[rank2]) <= float(s_line[2]) < float(ranks[rank3]):
                        rank = rank2
                    elif float(ranks[rank3]) <= float(s_line[2]) < float(ranks[rank4]):
                        rank = rank3
                    elif float(ranks[rank4]) <= float(s_line[2]) < float(ranks[rank5]):
                        rank = rank4
                    elif float(ranks[rank5]) <= float(s_line[2]) < float(ranks[rank6]):
                        rank = rank5
                    elif float(s_line[2]) >= float(ranks[rank6]):
                        rank = rank6
                    await ctx.send(f'{s_line[0]}:\nElo: {s_line[2]}\nSigma: {s_line[4]}\nRank: {rank}',
                                   delete_after=delete_delay)


    @client.command("add")
    async def add_member(ctx, name: str = None):
        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel

        if name is None:
            await ctx.send(f"Input new member for leaderboard ranking, Format is <clan>name, example: "
                           f"<BestClan>AlphaBeta. Warning, your unique Discord tag will be associated with your "
                           f"inputted name, so do not input anybody except yourself. If you make a typo, please use "
                           f"the .editname command.\nElo starts at {starting_elo} and Sigma starts at {starting_sigma} "
                           f"for all players", delete_after=delete_delay)

            try:
                msg = await client.wait_for("message", check=check, timeout=delete_delay)
            except asyncio.TimeoutError:
                await ctx.send("Sorry, you didn't reply in time!", delete_after=delete_delay)
                return

            name = msg.content

        role = discord.utils.get(ctx.guild.roles, id=bot_admin_role_id)
        with open('bot/data/ratings_master.txt') as file:
            if str(ctx.author.id) in file.read() and role not in ctx.author.roles:
                await ctx.send(f'<@{ctx.author.id}> Your Discord ID was already detected in the database! If you need '
                               f'to edit your name, use the .editname command', delete_after=delete_delay)
                return
            if name in file.read():
                await ctx.send(f'<@{ctx.author.id}> This member has already been added!',
                               delete_after=delete_delay)
                return

        elofile = open("bot/data/ratings_master.txt", "a+")
        elofile.write(f"\n{name} Elo: {starting_elo} Sigma: {starting_sigma} inputted by {ctx.author}, Discord "
                      f"Tag: <@{ctx.author.id}>")
        elofile.close()

        currentelo = open("bot/data/ratings.txt", "a+")
        currentelo.write(f"\n{name} Elo: {starting_elo} Sigma: {starting_sigma}")
        currentelo.close()
        await ctx.send(f'<@{ctx.author.id}> You were successfully registered in the database, GLHF!',
                       delete_after=delete_delay)


    @client.command('delete')
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

        with open("bot/data/ratings.txt", 'r+') as f1:
            data = f1.readlines()
            f1.seek(0)
            for line in data:
                line_split = line.split()
                if name not in line_split[0]:
                    f1.write(line)
                else:
                    msg_string = line
            f1.truncate()

        with open("bot/data/ratings_master.txt", 'r+') as f2:
            data = f2.readlines()
            f2.seek(0)
            for line in data:
                line_split = line.split()
                if name not in line_split[0]:
                    f2.write(line)
            f2.truncate()

        await ctx.send(f'{msg_string} was successfully removed from the database', delete_after=delete_delay)


    async def refresh_leaderboard():
        guild = client.guilds
        gm = None
        m = None
        pm = None
        classa = None
        classb = None
        classc = None
        novice = None
        for i in guild:
            if str(i) == "Risk Legacy Competitive":
                for j in i.emojis:
                    if str(j) == '<:GMrank:847985103787524147>':
                        gm = j
                    if str(j) == '<:Masterrank:847985113244499978>':
                        m = j
                    if str(j) == '<:PMrank:847985121478049823>':
                        pm = j
                    if str(j) == '<:ClassArank:847985131809538059>':
                        classa = j
                    if str(j) == '<:ClassBrank:847985143389356052>':
                        classb = j
                    if str(j) == '<:ClassCrank:847985151631949835>':
                        classc = j
                    if str(j) == '<:Novicerank:847985160711569468>':
                        novice = j

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
                    with open("bot/data/ratings.txt", 'r') as file:
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
                        if float(sorted_elo_ranking[i][1]) < float(ranks[rank1]):
                            rank = rank0
                            emoji = novice
                        elif float(ranks[rank1]) <= float(sorted_elo_ranking[i][1]) < float(ranks[rank2]):
                            rank = rank1
                            emoji = classc
                        elif float(ranks[rank2]) <= float(sorted_elo_ranking[i][1]) < float(ranks[rank3]):
                            rank = rank2
                            emoji = classb
                        elif float(ranks[rank3]) <= float(sorted_elo_ranking[i][1]) < float(ranks[rank4]):
                            rank = rank3
                            emoji = classa
                        elif float(ranks[rank4]) <= float(sorted_elo_ranking[i][1]) < float(ranks[rank5]):
                            rank = rank4
                            emoji = pm
                        elif float(ranks[rank5]) <= float(sorted_elo_ranking[i][1]) < float(ranks[rank6]):
                            rank = rank5
                            emoji = m
                        elif float(sorted_elo_ranking[i][1]) >= float(ranks[rank6]):
                            rank = rank6
                            emoji = gm

                        value_string = f'{sorted_elo_ranking[i][1]} ({rank}) Sigma: {sorted_elo_ranking[i][2]}'
                        new_embed.add_field(name=name_string, value=f'{emoji} ' + value_string, inline=False)
                    await message.edit(embed=new_embed)


    async def leaderboard():
        guild = client.guilds
        gm = None
        m = None
        pm = None
        classa = None
        classb = None
        classc = None
        novice = None
        for i in guild:
            if str(i) == "Risk Legacy Competitive":
                for j in i.emojis:
                    print(j)
                    if str(j) == '<:GMrank:847985103787524147>':
                        gm = j
                    if str(j) == '<:Masterrank:847985113244499978>':
                        m = j
                    if str(j) == '<:PMrank:847985121478049823>':
                        pm = j
                    if str(j) == '<:ClassArank:847985131809538059>':
                        classa = j
                    if str(j) == '<:ClassBrank:847985143389356052>':
                        classb = j
                    if str(j) == '<:ClassCrank:847985151631949835>':
                        classc = j
                    if str(j) == '<:Novicerank:847985160711569468>':
                        novice = j

        channel = client.get_channel(leaderboard_channel_id)
        elo_ranking = []
        with open("bot/data/ratings.txt", 'r') as file:
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
            if float(sorted_elo_ranking[i][1]) < float(ranks[rank1]):
                rank = rank0
                emoji = novice
            elif float(ranks[rank1]) <= float(sorted_elo_ranking[i][1]) < float(ranks[rank2]):
                rank = rank1
                emoji = classc
            elif float(ranks[rank2]) <= float(sorted_elo_ranking[i][1]) < float(ranks[rank3]):
                rank = rank2
                emoji = classb
            elif float(ranks[rank3]) <= float(sorted_elo_ranking[i][1]) < float(ranks[rank4]):
                rank = rank3
                emoji = classa
            elif float(ranks[rank4]) <= float(sorted_elo_ranking[i][1]) < float(ranks[rank5]):
                rank = rank4
                emoji = pm
            elif float(ranks[rank5]) <= float(sorted_elo_ranking[i][1]) < float(ranks[rank6]):
                rank = rank5
                emoji = m
            elif float(sorted_elo_ranking[i][1]) >= float(ranks[rank6]):
                rank = rank6
                emoji = gm

            value_string = f'{sorted_elo_ranking[i][1]} ({rank}) Sigma: {sorted_elo_ranking[i][2]}'
            embed.add_field(name=name_string, value=f'{emoji} {value_string}', inline=False)
        await channel.send(embed=embed)


    @client.command()
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


    @client.command('help')
    async def help_command(ctx):
        embed = discord.Embed(colour=discord.Colour.blue())
        embed.set_author(name='Help:')
        embed.add_field(name='Bot Developers:',
                        value='Bobo#6885 <@813330702712045590>, Sean#4318 <@202947434236739584>', inline=False)
        file = discord.File("bot/ArcturusMengsk_SC2_Cine1.jpg")
        embed.set_thumbnail(url='attachment://ArcturusMengsk_SC2_Cine1.jpg')
        embed.add_field(name='.add', value="Add yourself to be ranked", inline=True)
        embed.add_field(name='.match', value="Add a new match to influence rating", inline=True)
        embed.add_field(name='.stats', value="Check the ratings of a member", inline=True)
        embed.add_field(name='.editname', value="Edit your name (for typos and clan changes)", inline=True)
        embed.add_field(name='.help', value='Shows this', inline=True)
        embed.add_field(name='.ping', value='Bot latency (in ms)', inline=True)
        embed.add_field(name='.uptime', value='Display how long bot has been running for', inline=True)

        embed.add_field(name='.block', value="*Requires \'Bot Admin\' role* Blocks a user from inputting commands",
                        inline=True)
        embed.add_field(name='.unblock', value="*Requires \'Bot Admin\' role* Un-blocks a user from inputting commands",
                        inline=True)
        embed.add_field(name='.delete', value='*Requires \'Bot Admin\' role* Removes an erroneously entered name',
                        inline=True)
        embed.add_field(name='.editelo', value='*Requires \'Bot Admin\' role* Edits the Elo of a player', inline=True)
        embed.add_field(name='.editsigma', value='*Requires \'Bot Admin\' role* Edits the Sigma of a player',
                        inline=True)
        embed.add_field(name='.backupratings', value="*Requires \'Bot Admin\' role* Backup Current Elo ratings",
                        inline=True)
        embed.add_field(name='.restoreratings', value='*Requires \'Bot Admin\' role* Restore Elo from backup date',
                        inline=True)
        embed.add_field(name='.listmembers', value='*Requires \'Bot Admin\' role* List all members being ranked',
                        inline=True)
        embed.add_field(name='.filecontents', value='*Requires \'Bot Admin\' role* Displays contents of Elo files',
                        inline=True)
        embed.set_footer(icon_url=ctx.author.avatar_url,
                         text='Requested by {} on {}'.format(ctx.author, datetime.date.today().strftime("%m-%d-%Y")))
        await ctx.author.send(file=file, embed=embed)


    @client.event
    async def on_message(message):
        with open("bot/data/blocked_ids.txt") as f:
            data = f.readlines()
            if len(data) > 0:
                for line in data:
                    if str(message.author.id) in line:
                        await message.delete()
                        return
            else:
                pass

        if message.author.name == name_of_bot:
            return

        if message.content.startswith('.'):
            await client.process_commands(message)
            if str(message.content) == str('.match'):
                await refresh_leaderboard()
        else:
            return


    @client.event
    async def on_command_error(ctx, error):
        await ctx.send(f'Error. Try .help ({error})', delete_after=15)


    print('Bot is active')
    client.run(TOKEN)
