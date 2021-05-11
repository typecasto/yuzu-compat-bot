# Storage

The "database" (games.json) is stored here, and this folder gets mounted as a volume each time the container is started.

This file is really only here so that git will create the directory.

In the future, games.json may be replaced with protocol buffers, or some other format. 

This folder will eventually be split between different emulators, as well.