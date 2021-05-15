# 840768588000133151 App ID
# 8c7512fd0dfb5065a14a12db3f51d3f95a553948849b3ab5998039206d322dac Public Key
# Client ID 840768588000133151
# Client Secret i-ekmg_PFBKncCPpvsc7SwzPxBmOf99w

import discord
from discord.ext import commands
import math


# Function to calculate the Probability
def Probability(rating1, rating2):
    return 1.0 * 1.0 / (1 + 1.0 * math.pow(10, 1.0 * (rating1 - rating2) / 400))


# Function to calculate Elo rating
# K is a constant.
# d determines whether
# Player A wins or Player B.
def EloRating(Ratinga, Ratingb, K, winsa, winsb):
    Pb = Probability(Ratinga, Ratingb)
    Pa = Probability(Ratinga, Ratingb)

    # Case When Player A wins
    # Updating the Elo Ratings
    for i in range(winsa):
        Ratinga = Ratinga + K * (1 - Pa)
        Ratingb = Ratingb + K * (0 - Pb)

    # Case When Player B wins
    # Updating the Elo Ratings
    for i in range(winsb):
        Ratinga = Ratinga + K * (0 - Pa)
        Ratingb = Ratingb + K * (1 - Pb)

    # Setting an elo floor for both players
    if Ratinga < 900:
        Ratinga = 900

    if Ratingb < 900:
        Ratingb = 900

    return Ratinga, Ratingb


if __name__ == '__main__':
    TOKEN = open("token.txt", 'r').readline()
    client = commands.Bot(command_prefix='.')
    client.remove_command('help')

    @client.command()
    async def ping(ctx):
        print('pinged')
        await ctx.send(f'Pong! {round(client.latency * 1000)}ms ')


    @client.command()
    async def backup(ctx):
        with open('Current ELO.txt', 'r') as file:
            data = file.readlines()

        with open('Current ELO Backup.txt', 'w') as file:
            file.writelines(data)

        await ctx.send(f'ELO Backup copied to Current ELO')


    @client.command()
    async def match(ctx):
        await ctx.send(f"Input new match to influence rating, format is Name1 (wins) Name2 (wins), example: <RISKE>AssassinXY 3 <RISKE>Necroshader 2")
        await ctx.send(f"There is a global elo floor of 900 but no elo ceiling")

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        match = await client.wait_for("message", check=check)

        match_backup = open("Match Backup.txt", "a+")
        match_backup.write(str(match.content) + " (in case of fraudulent additions, this user inputted it) " +
                           str(match.author) + str('\n'))
        match_backup.close()

        match_array = match.content.split()

        personone = match_array[0]
        persononewins = int(match_array[1])
        persontwo = match_array[2]
        persontwowins = int(match_array[3])

        with open('ELO Backup.txt') as f:
            if personone not in f.read():
                await ctx.send(f'Person One has not been added yet!')
                return

        with open('ELO Backup.txt') as f:
            if persontwo not in f.read():
                await ctx.send(f'Person Two has not been added yet!')
                return

        persononeelo = 0
        persontwoelo = 0

        currentelofile = open('Current ELO.txt')
        for line in currentelofile:
            elofileline = line.split()
            if personone == elofileline[0]:
                persononeelo = float(elofileline[-1])
                break

        for line in currentelofile:
            elofileline = line.split()
            if persontwo == elofileline[0]:
                persontwoelo = float(elofileline[-1])
                break
        currentelofile.close()

        K = 17
        neweloplayerone, neweloplayertwo = EloRating(persononeelo, persontwoelo, K, persononewins, persontwowins)

        new_data = []
        with open("Current ELO.txt", 'r') as f:
            for i, line in enumerate(f.readlines(), 1):
                linesplitted = line.split()

                if personone == linesplitted[0]:
                    linesplitted[2] = round(neweloplayerone, 2)
                if persontwo == linesplitted[0]:
                    linesplitted[2] = round(neweloplayertwo, 2)

                new_data.append(linesplitted)

        with open('Current ELO.txt', 'w') as f:
            for linesplitted in new_data:
                linewrite = ''
                for string in linesplitted:
                    linewrite += str(string) + str(' ')

                linewrite += str('\n')
                f.writelines(linewrite)

        await ctx.send(f"Updated Ratings (automatically saved to file):-")
        string1 = '{}\'s new rating: {}'.format(personone, round(neweloplayerone, 6))
        string2 = '{}\'s new rating: {}'.format(persontwo, round(neweloplayertwo, 6))
        await ctx.send(string1)
        await ctx.send(string2)


    @client.command()
    async def add(ctx):
        await ctx.send(f"Input New Member to be ranked on the leaderboard, Format is <clan>name, example: <RISKE>AssassinXY")

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        msg = await client.wait_for("message", check=check)
        print(msg.content)

        with open('ELO Backup.txt') as f:
            if msg.content in f.read():
                print('Member has already been added')
                await ctx.send(f'This member has already been added!')
                return

        await ctx.send(f"To make rankings more fair, certain users will start with different elos")
        await ctx.send(f"Basic: 1000, Intermediate: 1100, Skilled: 1200, Expert: 1300, Master: 1400, input rank (must match exactly with ranks provided):")

        rank = await client.wait_for("message", check=check)
        print(rank.content)

        ranks = {'Basic': 1000, 'Intermediate': 1100, 'Skilled': 1200, 'Expert': 1300, 'Master': 1400}

        if rank.content in ranks:
            elo = ranks[rank.content]
            print(elo)
        else:
            await ctx.send("you inputted an invalid rank (reminder it must match exactly with the ranks provided)")
            return

        elofile = open("ELO Backup.txt", "a+")
        elofile.write(str(msg.content) + " ELO: {} (in case of fraudulent additions, this user inputted it) {}".format(str(elo), str(msg.author)) + "\n")
        elofile.close()

        currentelo = open("Current ELO.txt", "a+")
        currentelo.write(str(msg.content) + " ELO: " + str(elo) + '\n')
        currentelo.close()

        print('Member was successfully added')
        await ctx.send(f'Member was successfully added')


    @client.command(pass_context=True)
    async def help(ctx):
        embed = discord.Embed(colour=discord.Colour.green())
        embed.set_author(name='list of commands available')
        embed.add_field(name='.ping', value='Returns bot response time in milliseconds', inline=False)
        embed.add_field(name='.add', value="Add somebody who wants to be ranked (only used when new people join)", inline=False)
        embed.add_field(name='.match', value="Add a new match to influence rating", inline=False)
        embed.add_field(name='.backup', value="*For Administrator Use Only* Backup Current ELO", inline=False)
        await ctx.send(embed=embed)


    @client.event
    async def on_command_error(ctx, error):
        await ctx.send(f'Error. Try .help ({error})')

    print('Bot is active')

    client.run(TOKEN)
