#!/bin/sh

sqlite-utils insert ./var/users.db users --csv ./share/users.csv --detect-types --pk=id
sqlite-utils create-index ./var/users.db users username bio email password --unique
sqlite-utils insert ./var/users.db followers --csv ./share/followers.csv --detect-types --pk=id
sqlite-utils create-index ./var/users.db followers username friend_username --unique
sqlite-utils insert ./var/posts.db posts --csv ./share/posts.csv --detect-types --pk=id
sqlite-utils create-index ./var/posts.db posts username message timestamp repost --unique
