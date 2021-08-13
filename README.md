# yuzu-compat-bot

A discord bot to maintain a list of compatible yuzu games in a neat format.

## Running

0. Make sure you have docker and docker-compose installed, and are in the bot directory (where this file is).
1. Set up your discord server:
    1. Have a channel with \<yuzu-compat: list> in the description somewhere (including the brackets). This will be the channel where the bot stores a list of games.
    2. (optional) 1. Have a channel with \<yuzu-compat: log> in the description somewhere (including the brackets). This will be the channel where the bot gives a log of who edited what. 
2. `echo "put your token here" > token`
3. TODO: instructions (and a better method) on how to change the role that can edit. 
3. `docker-compose up --build`
