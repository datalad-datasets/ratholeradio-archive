The Rathole Radio git-annex archive
-----------------------------------

This is just a [git-annex](http://git-annex.branchable.com/) repository (with some abomination under
`.datalad/`) to provide convenient access to all episodes of the [Rathole Radio](http://ratholeradio.org).
In each of the two sub-directories (`mp3` and `ogg`) besides expected `.mp3` and `.ogg` files you will
find `.cue` files with information about timing/artist/title for the tracks Dan has played in those
episodes.  Such arrangement opens a number of opportunities
 
 - `git grep PHRASE` to e.g. find episodes with your favorite bands or titles you might remember
  
 - Listening to those episodes with some .cue-capable player (e.g., [qmmp](http://qmmp.ylsoftware.com))
   which would allow you to navigate around the episode

Disclaimer: There might still be broken and missing entries.  If you spot some, please file an issue on
[github](https://github.com/datalad/ratholeradio-archive/issues).

Enjoy!