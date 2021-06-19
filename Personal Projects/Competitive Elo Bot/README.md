# comp-elo-discord-bot
Used for saving and updating ELO information for ranked 1v1s for the Risk Legacy Arcade game in Starcraft II

How to get started using the bot:

Copy and paste the following link into your browser, you will be prompted to add the bot to your Discord server, and
then be redirected back to this Github repository.

https://discord.com/oauth2/authorize?client_id=840768588000133151&permissions=268889104&scope=bot

This URL gives the Competitive Ratings Bot the following permissions:

![image](https://user-images.githubusercontent.com/58061340/120872200-978d8300-c563-11eb-966f-229ca1cc9038.png)

Upon first invite to the server, the .setup command should be invoked by anybody with "administrator" permissions
in order to create the channels and roles required for the bot to function normally. These channels can be moved as 
you wish, but not renamed as the names are hardcoded.


Quick rundown on the mechanisms of the bot:
The bot works through saving member information to a .db file with a table specifiyng your guild id 
(to differentiate from server to server) using sqllite3. Updates to these files are made via queries using the commands
below. Since the .db files are in non-human readable binary format, I have a command to allow you to view the contents 
of each .db file, and delete any troublesome lines as needed, (although this is not recommended as it may cause issues 
with the auto-incrementing pointers so try to use it sparingly).


The "Bot Admin" role is used to oversee most of the Bot's operations, through viewing the file contents 
(.file_contents or .fc) of each table, adjusting ratings and sigma if there are erroneous matches entered, and banning/
unbanning troublesome users from issuing commands to the bot.


In the event of any issues, please contact me at my email address: alons3253@gmail.com or on discord using my ID and
tag supplied below.

If you have any questions, comments, suggestions, or any other inquiries, please feel free to contact me via the aforementioned avenues. Thanks!

All commands have the option of either supplying their arguments in one line or waiting until prompted to provide them,
i.e. typing ".add <Clan>Example" versus typing ".add" then typing "<Clan>Example".

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

.editsigma = *Requires \'Bot Admin\' role* Adjusts a member's Sigma (ratings uncertainty)

.backupratings = *Requires \'Bot Admin\' role* Backup all .db files in the data directory

.restoreratings = *Requires \'Bot Admin\' role* Restore .db files from backup date

.members = *Requires \'Bot Admin\' role* Displays all members registered on the bot

.filecontents = *Requires \'Bot Admin\' role* Displays contents of database files for your specific server
