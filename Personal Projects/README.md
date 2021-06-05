# comp-elo-discord-bot
Used for saving and updating ELO information for ranked 1v1s for the Risk Legacy Arcade game in Starcraft II

https://discord.com/api/oauth2/authorize?client_id=840768588000133151&permissions=268954640&scope=bot
Copy and paste this link in your browser to invite the bot into your server, bot is given the following permissions:
![image](https://user-images.githubusercontent.com/58061340/120872200-978d8300-c563-11eb-966f-229ca1cc9038.png)

The bot works through saving member information to a txt file, then updating their elo rating as necessary using file I/O operations.
Backups are used in order to save information.
Adding members and matches are saved in text files, along with the Discord user tag in order to audit new additions.

Bot Developers:

Bobo#6885 <@813330702712045590>

Sean#4318 <@202947434236739584>

Current Commands:

.add = Add yourself to be ranked

.match = Add a new match to influence rating

.stats = Check the Elo rating of a member

.editname = Edit your name (for typos and clan changes)

.help = Shows all commands

.ping = Shows Bot latency (in ms)

.uptime = Display how long bot has been running for

.block = *Requires \'Bot Admin\' role* Blocks a user from inputting commands

.unblock = *Requires \'Bot Admin\' role* Un-blocks a user from inputting commands

.delete = *Requires \'Bot Admin\' role* Removes an erroneously entered name

.editelo = *Requires \'Bot Admin\' role* Adjusts a member's Elo rating

.editsigma = *Requires \'Bot Admin\' role* Adjusts a member's Sigma (rating uncertainty)

.backupratings = *Requires \'Bot Admin\' role* Backup Current Elo ratings

.restoreratings = *Requires \'Bot Admin\' role* Restore ELO from backup date

.listmembers = *Requires \'Bot Admin\' role* List all members being ranked

.filecontents = *Requires \'Bot Admin\' role* Displays contents of Elo files
